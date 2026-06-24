import unittest
import sys
import os
from unittest.mock import MagicMock

# Adjust path to import src modules properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from report import ExecutiveReportAgent, ExecutiveReportPipeline  # type: ignore[import-not-found]
from models import (  # type: ignore[import-not-found]
    ExecutiveReportSchema, ExecutiveReportMetrics, ExecutiveReportTheme,
    ExecutiveReportSegment, ExecutiveReportInsight, ExecutiveReportPriorityMatrix,
    ExecutiveReportRecommendation
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

MOCK_ANALYZED_REVIEWS = [
    {
        "rating": 5,
        "analysis": {"sentiment": "positive", "emotion": "satisfaction", "pain_points": [], "feature_requests": ["dark mode"]}
    },
    {
        "rating": 2,
        "analysis": {"sentiment": "negative", "emotion": "frustration", "pain_points": ["app crashes"], "feature_requests": []}
    },
    {
        "rating": 3,
        "analysis": {"sentiment": "neutral", "emotion": "neutral", "pain_points": ["too many ads"], "feature_requests": ["equalizer"]}
    }
]

MOCK_THEMES = [
    ExecutiveReportTheme(theme_name="Performance", description="App crashes", review_count=1, percentage=50.0),
    ExecutiveReportTheme(theme_name="Advertisements", description="Too many ads", review_count=1, percentage=50.0)
]

MOCK_SEGMENTS = [
    ExecutiveReportSegment(segment_name="Premium Subscribers", description="Paying users", review_count=1, percentage=33.33),
    ExecutiveReportSegment(segment_name="Casual Listeners", description="Free users", review_count=2, percentage=66.67)
]

MOCK_INSIGHTS_JSON = {
    "top_frustrations": [
        {
            "title": "App Crashes",
            "description": "App crashes frequently",
            "category": "Top Frustration",
            "severity": 9,
            "impact": 8,
            "affected_segments": ["Premium Subscribers"],
            "recommended_action": "Fix crashes"
        }
    ],
    "feature_requests": [
        {
            "title": "Dark Mode",
            "description": "Users want dark mode",
            "category": "Feature Request",
            "severity": 6,
            "impact": 7,
            "affected_segments": ["Casual Listeners"],
            "recommended_action": "Add dark mode"
        }
    ],
    "quick_wins": [],
    "long_term_opportunities": []
}


# ── Tests ────────────────────────────────────────────────────────────────────

class TestExecutiveReportAgent(unittest.TestCase):

    def test_report_agent_fallback_heuristics(self):
        agent = ExecutiveReportAgent(api_key=None)
        agent.client = None  # Ensure client is None to run fallback path

        metrics = ExecutiveReportMetrics(
            total_reviews=3,
            average_rating=3.33,
            sentiment_distribution={},
            emotion_distribution={},
            total_pain_points=2,
            total_feature_requests=2
        )

        result = agent.generate_report(metrics, MOCK_THEMES, MOCK_SEGMENTS, MOCK_INSIGHTS_JSON)

        self.assertIsInstance(result, ExecutiveReportSchema)
        self.assertEqual(result.key_metrics.total_reviews, 3)
        self.assertEqual(len(result.top_themes), 2)
        self.assertEqual(len(result.user_segments), 2)
        self.assertGreater(len(result.major_pain_points), 0)
        self.assertGreater(len(result.recommendations), 0)
        self.assertGreater(len(result.priority_matrix.do_now), 0)

    def test_report_agent_with_mock_client(self):
        agent = ExecutiveReportAgent(api_key="mock-key")
        mock_output = ExecutiveReportSchema(
            executive_summary="This is a mock summary.",
            key_metrics=ExecutiveReportMetrics(
                total_reviews=3,
                average_rating=3.33,
                sentiment_distribution={},
                emotion_distribution={},
                total_pain_points=2,
                total_feature_requests=2
            ),
            top_themes=MOCK_THEMES,
            user_segments=MOCK_SEGMENTS,
            major_pain_points=[
                ExecutiveReportInsight(
                    title="Mock Pain", description="Detail", category="Top Frustration",
                    severity=9, impact=9, priority_score=81, affected_segments=["Casual Listeners"],
                    recommended_action="Fix it"
                )
            ],
            feature_requests=[],
            priority_matrix=ExecutiveReportPriorityMatrix(do_now=["Mock Pain"], quick_wins=[], plan=[], backlog=[]),
            recommendations=[
                ExecutiveReportRecommendation(
                    title="Mock Rec", description="Do mock things", timeframe="Immediate",
                    actionable_steps=["Step 1"]
                )
            ]
        )

        agent.client = MagicMock()
        agent.client.chat.completions.create.return_value = mock_output

        metrics = ExecutiveReportMetrics(
            total_reviews=3,
            average_rating=3.33,
            sentiment_distribution={},
            emotion_distribution={},
            total_pain_points=2,
            total_feature_requests=2
        )

        result = agent.generate_report(metrics, MOCK_THEMES, MOCK_SEGMENTS, MOCK_INSIGHTS_JSON)

        self.assertEqual(result.executive_summary, "This is a mock summary.")
        self.assertEqual(len(result.major_pain_points), 1)
        self.assertEqual(result.major_pain_points[0].title, "Mock Pain")


class TestExecutiveReportPipeline(unittest.TestCase):

    def test_calculate_metrics_correctly(self):
        pipeline = ExecutiveReportPipeline(
            analyzed_reviews_path="mock", themes_path="mock", segments_path="mock",
            insights_path="mock", output_dir="mock"
        )
        metrics = pipeline.calculate_metrics(MOCK_ANALYZED_REVIEWS)

        self.assertEqual(metrics.total_reviews, 3)
        self.assertEqual(metrics.average_rating, 3.33)
        self.assertEqual(metrics.total_pain_points, 2)
        self.assertEqual(metrics.total_feature_requests, 2)

        # Check sentiment distributions
        self.assertIn("positive", metrics.sentiment_distribution)
        self.assertEqual(metrics.sentiment_distribution["positive"]["count"], 1)
        self.assertEqual(metrics.sentiment_distribution["positive"]["percentage"], 33.33)

        # Check emotion distributions
        self.assertIn("frustration", metrics.emotion_distribution)
        self.assertEqual(metrics.emotion_distribution["frustration"]["count"], 1)

    def test_calculate_metrics_empty(self):
        pipeline = ExecutiveReportPipeline(
            analyzed_reviews_path="mock", themes_path="mock", segments_path="mock",
            insights_path="mock", output_dir="mock"
        )
        metrics = pipeline.calculate_metrics([])
        self.assertEqual(metrics.total_reviews, 0)
        self.assertEqual(metrics.average_rating, 0.0)

    def test_generate_markdown_structure(self):
        pipeline = ExecutiveReportPipeline(
            analyzed_reviews_path="mock", themes_path="mock", segments_path="mock",
            insights_path="mock", output_dir="mock"
        )

        metrics = ExecutiveReportMetrics(
            total_reviews=3,
            average_rating=3.33,
            sentiment_distribution={"positive": {"count": 1, "percentage": 33.33}},
            emotion_distribution={"satisfaction": {"count": 1, "percentage": 33.33}},
            total_pain_points=2,
            total_feature_requests=2
        )

        report = ExecutiveReportSchema(
            executive_summary="This app has issues.",
            key_metrics=metrics,
            top_themes=MOCK_THEMES,
            user_segments=MOCK_SEGMENTS,
            major_pain_points=[
                ExecutiveReportInsight(
                    title="Mock Pain", description="Detail", category="Top Frustration",
                    severity=9, impact=9, priority_score=81, affected_segments=["Casual Listeners"],
                    recommended_action="Fix it"
                )
            ],
            feature_requests=[],
            priority_matrix=ExecutiveReportPriorityMatrix(do_now=["Mock Pain"], quick_wins=[], plan=[], backlog=[]),
            recommendations=[
                ExecutiveReportRecommendation(
                    title="Mock Rec", description="Do mock things", timeframe="Immediate",
                    actionable_steps=["Step 1"]
                )
            ]
        )

        md = pipeline.generate_markdown(report)

        self.assertIn("# Executive Report: Music App Review Analysis & Strategy", md)
        self.assertIn("## 1. Executive Summary", md)
        self.assertIn("This app has issues.", md)
        self.assertIn("## 2. Key Metrics", md)
        self.assertIn("## 3. Top Theme Clusters", md)
        self.assertIn("## 4. User Behavioral Segments", md)
        self.assertIn("## 5. Major User Pain Points", md)
        self.assertIn("## 7. Priority Matrix", md)
        self.assertIn("## 8. Tactical Recommendations & Roadmap", md)


if __name__ == '__main__':
    unittest.main()
