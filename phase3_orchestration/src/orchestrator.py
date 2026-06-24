import uuid
import datetime
from typing import Optional
from state_db import init_db, PipelineRun, AgentExecutionLog

class AgentPipelineOrchestrator:
    def __init__(self, db_conn_str: str = "sqlite:///pipeline_state.db"):
        self.Session = init_db(db_conn_str)

    def create_run(self) -> str:
        session = self.Session()
        run_id = str(uuid.uuid4())
        new_run = PipelineRun(
            run_id=run_id,
            status="pending",
            current_phase="none",
            start_time=datetime.datetime.now(datetime.timezone.utc)
        )
        session.add(new_run)
        session.commit()
        session.close()
        return run_id

    def log_agent_action(self, run_id: str, agent_name: str, message: str, level: str = "INFO"):
        session = self.Session()
        new_log = AgentExecutionLog(
            log_id=str(uuid.uuid4()),
            run_id=run_id,
            agent_name=agent_name,
            log_level=level,
            message=message,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        session.add(new_log)
        session.commit()
        session.close()

    def update_run_status(self, run_id: str, status: str, phase: str, error_msg: Optional[str] = None):
        session = self.Session()
        run = session.query(PipelineRun).filter_by(run_id=run_id).first()
        if run:
            run.status = status
            run.current_phase = phase
            if error_msg:
                run.error_message = error_msg
            if status in ("completed", "failed"):
                run.end_time = datetime.datetime.now(datetime.timezone.utc)
            session.commit()
        session.close()

    def execute_pipeline(self, run_id: str):
        try:
            self.update_run_status(run_id, "running", "ingestion")
            self.log_agent_action(run_id, "Review Collector", "Starting review ingestion from resources...")
            
            # Step 1: Ingest
            self.log_agent_action(run_id, "Review Collector", "Ingested 100 new reviews successfully.")

            # Step 2: Clean & Analyze
            self.update_run_status(run_id, "running", "cleaning_analysis")
            self.log_agent_action(run_id, "Data Cleaner", "Translating and standardizing text content...")
            self.log_agent_action(run_id, "Review Analyzer", "Extracting sentiments and category flags...")

            # Step 3: Clustering & Segmentation
            self.update_run_status(run_id, "running", "clustering")
            self.log_agent_action(run_id, "Theme Clustering", "Executing multi-text theme aggregation...")
            self.log_agent_action(run_id, "User Segmentation", "Identifying demographic and usage categories...")

            # Step 4: Insights & Reporting
            self.update_run_status(run_id, "running", "reporting")
            self.log_agent_action(run_id, "Product Insight Generator", "Mapping feature requests to clusters...")
            self.log_agent_action(run_id, "Executive Report Generator", "Generating final report in markdown format...")

            # Success
            self.update_run_status(run_id, "completed", "reporting")
            self.log_agent_action(run_id, "Pipeline", "Pipeline run finished successfully.")

        except Exception as e:
            self.update_run_status(run_id, "failed", "none", error_msg=str(e))
            self.log_agent_action(run_id, "Pipeline", f"Pipeline failed: {e}", level="ERROR")

if __name__ == "__main__":
    orchestrator = AgentPipelineOrchestrator()
    run_id = orchestrator.create_run()
    print(f"Started pipeline execution for run: {run_id}")
    orchestrator.execute_pipeline(run_id)
    print("Orchestration cycle simulation complete.")
