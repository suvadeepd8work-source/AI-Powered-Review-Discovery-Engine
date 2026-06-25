"""
database.py — SQLAlchemy session factory for the Phase 3 pipeline state DB.
Used by pipeline status routes to query PipelineRun records.
"""

import sys
import os

# Allow importing state_db from phase3_orchestration
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(root_dir, "phase3_orchestration", "src"))

from config import PHASE3_DB_URL
from state_db import init_db  # type: ignore[import-not-found]

# Module-level session factory (lazy — only connects when first used)
_SessionFactory = None


def get_session_factory():
    """Return (creating if needed) the SQLAlchemy session factory."""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = init_db(PHASE3_DB_URL)
    return _SessionFactory


def get_db():
    """FastAPI dependency: yields a DB session and closes it after the request."""
    Session = get_session_factory()
    session = Session()
    try:
        yield session
    finally:
        session.close()
