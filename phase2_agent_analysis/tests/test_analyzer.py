import unittest
import sys
import os
from unittest.mock import MagicMock

# Adjust path to import src modules properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from analyzer import ReviewAnalyzerAgent, DataAnalyzerPipeline  # type: ignore[import-not-found]
from models import AnalyzedReviewItem, AnalyzedReviewBatchOutput  # type: ignore[import-not-found]


class TestReviewAnalyzerAgent(unittest.TestCase):

    def test_analyzer_agent_fallback_heuristics(self):
        # Create analyzer without API Key
        analyzer = ReviewAnalyzerAgent(api_key=None)
        analyzer.client = None  # Ensure client is None to run fallback path
        
        # Test positive review detection
        res_pos = analyzer.analyze_review("I absolutely love this app, it is amazing!")
        self.assertEqual(res_pos.sentiment, "positive")
        self.assertEqual(res_pos.emotion, "satisfaction")
        self.assertGreater(len(res_pos.positive_feedback), 0)
        self.assertEqual(len(res_pos.pain_points), 0)

        # Test negative review detection
        res_neg = analyzer.analyze_review("This is the worst app, it keeps crashing and has errors.")
        self.assertEqual(res_neg.sentiment, "negative")
        self.assertEqual(res_neg.emotion, "frustration")
        self.assertGreater(len(res_neg.pain_points), 0)
        self.assertEqual(len(res_neg.positive_feedback), 0)

        # Test feature request heuristic
        res_req = analyzer.analyze_review("Please add a dark mode option.")
        self.assertGreater(len(res_req.feature_requests), 0)

        # Test JTBD heuristic
        res_jtbd = analyzer.analyze_review("I want to search for new music to play.")
        self.assertGreater(len(res_jtbd.jobs_to_be_done), 0)

    def test_analyzer_agent_with_mock_client(self):
        analyzer = ReviewAnalyzerAgent(api_key="mock-key")
        mock_output = AnalyzedReviewBatchOutput(
            batch_results=[
                AnalyzedReviewItem(
                    review_index=0,
                    sentiment="negative",
                    emotion="disappointment",
                    pain_points=["playlist boredom"],
                    feature_requests=["better shuffle mode"],
                    positive_feedback=[],
                    negative_feedback=["bad recommendations"],
                    jobs_to_be_done=["discover fresh indie tracks"]
                )
            ]
        )
        
        # Mocking the instructor patched client call
        analyzer.client = MagicMock()
        analyzer.client.chat.completions.create.return_value = mock_output

        result = analyzer.analyze_review("The recommendation engine keeps suggesting the same songs, please improve shuffle.")
        self.assertEqual(result.sentiment, "negative")
        self.assertEqual(result.emotion, "disappointment")
        self.assertEqual(result.pain_points, ["playlist boredom"])
        self.assertEqual(result.feature_requests, ["better shuffle mode"])


class TestDataAnalyzerPipeline(unittest.TestCase):

    def test_analyzer_pipeline_flow(self):
        # Mock agent to return structured results
        mock_agent = MagicMock()
        mock_agent.analyze_batch.side_effect = [
            AnalyzedReviewBatchOutput(
                batch_results=[
                    AnalyzedReviewItem(
                        review_index=0,
                        sentiment="positive",
                        emotion="satisfaction",
                        pain_points=[],
                        feature_requests=[],
                        positive_feedback=["great sound quality"],
                        negative_feedback=[],
                        jobs_to_be_done=["listen to study music"]
                    ),
                    AnalyzedReviewItem(
                        review_index=1,
                        sentiment="negative",
                        emotion="frustration",
                        pain_points=["app lags"],
                        feature_requests=["fix performance issues"],
                        positive_feedback=[],
                        negative_feedback=["slow search speed"],
                        jobs_to_be_done=["find pop tracks"]
                    )
                ]
            )
        ]

        mock_filtered_reviews = [
            {"review": "I love the sound quality of this app!", "rating": 5, "review_date": "2026-06-25", "app_version": "1.0", "thumbs_up_count": 2},
            {"review": "The app lags a lot when I try to search for tracks.", "rating": 2, "review_date": "2026-06-25", "app_version": "1.0", "thumbs_up_count": 0}
        ]

        pipeline = DataAnalyzerPipeline(input_path="mock", output_dir="mock", analyzer_agent=mock_agent, batch_size=2)
        setattr(pipeline, 'load_reviews', lambda: mock_filtered_reviews)
        setattr(pipeline, 'save', lambda _: None) # No-op

        result = pipeline.analyze()
        analyzed = result["analyzed_reviews"]
        stats = result["statistics"]

        self.assertEqual(len(analyzed), 2)
        self.assertEqual(analyzed[0]["analysis"]["sentiment"], "positive")
        self.assertEqual(analyzed[1]["analysis"]["sentiment"], "negative")
        self.assertEqual(analyzed[0]["analysis"]["emotion"], "satisfaction")
        self.assertEqual(analyzed[1]["analysis"]["emotion"], "frustration")
        
        self.assertEqual(stats["total_analyzed"], 2)
        self.assertEqual(stats["sentiment_counts"]["positive"], 1)
        self.assertEqual(stats["sentiment_counts"]["negative"], 1)
        self.assertEqual(stats["total_pain_points"], 1)
        self.assertEqual(stats["total_feature_requests"], 1)
        self.assertEqual(stats["total_positive_feedback"], 1)
        self.assertEqual(stats["total_negative_feedback"], 1)
        self.assertEqual(stats["total_jtbd"], 2)


if __name__ == '__main__':
    unittest.main()
