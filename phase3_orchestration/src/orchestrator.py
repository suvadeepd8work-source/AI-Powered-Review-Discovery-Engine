"""
AgentPipelineOrchestrator
=========================
Coordinates the sequential execution of all 7 AI agents.

Execution order:
  Agent 1  Review Collector          phase: ingestion
  Agent 2  Data Cleaner              phase: cleaning
  Agent 3  Review Analyzer           phase: analysis
  Agent 4  Theme Clustering          phase: clustering
  Agent 5  User Segmentation         phase: segmentation
  Agent 6  Product Insight Generator phase: insights
  Agent 7  Executive Report Generator phase: reporting

For every agent the orchestrator:
  - Records the current agent name and pipeline phase in the DB.
  - Measures wall-clock execution time.
  - Retries the agent call up to MAX_AGENT_RETRIES times on transient failures.
  - Tracks the retry count and last error string.
  - Writes structured log entries to both the SQLite DB and a per-run JSONL file.
"""

import uuid
import datetime
import os
import sys
import shutil
import time
import json
from typing import Optional, Callable, Any

from tenacity import retry, stop_after_attempt, wait_exponential, RetryError, before_sleep_log
import logging

# ---------------------------------------------------------------------------
# Path setup – allow importing from other phases
# ---------------------------------------------------------------------------
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(root_dir, "phase3_orchestration", "src"))
sys.path.insert(0, os.path.join(root_dir, "phase1_data_ingestion", "src"))
sys.path.insert(0, os.path.join(root_dir, "phase2_agent_analysis", "src"))

# ---------------------------------------------------------------------------
# Agent imports
# ---------------------------------------------------------------------------
from collector import MultiSourceReviewCollector
from cleaner import DataCleanerAgent
from analyzer import DataAnalyzerPipeline
from clustering import ThemeClusteringPipeline
from segmentation import UserSegmentationPipeline
from insights import ProductInsightPipeline
from report import ExecutiveReportPipeline

from state_db import init_db, PipelineRun, AgentExecutionLog
from logger import OrchestratorLogger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_AGENT_RETRIES = 3          # Maximum retry attempts per agent
RETRY_WAIT_MIN_S  = 2          # Tenacity: minimum wait between retries (seconds)
RETRY_WAIT_MAX_S  = 10         # Tenacity: maximum wait between retries (seconds)


class AgentPipelineOrchestrator:
    """State-machine orchestrator for the 7-agent review analysis pipeline."""

    def __init__(self, db_conn_str: str = "sqlite:///pipeline_state.db"):
        self.Session = init_db(db_conn_str)
        self._current_agent: str = "Pipeline"
        self._current_phase: str = "none"
        self._data_context: dict = {}  # Share data between phases to avoid redundant I/O

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def create_run(self) -> str:
        session = self.Session()
        run_id = str(uuid.uuid4())
        new_run = PipelineRun(
            run_id=run_id,
            status="pending",
            current_phase="none",
            start_time=datetime.datetime.now(datetime.timezone.utc),
        )
        session.add(new_run)
        session.commit()
        session.close()
        return run_id

    def log_agent_action(
        self,
        run_id: str,
        agent_name: str,
        message: str,
        level: str = "INFO",
        phase: Optional[str] = None,
        event: Optional[str] = None,
        execution_time_s: Optional[float] = None,
        retry_count: int = 0,
        error_detail: Optional[str] = None,
    ) -> None:
        session = self.Session()
        new_log = AgentExecutionLog(
            log_id=str(uuid.uuid4()),
            run_id=run_id,
            agent_name=agent_name,
            log_level=level,
            phase=phase or self._current_phase,
            event=event,
            message=message,
            execution_time_s=round(execution_time_s, 4) if execution_time_s is not None else None,
            retry_count=retry_count,
            error_detail=error_detail,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        session.add(new_log)
        session.commit()
        session.close()

    def update_run_status(
        self,
        run_id: str,
        status: str,
        phase: str,
        error_msg: Optional[str] = None,
        total_execution_time_s: Optional[float] = None,
    ) -> None:
        self._current_phase = phase
        session = self.Session()
        run = session.query(PipelineRun).filter_by(run_id=run_id).first()
        if run:
            run.status = status
            run.current_phase = phase
            if error_msg:
                run.error_message = error_msg
            if total_execution_time_s is not None:
                run.total_execution_time_s = round(total_execution_time_s, 4)
            if status in ("completed", "failed"):
                run.end_time = datetime.datetime.now(datetime.timezone.utc)
            session.commit()
        session.close()

    # ------------------------------------------------------------------
    # Agent runner with timing + retry + logging
    # ------------------------------------------------------------------

    def _run_agent(
        self,
        run_id: str,
        agent_name: str,
        phase: str,
        fn: Callable[[], Any],
        file_logger: OrchestratorLogger,
    ) -> None:
        """
        Execute *fn* with automatic retry, timing, and dual-channel logging.

        Retries up to MAX_AGENT_RETRIES times on any exception, with
        exponential back-off.  Both the DB and the JSONL file are updated
        on every event (start, retry, complete, error).
        """
        self._current_agent = agent_name
        self.update_run_status(run_id, "running", phase)

        # Log agent start
        self.log_agent_action(run_id, agent_name, f"[{agent_name}] starting.", event="start")
        file_logger.agent_start(agent_name, phase)

        retry_count = 0
        last_error: Optional[str] = None
        agent_start_time = time.perf_counter()

        for attempt in range(1, MAX_AGENT_RETRIES + 1):
            try:
                fn()
                elapsed = time.perf_counter() - agent_start_time

                # Success
                self.log_agent_action(
                    run_id, agent_name,
                    f"[{agent_name}] completed in {elapsed:.2f}s.",
                    event="complete",
                    execution_time_s=elapsed,
                    retry_count=retry_count,
                )
                file_logger.agent_complete(agent_name, phase, elapsed)
                return  # ← success path

            except Exception as exc:
                last_error = str(exc)
                retry_count = attempt

                if attempt < MAX_AGENT_RETRIES:
                    wait_s = min(RETRY_WAIT_MIN_S * (2 ** (attempt - 1)), RETRY_WAIT_MAX_S)
                    # Log the retry
                    self.log_agent_action(
                        run_id, agent_name,
                        f"[{agent_name}] retry #{attempt}: {last_error}",
                        level="WARNING",
                        event="retry",
                        retry_count=attempt,
                        error_detail=last_error,
                    )
                    file_logger.agent_retry(agent_name, phase, attempt, last_error)
                    time.sleep(wait_s)
                else:
                    # All retries exhausted
                    elapsed = time.perf_counter() - agent_start_time
                    self.log_agent_action(
                        run_id, agent_name,
                        f"[{agent_name}] failed after {retry_count} retries: {last_error}",
                        level="ERROR",
                        event="error",
                        execution_time_s=elapsed,
                        retry_count=retry_count,
                        error_detail=last_error,
                    )
                    file_logger.agent_error(agent_name, phase, last_error, retry_count)
                    raise  # re-raise so execute_pipeline catches it

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def execute_pipeline(self, run_id: str) -> None:
        file_logger = OrchestratorLogger(run_id)
        pipeline_start = time.perf_counter()
        file_logger.pipeline_start()

        try:
            # Ensure required directories exist
            os.makedirs(os.path.join(root_dir, "phase1_data_ingestion", "data"), exist_ok=True)
            os.makedirs(os.path.join(root_dir, "phase2_agent_analysis", "data", "input"), exist_ok=True)
            os.makedirs(os.path.join(root_dir, "phase2_agent_analysis", "data", "output"), exist_ok=True)

            dest_reviews = os.path.join(root_dir, "phase2_agent_analysis", "data", "input", "reviews.json")

            # ── Agent 1: Review Collector ─────────────────────────────────
            def run_collector():
                collector = MultiSourceReviewCollector(
                    output_dir=os.path.join(root_dir, "phase1_data_ingestion", "data")
                )
                collector.execute_collection(target_total=1000)
                src = os.path.join(root_dir, "phase1_data_ingestion", "data", "reviews.json")
                if not os.path.exists(src):
                    raise FileNotFoundError(f"Collector produced no output at {src}")
                shutil.copy2(src, dest_reviews)

            self._run_agent(run_id, "Review Collector", "ingestion", run_collector, file_logger)

            # ── Agent 2: Data Cleaner ─────────────────────────────────────
            def run_cleaner():
                cleaner = DataCleanerAgent(
                    input_path=dest_reviews,
                    output_dir=os.path.join(root_dir, "phase2_agent_analysis", "data", "output"),
                )
                cleaner.run()
                # Load cleaned reviews into memory for next phase
                cleaned_file = os.path.join(root_dir, "phase2_agent_analysis", "data", "output", "filtered_reviews.json")
                with open(cleaned_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self._data_context['cleaned_reviews'] = eval(content)

            self._run_agent(run_id, "Data Cleaner", "cleaning", run_cleaner, file_logger)

            # ── Agent 3: Review Analyzer ──────────────────────────────────
            def run_analyzer():
                analyzer = DataAnalyzerPipeline(
                    output_dir=os.path.join(root_dir, "phase2_agent_analysis", "data", "output"),
                )
                # Use in-memory data instead of loading from file
                result = analyzer.analyze_from_data(self._data_context['cleaned_reviews'])
                analyzer.save(result)
                # Store analyzed reviews in memory for next phases
                self._data_context['analyzed_reviews'] = result['analyzed_reviews']

            self._run_agent(run_id, "Review Analyzer", "analysis", run_analyzer, file_logger)

            # ── Agent 4: Theme Clustering ─────────────────────────────────
            def run_clustering():
                clustering = ThemeClusteringPipeline(
                    output_dir=os.path.join(root_dir, "phase2_agent_analysis", "data", "output"),
                )
                # Use in-memory analyzed reviews
                themes = clustering.analyze_from_data(self._data_context['analyzed_reviews'])
                clustering.save(themes)
                # Store themes in memory
                self._data_context['themes'] = themes

            self._run_agent(run_id, "Theme Clustering", "clustering", run_clustering, file_logger)

            # ── Agent 5: User Segmentation ────────────────────────────────
            def run_segmentation():
                segmentation = UserSegmentationPipeline(
                    output_dir=os.path.join(root_dir, "phase2_agent_analysis", "data", "output"),
                )
                # Use in-memory analyzed reviews
                segments = segmentation.analyze_from_data(self._data_context['analyzed_reviews'])
                segmentation.save(segments)
                # Store segments in memory
                self._data_context['segments'] = segments

            self._run_agent(run_id, "User Segmentation", "segmentation", run_segmentation, file_logger)

            # ── Agent 6: Product Insight Generator ────────────────────────
            def run_insights():
                insights_pipeline = ProductInsightPipeline(
                    output_dir=os.path.join(root_dir, "phase2_agent_analysis", "data", "output"),
                )
                # Use in-memory data
                insights = insights_pipeline.analyze_from_data(
                    self._data_context['analyzed_reviews'],
                    self._data_context['themes'],
                    self._data_context['segments']
                )
                insights_pipeline.save(insights)
                # Store insights in memory
                self._data_context['insights'] = insights.model_dump()

            self._run_agent(run_id, "Product Insight Generator", "insights", run_insights, file_logger)

            # ── Agent 7: Executive Report Generator ───────────────────────
            def run_report():
                report_pipeline = ExecutiveReportPipeline(
                    output_dir=os.path.join(root_dir, "phase2_agent_analysis", "data", "output"),
                )
                # Calculate metrics from in-memory data
                metrics = report_pipeline.calculate_metrics(self._data_context['analyzed_reviews'])
                
                # Convert themes and segments to proper format
                from models import ExecutiveReportTheme, ExecutiveReportSegment
                total_theme_reviews = sum(len(t.get("supporting_reviews", [])) for t in self._data_context['themes'])
                themes_objs = []
                for t in self._data_context['themes']:
                    cnt = len(t.get("supporting_reviews", []))
                    pct = (cnt / total_theme_reviews) * 100 if total_theme_reviews > 0 else 0.0
                    themes_objs.append(
                        ExecutiveReportTheme(
                            theme_name=t["theme_name"],
                            description=t["description"],
                            review_count=cnt,
                            percentage=round(pct, 2)
                        )
                    )
                
                total_seg_reviews = sum(s.get("review_count", 0) for s in self._data_context['segments'])
                segments_objs = []
                for s in self._data_context['segments']:
                    cnt = s.get("review_count", 0)
                    pct = (cnt / total_seg_reviews) * 100 if total_seg_reviews > 0 else 0.0
                    segments_objs.append(
                        ExecutiveReportSegment(
                            segment_name=s["segment_name"],
                            description=s["description"],
                            review_count=cnt,
                            percentage=round(pct, 2)
                        )
                    )
                
                # Generate report using in-memory data
                report = report_pipeline.report_agent.generate_report(
                    metrics, themes_objs, segments_objs, self._data_context['insights']
                )
                report_pipeline.save(report)
                
                # Promote reports to project root
                shutil.copy2(
                    os.path.join(root_dir, "phase2_agent_analysis", "data", "output", "executive_report.json"),
                    os.path.join(root_dir, "executive_report.json"),
                )
                shutil.copy2(
                    os.path.join(root_dir, "phase2_agent_analysis", "data", "output", "executive_report.md"),
                    os.path.join(root_dir, "executive_report.md"),
                )

            self._run_agent(run_id, "Executive Report Generator", "reporting", run_report, file_logger)

            # ── Pipeline complete ─────────────────────────────────────────
            total_elapsed = time.perf_counter() - pipeline_start
            self.update_run_status(run_id, "completed", "reporting", total_execution_time_s=total_elapsed)
            self.log_agent_action(
                run_id, "Pipeline",
                f"Pipeline run {run_id} finished successfully in {total_elapsed:.2f}s.",
                event="pipeline_end",
                execution_time_s=total_elapsed,
            )
            file_logger.pipeline_end(total_elapsed, "completed")
            print(f"\n[Orchestrator] Pipeline completed in {total_elapsed:.2f}s.")

        except Exception as exc:
            total_elapsed = time.perf_counter() - pipeline_start
            self.update_run_status(
                run_id, "failed", self._current_phase,
                error_msg=str(exc),
                total_execution_time_s=total_elapsed,
            )
            self.log_agent_action(
                run_id, "Pipeline",
                f"Pipeline failed at agent '{self._current_agent}' (phase={self._current_phase}): {exc}",
                level="ERROR",
                event="pipeline_end",
                execution_time_s=total_elapsed,
                error_detail=str(exc),
            )
            file_logger.pipeline_end(total_elapsed, "failed")
            raise


if __name__ == "__main__":
    orchestrator = AgentPipelineOrchestrator()
    run_id = orchestrator.create_run()
    print(f"[Orchestrator] Starting pipeline run: {run_id}")
    orchestrator.execute_pipeline(run_id)
    print("[Orchestrator] Done.")
