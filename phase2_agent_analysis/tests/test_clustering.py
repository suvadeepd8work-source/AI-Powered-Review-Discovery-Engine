import unittest
import sys
import os
from unittest.mock import MagicMock

# Adjust path to import src modules properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from clustering import ThemeClusteringAgent, ThemeClusteringPipeline
from models import ThemeClusterSchema, ThemeCluster, SupportingReviewItem


class TestThemeClusteringAgent(unittest.TestCase):

    def test_clustering_agent_fallback_heuristics(self):
        # Create agent without API Key (runs in fallback mode)
        agent = ThemeClusteringAgent(api_key=None)

        # Mock inputs representing user complaints
        mock_inputs = [
            {"review": "This app keeps crashing when playing in full screen.", "rating": 1, "review_date": "2026-06-25"},
            {"review": "I hate ads, too many advertisements!", "rating": 2, "review_date": "2026-06-25"},
            {"review": "The subscription is way too expensive, pure greed", "rating": 2, "review_date": "2026-06-25"},
            {"review": "Offline listening is broken, cannot download playlists", "rating": 1, "review_date": "2026-06-25"}
        ]

        result = agent._cluster_batch_fallback(mock_inputs)
        themes = {tc.theme_name: tc for tc in result.themes}

        # Verify themes are correctly classified
        self.assertIn("Performance", themes)
        self.assertIn("Advertisements", themes)
        self.assertIn("Pricing", themes)
        self.assertIn("Offline Listening", themes)

        # Verify descriptions are populated
        self.assertGreater(len(themes["Performance"].description), 0)
        
        # Verify supporting reviews count
        self.assertEqual(len(themes["Performance"].supporting_reviews), 1)
        self.assertEqual(themes["Performance"].supporting_reviews[0].review, "This app keeps crashing when playing in full screen.")

    def test_clustering_agent_with_mock_client(self):
        agent = ThemeClusteringAgent(api_key="mock-key")
        mock_output = ThemeClusterSchema(
            themes=[
                ThemeCluster(
                    theme_name="Performance",
                    description="App crashes and freezes.",
                    supporting_reviews=[
                        SupportingReviewItem(
                            review="This app keeps crashing when playing in full screen.",
                            rating=1,
                            review_date="2026-06-25"
                        )
                    ]
                )
            ]
        )

        agent.client = MagicMock()
        agent.client.chat.completions.create.return_value = mock_output

        mock_inputs = [
            {"review": "This app keeps crashing when playing in full screen.", "rating": 1, "review_date": "2026-06-25"}
        ]
        result = agent.cluster_batch(mock_inputs)
        
        self.assertEqual(len(result.themes), 1)
        self.assertEqual(result.themes[0].theme_name, "Performance")
        self.assertEqual(result.themes[0].supporting_reviews[0].review, "This app keeps crashing when playing in full screen.")


class TestThemeClusteringPipeline(unittest.TestCase):

    def test_clustering_pipeline_flow(self):
        mock_agent = MagicMock()
        mock_agent.cluster_batch.side_effect = [
            ThemeClusterSchema(
                themes=[
                    ThemeCluster(
                        theme_name="Pricing",
                        description="Subscription concerns",
                        supporting_reviews=[
                            SupportingReviewItem(
                                review="Too expensive.",
                                rating=2,
                                review_date="2026-06-25"
                            )
                        ]
                    )
                ]
            )
        ]

        mock_analyzed_reviews = [
            {
                "original_review": "Too expensive.",
                "rating": 2,
                "review_date": "2026-06-25",
                "analysis": {
                    "sentiment": "negative",
                    "pain_points": ["too expensive"]
                }
            },
            {
                "original_review": "Great app, highly recommend!",
                "rating": 5,
                "review_date": "2026-06-25",
                "analysis": {
                    "sentiment": "positive",
                    "pain_points": []
                }
            }
        ]

        pipeline = ThemeClusteringPipeline(
            input_path="mock",
            output_dir="mock",
            clustering_agent=mock_agent,
            batch_size=2
        )
        pipeline.load_reviews = lambda: mock_analyzed_reviews
        pipeline.save = lambda result: None  # No-op

        result = pipeline.analyze()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["theme_name"], "Pricing")
        self.assertEqual(len(result[0]["supporting_reviews"]), 1)
        self.assertEqual(result[0]["supporting_reviews"][0]["review"], "Too expensive.")


if __name__ == '__main__':
    unittest.main()
