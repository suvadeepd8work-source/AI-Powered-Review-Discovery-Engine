import unittest
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from insights import (  # type: ignore[import-not-found]
    ProductInsightAgent, ProductInsightPipeline,
    _aggregate_pain_points, _aggregate_feature_requests,
    _summarize_themes, _summarize_segments
)
from models import ProductInsight, ProductInsightSchema  # type: ignore[import-not-found]


# ── Fixtures ─────────────────────────────────────────────────────────────────

MOCK_ANALYZED_REVIEWS = [
    {"analysis": {"pain_points": ["app crashes", "too many ads"], "feature_requests": ["dark mode", "sleep timer"]}},
    {"analysis": {"pain_points": ["app crashes", "slow loading"], "feature_requests": ["sleep timer", "crossfade"]}},
    {"analysis": {"pain_points": ["too many ads", "shuffle broken"], "feature_requests": ["dark mode"]}},
    {"analysis": {"pain_points": [], "feature_requests": []}},
]

MOCK_THEMES = [
    {
        "theme_name": "Performance",
        "description": "App crashes and freezes.",
        "supporting_reviews": [
            {"review": "App crashes every day.", "rating": 1, "review_date": "2026-06-25"},
            {"review": "Black screen after update.", "rating": 1, "review_date": "2026-06-25"}
        ]
    },
    {
        "theme_name": "Advertisements",
        "description": "Too many ads on free tier.",
        "supporting_reviews": [
            {"review": "Ads after every single song.", "rating": 2, "review_date": "2026-06-25"}
        ]
    }
]

MOCK_SEGMENTS = [
    {
        "segment_name": "Free Users",
        "description": "Non-paying users frustrated by ad limits.",
        "review_count": 120,
        "traits": ["Uses free tier", "Cannot skip"],
        "primary_challenges": ["Excessive ads"],
        "representative_reviews": []
    },
    {
        "segment_name": "Premium Subscribers",
        "description": "Paying users expecting performance.",
        "review_count": 85,
        "traits": ["Pays monthly", "Uses offline"],
        "primary_challenges": ["App crashes"],
        "representative_reviews": []
    }
]


def _make_mock_insight(title="Test Insight", category="Top Frustration", severity=8, frequency=50, impact=9):
    return ProductInsight(
        title=title,
        description="A test description for this insight.",
        category=category,
        severity=severity,
        frequency=frequency,
        impact=impact,
        affected_segments=["Free Users"],
        supporting_evidence=["Users report this constantly"],
        recommended_action="Fix it ASAP."
    )


# ── Helper function tests ─────────────────────────────────────────────────────

class TestAggregationHelpers(unittest.TestCase):

    def test_aggregate_pain_points_counts_correctly(self):
        result = _aggregate_pain_points(MOCK_ANALYZED_REVIEWS, top_n=10)
        counts = {item["text"]: item["count"] for item in result}
        self.assertEqual(counts.get("app crashes"), 2)
        self.assertEqual(counts.get("too many ads"), 2)
        self.assertEqual(counts.get("slow loading"), 1)
        self.assertEqual(counts.get("shuffle broken"), 1)

    def test_aggregate_pain_points_top_n_limit(self):
        result = _aggregate_pain_points(MOCK_ANALYZED_REVIEWS, top_n=2)
        self.assertLessEqual(len(result), 2)

    def test_aggregate_feature_requests_counts_correctly(self):
        result = _aggregate_feature_requests(MOCK_ANALYZED_REVIEWS, top_n=10)
        counts = {item["text"]: item["count"] for item in result}
        self.assertEqual(counts.get("dark mode"), 2)
        self.assertEqual(counts.get("sleep timer"), 2)
        self.assertEqual(counts.get("crossfade"), 1)

    def test_aggregate_skips_empty_strings(self):
        reviews = [{"analysis": {"pain_points": ["", "  ", "real issue"], "feature_requests": []}}]
        result = _aggregate_pain_points(reviews, top_n=10)
        texts = [r["text"] for r in result]
        self.assertIn("real issue", texts)
        self.assertNotIn("", texts)
        self.assertNotIn("  ", texts)

    def test_summarize_themes_caps_reviews(self):
        long_theme = {
            "theme_name": "Performance",
            "description": "Crashes.",
            "supporting_reviews": [
                {"review": f"Review {i}", "rating": 1, "review_date": "2026-06-25"}
                for i in range(20)
            ]
        }
        result = _summarize_themes([long_theme])
        self.assertLessEqual(len(result[0]["sample_reviews"]), 5)
        self.assertEqual(result[0]["review_count"], 20)

    def test_summarize_segments_structure(self):
        result = _summarize_segments(MOCK_SEGMENTS)
        self.assertEqual(len(result), 2)
        self.assertIn("segment_name", result[0])
        self.assertIn("review_count", result[0])
        self.assertIn("primary_challenges", result[0])


# ── Agent unit tests ──────────────────────────────────────────────────────────

class TestProductInsightAgent(unittest.TestCase):

    def test_fallback_returns_valid_schema(self):
        agent = ProductInsightAgent(api_key=None)
        pain_counts = {"app crashes": 25, "too many ads": 30, "shuffle broken": 10}
        feat_counts  = {"dark mode": 20, "sleep timer": 15}
        result = agent._fallback_insights(pain_counts, feat_counts)

        self.assertIsInstance(result, ProductInsightSchema)
        self.assertGreater(len(result.top_frustrations), 0)
        self.assertGreater(len(result.feature_requests), 0)
        self.assertGreater(len(result.quick_wins), 0)
        self.assertGreater(len(result.long_term_opportunities), 0)

    def test_fallback_insights_have_valid_scores(self):
        agent = ProductInsightAgent(api_key=None)
        result = agent._fallback_insights({}, {})

        for ins in result.top_frustrations + result.feature_requests + result.quick_wins + result.long_term_opportunities:
            self.assertIsInstance(ins, ProductInsight)
            self.assertGreaterEqual(ins.severity, 1)
            self.assertLessEqual(ins.severity, 10)
            self.assertGreaterEqual(ins.impact, 1)
            self.assertLessEqual(ins.impact, 10)
            self.assertGreater(ins.frequency, 0)
            self.assertGreater(len(ins.title), 0)
            self.assertGreater(len(ins.recommended_action), 0)

    def test_generate_insights_with_mock_client(self):
        agent = ProductInsightAgent(api_key="mock-key")
        mock_output = ProductInsightSchema(
            top_frustrations=[_make_mock_insight("App crashes", "Top Frustration")],
            feature_requests=[_make_mock_insight("Sleep timer", "Feature Request", severity=5, impact=6)],
            quick_wins=[_make_mock_insight("Reduce first ad", "Quick Win", severity=4, impact=7)],
            long_term_opportunities=[_make_mock_insight("AI recommendations", "Long-term Opportunity", severity=6, impact=10)]
        )
        agent.client = MagicMock()
        agent.client.chat.completions.create.return_value = mock_output

        result = agent.generate_insights(
            themes=MOCK_THEMES,
            segments=MOCK_SEGMENTS,
            top_pain_points=[{"text": "app crashes", "count": 25}],
            top_feature_requests=[{"text": "sleep timer", "count": 15}]
        )

        self.assertEqual(len(result.top_frustrations), 1)
        self.assertEqual(result.top_frustrations[0].title, "App crashes")
        self.assertEqual(len(result.feature_requests), 1)
        self.assertEqual(len(result.quick_wins), 1)
        self.assertEqual(len(result.long_term_opportunities), 1)

    def test_generate_insights_raises_after_all_retries(self):
        """generate_insights re-raises after all tenacity retries (pipeline handles the fallback)."""
        agent = ProductInsightAgent(api_key="mock-key")
        agent.client = MagicMock()
        agent.client.chat.completions.create.side_effect = Exception("503 Service Unavailable")

        with self.assertRaises(Exception) as ctx:
            agent.generate_insights(
                themes=MOCK_THEMES,
                segments=MOCK_SEGMENTS,
                top_pain_points=[{"text": "crashes", "count": 10}],
                top_feature_requests=[{"text": "sleep timer", "count": 5}]
            )
        self.assertIn("503", str(ctx.exception))


# ── Pipeline integration tests ────────────────────────────────────────────────

class TestProductInsightPipeline(unittest.TestCase):

    def test_pipeline_end_to_end_with_mock_data(self):
        mock_agent = MagicMock()
        mock_agent.generate_insights.return_value = ProductInsightSchema(
            top_frustrations=[_make_mock_insight("App crashes", "Top Frustration")],
            feature_requests=[_make_mock_insight("Sleep timer", "Feature Request", severity=5, impact=6)],
            quick_wins=[_make_mock_insight("Reduce first ad", "Quick Win", severity=4, impact=7)],
            long_term_opportunities=[_make_mock_insight("AI recs", "Long-term Opportunity", severity=6, impact=10)]
        )

        pipeline = ProductInsightPipeline(
            analyzed_reviews_path="mock",
            themes_path="mock_themes",
            segments_path="mock_segments",
            output_dir="mock_out",
            insight_agent=mock_agent
        )
        pipeline.load_data = lambda: (MOCK_ANALYZED_REVIEWS, MOCK_THEMES, MOCK_SEGMENTS)
        pipeline.save = lambda result: None  # No-op

        result = pipeline.analyze()

        self.assertIsInstance(result, ProductInsightSchema)
        self.assertEqual(len(result.top_frustrations), 1)
        mock_agent.generate_insights.assert_called_once()

    def test_pipeline_passes_correct_aggregated_data(self):
        """Verify the pipeline correctly counts pain points and feature requests before sending to agent."""
        captured = {}
        mock_agent = MagicMock()

        def capture_call(**kwargs):
            captured.update(kwargs)
            return ProductInsightSchema(
                top_frustrations=[], feature_requests=[], quick_wins=[], long_term_opportunities=[]
            )

        mock_agent.generate_insights.side_effect = lambda **kw: capture_call(**kw)

        pipeline = ProductInsightPipeline(
            analyzed_reviews_path="mock",
            themes_path="mock",
            segments_path="mock",
            output_dir="mock",
            insight_agent=mock_agent
        )
        pipeline.load_data = lambda: (MOCK_ANALYZED_REVIEWS, MOCK_THEMES, MOCK_SEGMENTS)
        pipeline.save = lambda result: None

        pipeline.analyze()

        # Verify top_pain_points contains "app crashes" with count 2
        pp_texts = {p["text"]: p["count"] for p in captured.get("top_pain_points", [])}
        self.assertEqual(pp_texts.get("app crashes"), 2)
        fr_texts = {f["text"]: f["count"] for f in captured.get("top_feature_requests", [])}
        self.assertEqual(fr_texts.get("dark mode"), 2)

    def test_pipeline_uses_fallback_when_themes_missing(self):
        """Pipeline still runs if themes.json doesn't exist."""
        mock_agent = MagicMock()
        mock_agent.generate_insights.return_value = ProductInsightSchema(
            top_frustrations=[], feature_requests=[], quick_wins=[], long_term_opportunities=[]
        )

        pipeline = ProductInsightPipeline(
            analyzed_reviews_path="mock",
            themes_path="/nonexistent/themes.json",
            segments_path="/nonexistent/segments.json",
            output_dir="mock",
            insight_agent=mock_agent
        )
        pipeline.load_data = lambda: (MOCK_ANALYZED_REVIEWS, [], [])  # Empty themes/segments
        pipeline.save = lambda result: None

        result = pipeline.analyze()
        self.assertIsInstance(result, ProductInsightSchema)


if __name__ == '__main__':
    unittest.main()
