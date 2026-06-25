"""
routes/pipeline.py — Pipeline trigger and status endpoints.

POST /api/pipeline/run
  Triggers a new pipeline run via AgentPipelineOrchestrator in a background task.
  Returns a run_id immediately.

GET /api/pipeline/status/{run_id}
  Returns the current status of a pipeline run from the Phase 3 SQLite DB.
"""

import os
import sys
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session

# Allow importing Phase 3 orchestrator
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, os.path.join(root_dir, "phase3_orchestration", "src"))

from orchestrator import AgentPipelineOrchestrator  # type: ignore[import-not-found]
from config import PHASE3_DB_URL                    # type: ignore[import-not-found]
from database import get_db, get_session_factory                     # type: ignore[import-not-found]
from api_models.response import PipelineTriggerResponse, PipelineStatusResponse

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


def _run_pipeline_in_background(run_id: str) -> None:
    """Execute the full 7-agent pipeline. Called as a background task."""
    try:
        orchestrator = AgentPipelineOrchestrator(db_conn_str=PHASE3_DB_URL)
        orchestrator.execute_pipeline(run_id)
    except Exception as exc:
        # Errors are already logged inside the orchestrator; swallow here so
        # the background task doesn't crash the server process.
        print(f"[Pipeline Background Task] run_id={run_id} error: {exc}")


@router.post("/run", response_model=PipelineTriggerResponse, summary="Trigger Pipeline Run")
def trigger_pipeline(background_tasks: BackgroundTasks):
    """
    Start a new pipeline run asynchronously.

    Creates a pipeline run record in the database, enqueues the 7-agent
    pipeline as a background task, and immediately returns the **run_id**.
    Poll `GET /api/pipeline/status/{run_id}` to track progress.
    """
    try:
        orchestrator = AgentPipelineOrchestrator(db_conn_str=PHASE3_DB_URL)
        run_id = orchestrator.create_run()
    except Exception:
        # Fallback: create a UUID without DB (DB may not exist on first boot)
        run_id = str(uuid.uuid4())

    background_tasks.add_task(_run_pipeline_in_background, run_id)
    return PipelineTriggerResponse(
        run_id=run_id,
        status="pending",
        message=f"Pipeline run {run_id} enqueued. Poll /api/pipeline/status/{run_id} for updates.",
    )


@router.get("/status/{run_id}", response_model=PipelineStatusResponse, summary="Get Pipeline Status")
def get_pipeline_status(run_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the current status of a pipeline run from the state database.

    Returns full metadata including current phase, start/end times,
    total wall-clock execution time, and any error messages.
    """
    try:
        from state_db import PipelineRun  # type: ignore[import-not-found]
        run = db.query(PipelineRun).filter_by(run_id=run_id).first()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")

    if not run:
        raise HTTPException(status_code=404, detail=f"Pipeline run '{run_id}' not found.")

    return PipelineStatusResponse(
        run_id=run.run_id,
        status=run.status,
        current_phase=run.current_phase,
        start_time=run.start_time.isoformat() if run.start_time else None,
        end_time=run.end_time.isoformat() if run.end_time else None,
        total_execution_time_s=run.total_execution_time_s,
        error_message=run.error_message,
    )
