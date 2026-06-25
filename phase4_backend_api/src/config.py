"""
config.py — Central settings for the Phase 4 FastAPI backend.
All path resolution is relative to the project root so the API
works regardless of where uvicorn is launched from.
"""

import os

# Project root = two levels up from this file (phase4_backend_api/src/config.py)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ── Phase 2 data output directory ────────────────────────────────────────────
PHASE2_OUTPUT_DIR = os.path.join(ROOT_DIR, "phase2_agent_analysis", "data", "output")

# ── Phase 3 SQLite database ───────────────────────────────────────────────────
PHASE3_DB_PATH = os.path.join(ROOT_DIR, "phase3_orchestration", "pipeline_state.db")
PHASE3_DB_URL  = f"sqlite:///{PHASE3_DB_PATH}"

# ── Output file paths ─────────────────────────────────────────────────────────
ANALYZED_REVIEWS_PATH = os.path.join(PHASE2_OUTPUT_DIR, "analyzed_reviews.json")
THEMES_PATH           = os.path.join(PHASE2_OUTPUT_DIR, "themes.json")
SEGMENTS_PATH         = os.path.join(PHASE2_OUTPUT_DIR, "segments.json")
INSIGHTS_PATH         = os.path.join(PHASE2_OUTPUT_DIR, "product_insights.json")
REPORT_JSON_PATH      = os.path.join(PHASE2_OUTPUT_DIR, "executive_report.json")
REPORT_MD_PATH        = os.path.join(PHASE2_OUTPUT_DIR, "executive_report.md")

# ── API metadata ──────────────────────────────────────────────────────────────
API_VERSION = "1.0.0"
API_TITLE   = "AI-Powered Review Discovery Engine API"
