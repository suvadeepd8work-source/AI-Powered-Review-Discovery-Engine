import sys
import os

# Register all phase src directories so tests can import internal modules
phases = [
    "phase1_data_ingestion/src",
    "phase2_agent_analysis/src",
    "phase3_orchestration/src",
    "phase4_backend_api/src",
]

root = os.path.dirname(__file__)
for phase in phases:
    path = os.path.abspath(os.path.join(root, phase))
    if path not in sys.path:
        sys.path.insert(0, path)
