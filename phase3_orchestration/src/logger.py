"""
OrchestratorLogger
==================
Writes structured JSON-Lines log entries to a dedicated per-run log file on disk.

Each entry captures:
  - timestamp        ISO-8601 UTC
  - run_id           Pipeline run identifier
  - agent_name       Which agent is executing (or "Pipeline" for meta events)
  - level            INFO | WARNING | ERROR
  - phase            Current pipeline phase string
  - event            Short label: "start" | "complete" | "retry" | "error" | "pipeline_start" | "pipeline_end"
  - execution_time_s Wall-clock seconds the agent took (None for non-timed events)
  - retry_count      Number of retries attempted (0 = first attempt succeeded)
  - error            Full exception string (None on success)
  - message          Human-readable log line

Log file location:  <project_root>/phase3_orchestration/logs/run_<run_id>.jsonl
"""

import json
import os
import datetime
from typing import Optional


LOG_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "logs")
)


class OrchestratorLogger:
    """Writes structured JSONL log entries to a per-run file."""

    def __init__(self, run_id: str, log_dir: str = LOG_DIR):
        self.run_id = run_id
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_path = os.path.join(self.log_dir, f"run_{run_id}.jsonl")

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def log(
        self,
        agent_name: str,
        event: str,
        phase: str,
        level: str = "INFO",
        message: str = "",
        execution_time_s: Optional[float] = None,
        retry_count: int = 0,
        error: Optional[str] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "run_id": self.run_id,
            "agent_name": agent_name,
            "level": level,
            "phase": phase,
            "event": event,
            "execution_time_s": round(execution_time_s, 4) if execution_time_s is not None else None,
            "retry_count": retry_count,
            "error": error,
            "message": message,
        }
        self._write(entry)

    def pipeline_start(self) -> None:
        self.log(
            agent_name="Pipeline",
            event="pipeline_start",
            phase="none",
            message=f"Pipeline run {self.run_id} started.",
        )

    def pipeline_end(self, execution_time_s: float, status: str) -> None:
        self.log(
            agent_name="Pipeline",
            event="pipeline_end",
            phase="reporting",
            level="INFO" if status == "completed" else "ERROR",
            execution_time_s=execution_time_s,
            message=f"Pipeline run {self.run_id} {status} in {execution_time_s:.2f}s.",
        )

    def agent_start(self, agent_name: str, phase: str) -> None:
        self.log(
            agent_name=agent_name,
            event="start",
            phase=phase,
            message=f"[{agent_name}] starting.",
        )

    def agent_complete(self, agent_name: str, phase: str, execution_time_s: float) -> None:
        self.log(
            agent_name=agent_name,
            event="complete",
            phase=phase,
            execution_time_s=execution_time_s,
            message=f"[{agent_name}] completed in {execution_time_s:.2f}s.",
        )

    def agent_retry(self, agent_name: str, phase: str, retry_count: int, error: str) -> None:
        self.log(
            agent_name=agent_name,
            event="retry",
            phase=phase,
            level="WARNING",
            retry_count=retry_count,
            error=error,
            message=f"[{agent_name}] retry #{retry_count}: {error}",
        )

    def agent_error(self, agent_name: str, phase: str, error: str, retry_count: int = 0) -> None:
        self.log(
            agent_name=agent_name,
            event="error",
            phase=phase,
            level="ERROR",
            retry_count=retry_count,
            error=error,
            message=f"[{agent_name}] failed after {retry_count} retries: {error}",
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write(self, entry: dict) -> None:
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
