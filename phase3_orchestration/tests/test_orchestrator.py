"""
Tests for the AgentPipelineOrchestrator.

Coverage:
  - Run creation & default status
  - Full happy-path execution cycle with all 7 agents mocked
  - Verify execution_time_s, retry_count, event columns are written to DB
  - Verify JSONL file is written per-run with correct fields
  - Verify failed-run path: error captured, status=failed, file log ends with error
  - Verify retry logic: agent fails N-1 times then succeeds; retry_count recorded
"""

import json
import os
import sys
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock, call

# Adjust path so src modules are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from orchestrator import AgentPipelineOrchestrator, MAX_AGENT_RETRIES
from state_db import PipelineRun, AgentExecutionLog
from logger import OrchestratorLogger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_jsonl(path: str) -> list:
    """Read all JSONL entries from *path* into a list of dicts."""
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


# ---------------------------------------------------------------------------
# Fixtures – dummy file writers that simulate real agent output
# ---------------------------------------------------------------------------

def _make_dummy_files(root_dir: str):
    """Return a dict of side-effect functions, one per agent."""

    p1_reviews   = os.path.join(root_dir, "phase1_data_ingestion", "data", "reviews.json")
    p2_input     = os.path.join(root_dir, "phase2_agent_analysis", "data", "input", "reviews.json")
    p2_filtered  = os.path.join(root_dir, "phase2_agent_analysis", "data", "output", "filtered_reviews.json")
    p2_analyzed  = os.path.join(root_dir, "phase2_agent_analysis", "data", "output", "analyzed_reviews.json")
    p2_themes    = os.path.join(root_dir, "phase2_agent_analysis", "data", "output", "themes.json")
    p2_segments  = os.path.join(root_dir, "phase2_agent_analysis", "data", "output", "segments.json")
    p2_insights  = os.path.join(root_dir, "phase2_agent_analysis", "data", "output", "product_insights.json")
    p2_rep_json  = os.path.join(root_dir, "phase2_agent_analysis", "data", "output", "executive_report.json")
    p2_rep_md    = os.path.join(root_dir, "phase2_agent_analysis", "data", "output", "executive_report.md")
    root_rep_json = os.path.join(root_dir, "executive_report.json")
    root_rep_md   = os.path.join(root_dir, "executive_report.md")

    all_files = [p1_reviews, p2_input, p2_filtered, p2_analyzed, p2_themes,
                 p2_segments, p2_insights, p2_rep_json, p2_rep_md,
                 root_rep_json, root_rep_md]

    def _w(path, content="{}"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def collector(target_total):
        _w(p1_reviews, '{"test":"collector"}')

    def cleaner():
        _w(p2_filtered, '{"test":"cleaner"}')

    def analyzer():
        _w(p2_analyzed, '{"test":"analyzer"}')

    def clustering():
        _w(p2_themes, '{"test":"clustering"}')

    def segmentation():
        _w(p2_segments, '{"test":"segmentation"}')

    def insights():
        _w(p2_insights, '{"test":"insights"}')

    def report():
        _w(p2_rep_json, '{"test":"report"}')
        _w(p2_rep_md,   "# Executive Report")
        _w(root_rep_json, '{"test":"report_root"}')
        _w(root_rep_md,   "# Executive Report Root")

    return {
        "collector":    collector,
        "cleaner":      cleaner,
        "analyzer":     analyzer,
        "clustering":   clustering,
        "segmentation": segmentation,
        "insights":     insights,
        "report":       report,
        "all_files":    all_files,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@patch("orchestrator.MultiSourceReviewCollector")
@patch("orchestrator.DataCleanerAgent")
@patch("orchestrator.DataAnalyzerPipeline")
@patch("orchestrator.ThemeClusteringPipeline")
@patch("orchestrator.UserSegmentationPipeline")
@patch("orchestrator.ProductInsightPipeline")
@patch("orchestrator.ExecutiveReportPipeline")
class TestPipelineOrchestrator(unittest.TestCase):

    def setUp(self):
        # Isolated SQLite + temp log directory
        self.orchestrator = AgentPipelineOrchestrator(db_conn_str="sqlite:///:memory:")
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        self.log_dir = tempfile.mkdtemp(prefix="orch_test_logs_")
        # Patch the logger to use the temp dir
        self._log_dir_patcher = patch("orchestrator.OrchestratorLogger",
                                      lambda run_id: OrchestratorLogger(run_id, log_dir=self.log_dir))
        self._log_dir_patcher.start()
        self.fixtures = _make_dummy_files(self.root_dir)
        self._cleanup()

    def tearDown(self):
        self._log_dir_patcher.stop()
        self._cleanup()
        shutil.rmtree(self.log_dir, ignore_errors=True)

    def _cleanup(self):
        for fpath in self.fixtures["all_files"]:
            if os.path.exists(fpath):
                try:
                    os.remove(fpath)
                except Exception:
                    pass

    def _apply_mocks(self, mock_report, mock_insight, mock_segment,
                     mock_cluster, mock_analyzer, mock_cleaner, mock_collector):
        fx = self.fixtures
        mock_collector.return_value.execute_collection.side_effect = fx["collector"]
        mock_cleaner.return_value.run.side_effect   = fx["cleaner"]
        mock_analyzer.return_value.run.side_effect  = fx["analyzer"]
        mock_cluster.return_value.run.side_effect   = fx["clustering"]
        mock_segment.return_value.run.side_effect   = fx["segmentation"]
        mock_insight.return_value.run.side_effect   = fx["insights"]
        mock_report.return_value.run.side_effect    = fx["report"]

    # ── 1. Run creation ──────────────────────────────────────────────────────

    def test_run_creation(self, *mocks):
        run_id = self.orchestrator.create_run()
        self.assertIsNotNone(run_id)
        session = self.orchestrator.Session()
        run = session.query(PipelineRun).filter_by(run_id=run_id).first()
        self.assertEqual(run.status, "pending")
        self.assertEqual(run.current_phase, "none")
        session.close()

    # ── 2. Happy-path execution cycle ────────────────────────────────────────

    def test_run_execution_cycle(self, mock_report, mock_insight, mock_segment,
                                 mock_cluster, mock_analyzer, mock_cleaner, mock_collector):
        self._apply_mocks(mock_report, mock_insight, mock_segment,
                          mock_cluster, mock_analyzer, mock_cleaner, mock_collector)
        run_id = self.orchestrator.create_run()
        self.orchestrator.execute_pipeline(run_id)

        session = self.orchestrator.Session()
        run = session.query(PipelineRun).filter_by(run_id=run_id).first()

        # Pipeline status
        self.assertEqual(run.status, "completed")
        self.assertEqual(run.current_phase, "reporting")
        self.assertIsNotNone(run.total_execution_time_s)
        self.assertGreater(run.total_execution_time_s, 0)

        # All 7 agent names appear in logs
        logs = session.query(AgentExecutionLog).filter_by(run_id=run_id).all()
        agent_names = {log.agent_name for log in logs}
        expected_agents = {
            "Review Collector", "Data Cleaner", "Review Analyzer",
            "Theme Clustering", "User Segmentation",
            "Product Insight Generator", "Executive Report Generator",
        }
        self.assertTrue(expected_agents.issubset(agent_names))
        session.close()

        # Root reports exist
        self.assertTrue(os.path.exists(os.path.join(self.root_dir, "executive_report.json")))
        self.assertTrue(os.path.exists(os.path.join(self.root_dir, "executive_report.md")))

    # ── 3. Execution time logged in DB ───────────────────────────────────────

    def test_execution_time_recorded_in_db(self, mock_report, mock_insight, mock_segment,
                                            mock_cluster, mock_analyzer, mock_cleaner, mock_collector):
        self._apply_mocks(mock_report, mock_insight, mock_segment,
                          mock_cluster, mock_analyzer, mock_cleaner, mock_collector)
        run_id = self.orchestrator.create_run()
        self.orchestrator.execute_pipeline(run_id)

        session = self.orchestrator.Session()
        # Every "complete" log entry must have a non-None, positive execution_time_s
        complete_logs = (session.query(AgentExecutionLog)
                         .filter_by(run_id=run_id, event="complete")
                         .all())
        self.assertEqual(len(complete_logs), 7,
                         "Expected exactly 7 'complete' log entries (one per agent).")
        for log in complete_logs:
            self.assertIsNotNone(log.execution_time_s,
                                 f"execution_time_s is None for {log.agent_name}")
            self.assertGreaterEqual(log.execution_time_s, 0)
        session.close()

    # ── 4. JSONL file written per run ────────────────────────────────────────

    def test_jsonl_log_file_written(self, mock_report, mock_insight, mock_segment,
                                    mock_cluster, mock_analyzer, mock_cleaner, mock_collector):
        self._apply_mocks(mock_report, mock_insight, mock_segment,
                          mock_cluster, mock_analyzer, mock_cleaner, mock_collector)
        run_id = self.orchestrator.create_run()
        self.orchestrator.execute_pipeline(run_id)

        log_path = os.path.join(self.log_dir, f"run_{run_id}.jsonl")
        self.assertTrue(os.path.exists(log_path), "JSONL log file not created.")

        entries = _read_jsonl(log_path)
        self.assertGreater(len(entries), 0)

        # Every entry must have the mandatory fields
        required_fields = {"timestamp", "run_id", "agent_name", "level",
                           "phase", "event", "message"}
        for entry in entries:
            for field in required_fields:
                self.assertIn(field, entry, f"Missing field '{field}' in entry: {entry}")

        # First entry is pipeline_start, last is pipeline_end
        self.assertEqual(entries[0]["event"], "pipeline_start")
        self.assertEqual(entries[-1]["event"], "pipeline_end")
        self.assertEqual(entries[-1]["agent_name"], "Pipeline")

    # ── 5. Pipeline phase sequence in JSONL ──────────────────────────────────

    def test_jsonl_phase_sequence(self, mock_report, mock_insight, mock_segment,
                                   mock_cluster, mock_analyzer, mock_cleaner, mock_collector):
        self._apply_mocks(mock_report, mock_insight, mock_segment,
                          mock_cluster, mock_analyzer, mock_cleaner, mock_collector)
        run_id = self.orchestrator.create_run()
        self.orchestrator.execute_pipeline(run_id)

        entries = _read_jsonl(os.path.join(self.log_dir, f"run_{run_id}.jsonl"))
        start_phases = [e["phase"] for e in entries if e["event"] == "start"]
        expected_phases = [
            "ingestion", "cleaning", "analysis",
            "clustering", "segmentation", "insights", "reporting",
        ]
        self.assertEqual(start_phases, expected_phases)

    # ── 6. Retry logic – agent succeeds on 2nd attempt ───────────────────────

    def test_retry_on_transient_failure(self, mock_report, mock_insight, mock_segment,
                                         mock_cluster, mock_analyzer, mock_cleaner, mock_collector):
        """Review Collector fails once then succeeds; retry_count=1 in DB."""
        self._apply_mocks(mock_report, mock_insight, mock_segment,
                          mock_cluster, mock_analyzer, mock_cleaner, mock_collector)

        call_count = {"n": 0}
        original_collector_side_effect = self.fixtures["collector"]

        def flaky_collector(target_total):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ConnectionError("Simulated network blip on attempt 1")
            original_collector_side_effect(target_total)

        mock_collector.return_value.execute_collection.side_effect = flaky_collector

        run_id = self.orchestrator.create_run()
        self.orchestrator.execute_pipeline(run_id)

        session = self.orchestrator.Session()
        run = session.query(PipelineRun).filter_by(run_id=run_id).first()
        self.assertEqual(run.status, "completed")

        # A "retry" log entry must exist for Review Collector
        retry_log = (session.query(AgentExecutionLog)
                     .filter_by(run_id=run_id, agent_name="Review Collector", event="retry")
                     .first())
        self.assertIsNotNone(retry_log, "Expected a retry log entry for Review Collector.")
        self.assertEqual(retry_log.retry_count, 1)
        self.assertIn("Simulated network blip", retry_log.error_detail)
        session.close()

    # ── 7. Failed pipeline – error recorded in DB and file ───────────────────

    def test_failed_pipeline_error_recorded(self, mock_report, mock_insight, mock_segment,
                                             mock_cluster, mock_analyzer, mock_cleaner, mock_collector):
        """Collector always raises; after MAX_AGENT_RETRIES the pipeline fails."""
        mock_collector.return_value.execute_collection.side_effect = RuntimeError("Fatal collector error")

        run_id = self.orchestrator.create_run()
        with self.assertRaises(RuntimeError):
            self.orchestrator.execute_pipeline(run_id)

        session = self.orchestrator.Session()
        run = session.query(PipelineRun).filter_by(run_id=run_id).first()
        self.assertEqual(run.status, "failed")
        self.assertIn("Fatal collector error", run.error_message)
        self.assertIsNotNone(run.total_execution_time_s)

        # An ERROR-level log must exist in the DB
        error_log = (session.query(AgentExecutionLog)
                     .filter_by(run_id=run_id, log_level="ERROR")
                     .first())
        self.assertIsNotNone(error_log)
        session.close()

        # JSONL file: last entry must be pipeline_end with level=ERROR
        log_path = os.path.join(self.log_dir, f"run_{run_id}.jsonl")
        self.assertTrue(os.path.exists(log_path))
        entries = _read_jsonl(log_path)
        last = entries[-1]
        self.assertEqual(last["event"], "pipeline_end")
        self.assertEqual(last["level"], "ERROR")

    # ── 8. retry_count=0 on first-attempt success ────────────────────────────

    def test_retry_count_zero_on_clean_run(self, mock_report, mock_insight, mock_segment,
                                            mock_cluster, mock_analyzer, mock_cleaner, mock_collector):
        self._apply_mocks(mock_report, mock_insight, mock_segment,
                          mock_cluster, mock_analyzer, mock_cleaner, mock_collector)
        run_id = self.orchestrator.create_run()
        self.orchestrator.execute_pipeline(run_id)

        session = self.orchestrator.Session()
        complete_logs = (session.query(AgentExecutionLog)
                         .filter_by(run_id=run_id, event="complete")
                         .all())
        for log in complete_logs:
            self.assertEqual(log.retry_count, 0,
                             f"{log.agent_name} should have retry_count=0 on success.")
        session.close()


if __name__ == "__main__":
    unittest.main()
