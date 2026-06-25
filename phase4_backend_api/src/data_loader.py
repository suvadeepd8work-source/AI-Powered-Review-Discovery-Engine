"""
data_loader.py — Loads Phase 2 agent output JSON files from disk.

All methods return empty collections / None gracefully when the files
don't exist (i.e., the pipeline hasn't run yet). Routes should handle
the empty case with a descriptive API response rather than crashing.
"""

import json
import os
from typing import Any, Optional

from config import (
    ANALYZED_REVIEWS_PATH,
    THEMES_PATH,
    SEGMENTS_PATH,
    INSIGHTS_PATH,
    REPORT_JSON_PATH,
    REPORT_MD_PATH,
)


def _load_json(path: str, default: Any = None) -> Any:
    """Load a JSON file; return *default* if it doesn't exist or is malformed."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _load_text(path: str) -> Optional[str]:
    """Load a plain-text file; return None if it doesn't exist."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


class DataLoader:
    """Centralised loader for all Phase 2 pipeline output files."""

    # ------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------

    def load_analyzed_reviews(self) -> list:
        """Return the list of analyzed review dicts, or [] if unavailable."""
        data = _load_json(ANALYZED_REVIEWS_PATH, default=[])
        if isinstance(data, list):
            return data
        # Some agents write {"reviews": [...]}
        if isinstance(data, dict):
            return data.get("reviews", [])
        return []

    # ------------------------------------------------------------------
    # Themes
    # ------------------------------------------------------------------

    def load_themes(self) -> list:
        """Return the list of theme cluster dicts, or [] if unavailable."""
        data = _load_json(THEMES_PATH, default=[])
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("themes", [])
        return []

    # ------------------------------------------------------------------
    # Segments
    # ------------------------------------------------------------------

    def load_segments(self) -> list:
        """Return the list of user segment dicts, or [] if unavailable."""
        data = _load_json(SEGMENTS_PATH, default=[])
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("segments", [])
        return []

    # ------------------------------------------------------------------
    # Insights
    # ------------------------------------------------------------------

    def load_insights(self) -> list:
        """Return the list of product insight dicts, or [] if unavailable."""
        data = _load_json(INSIGHTS_PATH, default=[])
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # insights.json may be {"opportunities": [...], "pain_points": [...]}
            val = data.get("opportunities") or data.get("insights")
            if isinstance(val, list):
                return val
        return []

    def load_insights_raw(self) -> dict:
        """Return the raw product_insights.json dict."""
        return _load_json(INSIGHTS_PATH, default={}) or {}

    # ------------------------------------------------------------------
    # Executive Report
    # ------------------------------------------------------------------

    def load_report_json(self) -> Optional[dict]:
        """Return the executive_report.json dict, or None if unavailable."""
        return _load_json(REPORT_JSON_PATH, default=None)

    def load_report_markdown(self) -> Optional[str]:
        """Return the executive_report.md text, or None if unavailable."""
        return _load_text(REPORT_MD_PATH)

    # ------------------------------------------------------------------
    # Availability helpers
    # ------------------------------------------------------------------

    def data_available(self) -> bool:
        """Return True if at least the analyzed_reviews file exists."""
        return os.path.exists(ANALYZED_REVIEWS_PATH)

    def report_available(self) -> bool:
        """Return True if both report files exist."""
        return os.path.exists(REPORT_JSON_PATH) and os.path.exists(REPORT_MD_PATH)


# Module-level singleton
loader = DataLoader()
