from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])

class PipelineTriggerResponse(BaseModel):
    run_id: str
    status: str

class PipelineStatusResponse(BaseModel):
    run_id: str
    status: str
    current_phase: str
    message: str

# Mock database dictionary to represent current state tracker
mock_runs_db = {}

def simulate_pipeline_run(run_id: str):
    mock_runs_db[run_id] = {
        "status": "running",
        "current_phase": "ingestion",
        "message": "Collecting user reviews..."
    }
    # Future integration will trigger Phase 3 Orchestrator here

@router.post("/run", response_model=PipelineTriggerResponse)
def trigger_pipeline(background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())
    mock_runs_db[run_id] = {
        "status": "pending",
        "current_phase": "none",
        "message": "Enqueued job"
    }
    background_tasks.add_task(simulate_pipeline_run, run_id)
    return PipelineTriggerResponse(run_id=run_id, status="pending")

@router.get("/status/{run_id}", response_model=PipelineStatusResponse)
def get_pipeline_status(run_id: str):
    if run_id not in mock_runs_db:
        raise HTTPException(status_code=404, detail="Pipeline run ID not found")
    data = mock_runs_db[run_id]
    return PipelineStatusResponse(
        run_id=run_id,
        status=data["status"],
        current_phase=data["current_phase"],
        message=data["message"]
    )
