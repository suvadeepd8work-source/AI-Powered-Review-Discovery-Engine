"""
Pipeline Scheduler
==================
Automated scheduling for weekly review analysis pipeline execution.

Features:
- Weekly execution (Monday 10:00 AM IST)
- Automatic workflow execution
- Review collection and analysis
- Frontend data update
- Comprehensive logging
- Error handling and retry logic
"""

import os
import sys
import json
import logging
import shutil
from datetime import datetime, timezone, timedelta
from typing import Optional
from pathlib import Path
import pytz

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

# Path setup for imports
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(root_dir, "phase3_orchestration", "src"))
sys.path.insert(0, os.path.join(root_dir, "phase1_data_ingestion", "src"))
sys.path.insert(0, os.path.join(root_dir, "phase2_agent_analysis", "src"))

from orchestrator import AgentPipelineOrchestrator
from logger import OrchestratorLogger
from state_db import init_db, PipelineRun, SchedulerLog


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCHEDULE_TIME = "10:00"  # 10:00 AM
SCHEDULE_DAY = "mon"     # Monday
TIMEZONE = "Asia/Kolkata"  # IST

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs", "scheduler")
os.makedirs(LOG_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Setup logging
# ---------------------------------------------------------------------------
def setup_scheduler_logger():
    """Setup dedicated logger for scheduler operations."""
    logger = logging.getLogger("PipelineScheduler")
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # File handler
    log_file = os.path.join(LOG_DIR, f"scheduler_{datetime.now().strftime('%Y%m%d')}.log")
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(ch)
    
    return logger


scheduler_logger = setup_scheduler_logger()


# ---------------------------------------------------------------------------
# Scheduler Event Listeners
# ---------------------------------------------------------------------------
def job_executed_listener(event):
    """Log successful job execution."""
    scheduler_logger.info(f"Job {event.job_id} executed successfully at {datetime.now(timezone.utc)}")
    
    # Log to database
    session = init_db("sqlite:///pipeline_state.db")()
    try:
        log_entry = SchedulerLog(
            log_id=str(event.job_id),
            job_name=event.job_id,
            status="completed",
            executed_at=datetime.now(timezone.utc),
            next_run_time=event.scheduled_run_time
        )
        session.add(log_entry)
        session.commit()
    except Exception as e:
        scheduler_logger.error(f"Failed to log job execution to database: {e}")
    finally:
        session.close()


def job_error_listener(event):
    """Log job execution errors."""
    scheduler_logger.error(f"Job {event.job_id} failed: {event.exception}")
    
    # Log to database
    session = init_db("sqlite:///pipeline_state.db")()
    try:
        log_entry = SchedulerLog(
            log_id=str(event.job_id),
            job_name=event.job_id,
            status="failed",
            executed_at=datetime.now(timezone.utc),
            error_message=str(event.exception),
            next_run_time=event.scheduled_run_time
        )
        session.add(log_entry)
        session.commit()
    except Exception as e:
        scheduler_logger.error(f"Failed to log job error to database: {e}")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Pipeline Scheduler
# ---------------------------------------------------------------------------
class PipelineScheduler:
    """Manages scheduled execution of the review analysis pipeline."""
    
    def __init__(self, db_conn_str: str = "sqlite:///pipeline_state.db"):
        self.db_conn_str = db_conn_str
        self.scheduler = BackgroundScheduler(timezone=pytz.timezone(TIMEZONE))
        self.orchestrator = AgentPipelineOrchestrator(db_conn_str)
        
        # Add event listeners
        self.scheduler.add_listener(
            job_executed_listener,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            job_error_listener,
            EVENT_JOB_ERROR
        )
    
    def execute_pipeline_job(self):
        """Execute the complete pipeline workflow."""
        job_id = f"pipeline_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        scheduler_logger.info(f"Starting scheduled pipeline execution: {job_id}")
        
        try:
            # Create pipeline run
            run_id = self.orchestrator.create_run()
            scheduler_logger.info(f"Created pipeline run: {run_id}")
            
            # Execute pipeline
            self.orchestrator.execute_pipeline(run_id)
            
            # Update frontend data
            self.update_frontend_data()
            
            scheduler_logger.info(f"Pipeline execution completed successfully: {job_id}")
            
        except Exception as e:
            scheduler_logger.error(f"Pipeline execution failed: {e}")
            raise
    
    def update_frontend_data(self):
        """Trigger frontend data update after pipeline completion."""
        scheduler_logger.info("Updating frontend data...")
        
        try:
            # Copy latest reports to frontend public directory
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            source_dir = os.path.join(root_dir, "phase2_agent_analysis", "data", "output")
            frontend_dir = os.path.join(root_dir, "phase5_frontend_ui", "public", "data")
            
            os.makedirs(frontend_dir, exist_ok=True)
            
            # Copy executive report
            if os.path.exists(os.path.join(source_dir, "executive_report.json")):
                shutil.copy2(
                    os.path.join(source_dir, "executive_report.json"),
                    os.path.join(frontend_dir, "executive_report.json")
                )
                scheduler_logger.info("Copied executive report to frontend")
            
            # Copy themes
            if os.path.exists(os.path.join(source_dir, "themes.json")):
                shutil.copy2(
                    os.path.join(source_dir, "themes.json"),
                    os.path.join(frontend_dir, "themes.json")
                )
                scheduler_logger.info("Copied themes to frontend")
            
            # Copy segments
            if os.path.exists(os.path.join(source_dir, "segments.json")):
                shutil.copy2(
                    os.path.join(source_dir, "segments.json"),
                    os.path.join(frontend_dir, "segments.json")
                )
                scheduler_logger.info("Copied segments to frontend")
            
            # Copy insights
            if os.path.exists(os.path.join(source_dir, "product_insights.json")):
                shutil.copy2(
                    os.path.join(source_dir, "product_insights.json"),
                    os.path.join(frontend_dir, "product_insights.json")
                )
                scheduler_logger.info("Copied product insights to frontend")
            
            # Copy analyzed reviews
            if os.path.exists(os.path.join(source_dir, "analyzed_reviews.json")):
                shutil.copy2(
                    os.path.join(source_dir, "analyzed_reviews.json"),
                    os.path.join(frontend_dir, "analyzed_reviews.json")
                )
                scheduler_logger.info("Copied analyzed reviews to frontend")
            
            # Update last update timestamp
            timestamp_file = os.path.join(frontend_dir, "last_update.json")
            with open(timestamp_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "timezone": TIMEZONE
                }, f, indent=2)
            
            scheduler_logger.info("Frontend data update completed successfully")
            
        except Exception as e:
            scheduler_logger.error(f"Frontend data update failed: {e}")
            raise
    
    def schedule_weekly_job(self):
        """Schedule the pipeline to run every Monday at 10:00 AM IST."""
        scheduler_logger.info(f"Scheduling weekly job for {SCHEDULE_DAY} at {SCHEDULE_TIME} {TIMEZONE}")
        
        self.scheduler.add_job(
            self.execute_pipeline_job,
            trigger=CronTrigger(
                day_of_week=SCHEDULE_DAY,
                hour=int(SCHEDULE_TIME.split(':')[0]),
                minute=int(SCHEDULE_TIME.split(':')[1]),
                timezone=pytz.timezone(TIMEZONE)
            ),
            id='weekly_pipeline_execution',
            name='Weekly Review Analysis Pipeline',
            replace_existing=True
        )
        
        scheduler_logger.info("Weekly job scheduled successfully")
    
    def schedule_immediate_job(self):
        """Schedule an immediate one-time execution for testing."""
        scheduler_logger.info("Scheduling immediate pipeline execution")
        
        self.scheduler.add_job(
            self.execute_pipeline_job,
            trigger='date',
            run_date=datetime.now(pytz.timezone(TIMEZONE)) + timedelta(seconds=5),
            id='immediate_pipeline_execution',
            name='Immediate Pipeline Execution',
            replace_existing=True
        )
        
        scheduler_logger.info("Immediate job scheduled successfully")
    
    def start(self):
        """Start the scheduler."""
        scheduler_logger.info("Starting pipeline scheduler...")
        self.scheduler.start()
        scheduler_logger.info("Pipeline scheduler started")
        
        # Log next run time
        jobs = self.scheduler.get_jobs()
        if jobs:
            for job in jobs:
                next_run = job.next_run_time
                if next_run:
                    scheduler_logger.info(f"Next scheduled run: {next_run}")
    
    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        scheduler_logger.info("Shutting down pipeline scheduler...")
        self.scheduler.shutdown(wait=True)
        scheduler_logger.info("Pipeline scheduler shutdown complete")
    
    def get_job_status(self):
        """Get status of scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        status = {
            "scheduler_running": self.scheduler.running,
            "jobs": []
        }
        
        for job in jobs:
            status["jobs"].append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return status


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main():
    """Main entry point for running the scheduler."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pipeline Scheduler")
    parser.add_argument(
        "--mode",
        choices=["schedule", "run-now", "status"],
        default="schedule",
        help="Operation mode: schedule (default), run-now, status"
    )
    parser.add_argument(
        "--timezone",
        default=TIMEZONE,
        help=f"Timezone for scheduling (default: {TIMEZONE})"
    )
    
    args = parser.parse_args()
    
    scheduler = PipelineScheduler()
    
    if args.mode == "schedule":
        scheduler.schedule_weekly_job()
        scheduler.start()
        scheduler_logger.info("Scheduler running. Press Ctrl+C to stop.")
        
        try:
            # Keep the scheduler running
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            scheduler.shutdown()
    
    elif args.mode == "run-now":
        scheduler_logger.info("Executing pipeline immediately...")
        scheduler.execute_pipeline_job()
        scheduler_logger.info("Pipeline execution completed")
    
    elif args.mode == "status":
        status = scheduler.get_job_status()
        print(json.dumps(status, indent=2, default=str))


if __name__ == "__main__":
    main()
