"""
tests/test_routes.py — Comprehensive API endpoint tests for Phase 4.

Coverage:
  - GET /                         root endpoint
  - GET /api/health               health check (data present / absent)
  - GET /api/reviews              default, q search, sentiment/category/platform filter, pagination
  - GET /api/insights/themes      with data / no data
  - GET /api/insights/segments    with data / no data
  - GET /api/insights/insights    with data / no data
  - GET /api/insights/report      with report / no report
  - GET /api/insights/latest      aggregated snapshot
  - POST /api/pipeline/run        trigger returns run_id
  - GET /api/pipeline/status/{id} status from DB / 404 for unknown run_id

All tests use FastAPI TestClient. File I/O is patched via
unittest.mock.patch so tests run offline without real pipeline output.
The pipeline DB dependency is satisfied with an in-memory SQLite session.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Adjust path so src modules are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from fastapi.testclient import TestClient
from main import app

# ---------------------------------------------------------------------------
# Sample fixtures
# ---------------------------------------------------------------------------

SAMPLE_REVIEWS = [
    {
        "id": "r1",
        "review_text": "Recommendations always play the same songs, very frustrating.",
        "sentiment": "negative",
        "category": "recommendation",
        "rating": 2,
        "platform": "android",
        "extracted_barriers": ["repetitive recommendations"],
    },
    {
        "id": "r2",
        "review_text": "Sound quality is excellent, love the audio experience.",
        "sentiment": "positive",
        "category": "audio",
        "rating": 5,
        "platform": "ios",
        "extracted_barriers": [],
    },
    {
        "id": "r3",
        "review_text": "Hard to find new music, the search is broken.",
        "sentiment": "negative",
        "category": "search",
        "rating": 1,
        "platform": "android",
        "extracted_barriers": ["poor search"],
    },
]

SAMPLE_THEMES = [
    {
        "theme_id": "t1",
        "title": "Repetitive Recommendations",
        "description": "Users report the same songs being recommended repeatedly.",
        "representative_reviews": ["Always the same songs.", "No variety."],
        "review_count": 42,
    },
    {
        "theme_id": "t2",
        "title": "Audio Quality Praise",
        "description": "Users highlight excellent audio clarity.",
        "representative_reviews": ["Crystal clear sound."],
        "review_count": 18,
    },
]

SAMPLE_SEGMENTS = [
    {
        "segment_id": "s1",
        "label": "Casual Listener",
        "traits": ["listens for 30 min/day", "prefers familiar artists"],
        "challenges": ["wants variety without effort"],
        "review_count": 55,
        "listening_behaviors": ["background listening"],
    },
]

SAMPLE_INSIGHTS = [
    {
        "insight_id": "i1",
        "opportunity": "Improve discovery algorithm diversity",
        "target_segment": "Casual Listener",
        "impact_score": 0.87,
        "feature_requests": ["shuffle across genres"],
        "pain_points": ["repetitive recommendations"],
    },
]

SAMPLE_REPORT_JSON = {
    "generated_at": "2026-06-25T12:00:00Z",
    "summary": "Users want better music discovery.",
    "metrics": {"total_reviews": 100},
}

SAMPLE_REPORT_MD = "# Executive Report\n\n## Summary\nUsers want better music discovery."


# ---------------------------------------------------------------------------
# Helper — build a mock DataLoader
# ---------------------------------------------------------------------------

def _mock_loader(
    reviews=None,
    themes=None,
    segments=None,
    insights=None,
    report_json=None,
    report_md=None,
    data_available=True,
    report_available=True,
):
    m = MagicMock()
    m.load_analyzed_reviews.return_value = reviews if reviews is not None else []
    m.load_themes.return_value            = themes  if themes  is not None else []
    m.load_segments.return_value          = segments if segments is not None else []
    m.load_insights.return_value          = insights if insights is not None else []
    m.load_report_json.return_value       = report_json
    m.load_report_markdown.return_value   = report_md
    m.data_available.return_value         = data_available
    m.report_available.return_value       = report_available
    return m


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRootAndHealth(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    # ── Root ──────────────────────────────────────────────────────────────

    def test_root_returns_200(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("project", data)
        self.assertIn("status", data)
        self.assertIn("endpoints", data)

    # ── Health — data present ─────────────────────────────────────────────

    @patch("routes.health.loader", _mock_loader(data_available=True, report_available=True))
    def test_health_ok_when_data_present(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["data_available"])
        self.assertTrue(data["report_available"])
        self.assertIn("version", data)

    # ── Health — no data ─────────────────────────────────────────────────

    @patch("routes.health.loader", _mock_loader(data_available=False, report_available=False))
    def test_health_degraded_when_no_data(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "degraded")
        self.assertFalse(data["data_available"])


class TestReviewsEndpoint(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def _patch_loader(self, reviews):
        return patch("routes.reviews.loader", _mock_loader(reviews=reviews))

    # ── Default (no filters) ─────────────────────────────────────────────

    def test_reviews_default_returns_all(self):
        with self._patch_loader(SAMPLE_REVIEWS):
            resp = self.client.get("/api/reviews")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("reviews", data)
        self.assertIn("total", data)
        self.assertEqual(data["total"], 3)
        self.assertEqual(len(data["reviews"]), 3)

    # ── Empty dataset ─────────────────────────────────────────────────────

    def test_reviews_empty_when_no_data(self):
        with self._patch_loader([]):
            resp = self.client.get("/api/reviews")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["total"], 0)

    # ── Full-text search ──────────────────────────────────────────────────

    def test_reviews_full_text_search(self):
        with self._patch_loader(SAMPLE_REVIEWS):
            resp = self.client.get("/api/reviews?q=frustrating")
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertIn("frustrating", data["reviews"][0]["review_text"].lower())

    # ── Sentiment filter ──────────────────────────────────────────────────

    def test_reviews_filter_by_sentiment(self):
        with self._patch_loader(SAMPLE_REVIEWS):
            resp = self.client.get("/api/reviews?sentiment=positive")
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["reviews"][0]["sentiment"], "positive")

    # ── Category filter ───────────────────────────────────────────────────

    def test_reviews_filter_by_category(self):
        with self._patch_loader(SAMPLE_REVIEWS):
            resp = self.client.get("/api/reviews?category=recommendation")
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["reviews"][0]["category"], "recommendation")

    # ── Platform filter ───────────────────────────────────────────────────

    def test_reviews_filter_by_platform(self):
        with self._patch_loader(SAMPLE_REVIEWS):
            resp = self.client.get("/api/reviews?platform=ios")
        data = resp.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["reviews"][0]["platform"], "ios")

    # ── Pagination ────────────────────────────────────────────────────────

    def test_reviews_pagination_limit(self):
        with self._patch_loader(SAMPLE_REVIEWS):
            resp = self.client.get("/api/reviews?limit=2&offset=0")
        data = resp.json()
        self.assertEqual(data["total"], 3)     # total unchanged
        self.assertEqual(len(data["reviews"]), 2)  # only 2 returned

    def test_reviews_pagination_offset(self):
        with self._patch_loader(SAMPLE_REVIEWS):
            resp = self.client.get("/api/reviews?limit=10&offset=2")
        data = resp.json()
        self.assertEqual(len(data["reviews"]), 1)  # only 1 left after offset=2

    # ── Response structure ────────────────────────────────────────────────

    def test_reviews_response_structure(self):
        with self._patch_loader(SAMPLE_REVIEWS):
            resp = self.client.get("/api/reviews")
        review = resp.json()["reviews"][0]
        for field in ("id", "review_text", "sentiment", "category", "rating", "platform"):
            self.assertIn(field, review, f"Missing field: {field}")


class TestInsightsEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    # ── Themes ────────────────────────────────────────────────────────────

    def test_themes_with_data(self):
        with patch("routes.insights.loader", _mock_loader(themes=SAMPLE_THEMES)):
            resp = self.client.get("/api/insights/themes")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)
        self.assertIn("title", data[0])
        self.assertIn("review_count", data[0])

    def test_themes_empty_when_no_data(self):
        with patch("routes.insights.loader", _mock_loader(themes=[])):
            resp = self.client.get("/api/insights/themes")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    # ── Segments ──────────────────────────────────────────────────────────

    def test_segments_with_data(self):
        with patch("routes.insights.loader", _mock_loader(segments=SAMPLE_SEGMENTS)):
            resp = self.client.get("/api/insights/segments")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertIn("label", data[0])
        self.assertIn("traits", data[0])
        self.assertIn("challenges", data[0])

    def test_segments_empty_when_no_data(self):
        with patch("routes.insights.loader", _mock_loader(segments=[])):
            resp = self.client.get("/api/insights/segments")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    # ── Insights ──────────────────────────────────────────────────────────

    def test_insights_with_data(self):
        with patch("routes.insights.loader", _mock_loader(insights=SAMPLE_INSIGHTS)):
            resp = self.client.get("/api/insights/insights")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertIn("opportunity", data[0])
        self.assertIn("impact_score", data[0])

    def test_insights_empty_when_no_data(self):
        with patch("routes.insights.loader", _mock_loader(insights=[])):
            resp = self.client.get("/api/insights/insights")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    # ── Executive Report — available ──────────────────────────────────────

    def test_report_with_data(self):
        with patch("routes.insights.loader", _mock_loader(
            report_json=SAMPLE_REPORT_JSON,
            report_md=SAMPLE_REPORT_MD,
        )):
            resp = self.client.get("/api/insights/report")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["available"])
        self.assertIsNotNone(data["markdown_report"])
        self.assertIsNotNone(data["json_report"])
        self.assertEqual(data["generated_at"], "2026-06-25T12:00:00Z")

    # ── Executive Report — not available ──────────────────────────────────

    def test_report_not_available(self):
        with patch("routes.insights.loader", _mock_loader(
            report_json=None, report_md=None,
        )):
            resp = self.client.get("/api/insights/report")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["available"])
        self.assertIsNone(data["markdown_report"])

    # ── Latest Analysis — with data ───────────────────────────────────────

    def test_latest_analysis_with_data(self):
        with patch("routes.insights.loader", _mock_loader(
            reviews=SAMPLE_REVIEWS,
            themes=SAMPLE_THEMES,
            segments=SAMPLE_SEGMENTS,
            report_available=True,
        )):
            resp = self.client.get("/api/insights/latest")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["data_available"])
        self.assertEqual(data["total_reviews"], 3)
        self.assertEqual(data["total_themes"], 2)
        self.assertEqual(data["total_segments"], 1)
        self.assertIn("sentiment_distribution", data)
        dist = data["sentiment_distribution"]
        self.assertEqual(dist["positive"], 1)
        self.assertEqual(dist["negative"], 2)
        self.assertEqual(dist["neutral"], 0)
        self.assertIsNotNone(data["top_theme"])
        self.assertTrue(data["report_available"])

    # ── Latest Analysis — no data ─────────────────────────────────────────

    def test_latest_analysis_no_data(self):
        with patch("routes.insights.loader", _mock_loader(
            reviews=[], themes=[], segments=[],
            data_available=False, report_available=False,
        )):
            resp = self.client.get("/api/insights/latest")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["data_available"])


class TestPipelineEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    # ── POST /run ─────────────────────────────────────────────────────────

    @patch("routes.pipeline.AgentPipelineOrchestrator")
    @patch("routes.pipeline._run_pipeline_in_background")
    def test_pipeline_run_returns_run_id(self, mock_bg_run, mock_orch):
        mock_orch_inst = MagicMock()
        mock_orch_inst.create_run.return_value = "mocked-run-id-999"
        mock_orch.return_value = mock_orch_inst

        resp = self.client.post("/api/pipeline/run")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["run_id"], "mocked-run-id-999")
        self.assertEqual(data["status"], "pending")
        mock_bg_run.assert_called_once_with("mocked-run-id-999")

    # ── GET /status/{run_id} — found ──────────────────────────────────────

    def test_pipeline_status_found(self):
        import datetime
        from database import get_db
        from main import app as fastapi_app

        mock_run = MagicMock()
        mock_run.run_id = "test-run-123"
        mock_run.status = "completed"
        mock_run.current_phase = "reporting"
        mock_run.start_time = datetime.datetime(2026, 6, 25, 12, 0, 0)
        mock_run.end_time   = datetime.datetime(2026, 6, 25, 12, 5, 0)
        mock_run.total_execution_time_s = 300.0
        mock_run.error_message = None

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_run

        def override_get_db():
            yield mock_session

        fastapi_app.dependency_overrides[get_db] = override_get_db
        try:
            resp = self.client.get("/api/pipeline/status/test-run-123")
        finally:
            fastapi_app.dependency_overrides.clear()

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["run_id"], "test-run-123")
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["current_phase"], "reporting")
        self.assertIsNotNone(data["start_time"])


    # ── GET /status/{run_id} — not found ─────────────────────────────────

    def test_pipeline_status_not_found(self):
        from database import get_db
        from main import app as fastapi_app

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        def override_get_db():
            yield mock_session

        fastapi_app.dependency_overrides[get_db] = override_get_db
        try:
            resp = self.client.get("/api/pipeline/status/nonexistent-run")
        finally:
            fastapi_app.dependency_overrides.clear()

        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found", resp.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
