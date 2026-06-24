import unittest
import sys
import os

# Adjust path to import src modules properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from orchestrator import AgentPipelineOrchestrator
from state_db import PipelineRun

class TestPipelineOrchestrator(unittest.TestCase):
    def setUp(self):
        # Using memory-isolated SQLite engine for testing
        self.orchestrator = AgentPipelineOrchestrator(db_conn_str="sqlite:///:memory:")

    def test_run_creation(self):
        run_id = self.orchestrator.create_run()
        self.assertIsNotNone(run_id)
        
        # Verify run status defaults to pending
        session = self.orchestrator.Session()
        run = session.query(PipelineRun).filter_by(run_id=run_id).first()
        self.assertEqual(run.status, "pending")
        session.close()

    def test_run_execution_cycle(self):
        run_id = self.orchestrator.create_run()
        self.orchestrator.execute_pipeline(run_id)
        
        session = self.orchestrator.Session()
        run = session.query(PipelineRun).filter_by(run_id=run_id).first()
        self.assertEqual(run.status, "completed")
        self.assertEqual(run.current_phase, "reporting")
        session.close()

if __name__ == '__main__':
    unittest.main()
