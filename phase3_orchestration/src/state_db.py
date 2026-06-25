import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class PipelineRun(Base):
    __tablename__ = 'pipeline_runs'

    run_id = Column(String, primary_key=True)
    status = Column(String, default="pending")           # pending | running | completed | failed
    current_phase = Column(String, default="none")       # ingestion | cleaning | analysis | clustering | segmentation | insights | reporting
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    total_execution_time_s = Column(Float, nullable=True)  # wall-clock seconds for the full run
    error_message = Column(Text, nullable=True)


class AgentExecutionLog(Base):
    __tablename__ = 'agent_execution_logs'

    log_id = Column(String, primary_key=True)
    run_id = Column(String, nullable=False)
    agent_name = Column(String, nullable=False)
    log_level = Column(String, default="INFO")           # INFO | WARNING | ERROR
    phase = Column(String, nullable=True)                # current pipeline phase when this log was emitted
    event = Column(String, nullable=True)                # start | complete | retry | error | pipeline_start | pipeline_end
    message = Column(Text, nullable=False)
    execution_time_s = Column(Float, nullable=True)      # seconds agent took (None for non-timed log entries)
    retry_count = Column(Integer, default=0)             # number of retries attempted before success/failure
    error_detail = Column(Text, nullable=True)           # full exception string on errors/retries
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


def init_db(conn_str: str = "sqlite:///pipeline_state.db"):
    engine = create_engine(conn_str)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


if __name__ == "__main__":
    init_db()
    print("Database models initialized successfully.")
