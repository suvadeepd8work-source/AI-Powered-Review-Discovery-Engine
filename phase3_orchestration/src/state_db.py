import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class PipelineRun(Base):
    __tablename__ = 'pipeline_runs'
    
    run_id = Column(String, primary_key=True)
    status = Column(String, default="pending") # pending, running, completed, failed
    current_phase = Column(String, default="none")
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

class AgentExecutionLog(Base):
    __tablename__ = 'agent_execution_logs'
    
    log_id = Column(String, primary_key=True)
    run_id = Column(String, nullable=False)
    agent_name = Column(String, nullable=False)
    log_level = Column(String, default="INFO")
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

def init_db(conn_str: str = "sqlite:///pipeline_state.db"):
    engine = create_engine(conn_str)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database models initialized successfully.")
