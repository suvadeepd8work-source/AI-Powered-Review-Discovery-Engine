import unittest
import sys
import os
from unittest.mock import MagicMock

# Adjust path to import src modules properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from segmentation import UserSegmentationAgent, UserSegmentationPipeline  # type: ignore[import-not-found]
from models import UserSegmentSchema, UserSegment, UserSegmentReview  # type: ignore[import-not-found]


class TestUserSegmentationAgent(unittest.TestCase):

    def test_segmentation_agent_fallback_casual_listener(self):
        """Free-tier casual listener review maps to 'Casual Listeners'."""
        agent = UserSegmentationAgent(api_key=None)
        mock_inputs = [
            {
                "review": "I just casually listen to background music sometimes using the free version.",
                "rating": 3,
                "review_date": "2026-06-25",
                "analysis": {"pain_points": [], "jobs_to_be_done": ["listen to music casually"]}
            }
        ]
        result = agent._segment_batch_fallback(mock_inputs)
        segment_names = [s.segment_name for s in result.segments]
        self.assertIn("Casual Listeners", segment_names)

    def test_segmentation_agent_fallback_student(self):
        """Student review maps to 'Students'."""
        agent = UserSegmentationAgent(api_key=None)
        mock_inputs = [
            {
                "review": "I'm a college student and I study while listening. The student discount should be cheaper!",
                "rating": 2,
                "review_date": "2026-06-25",
                "analysis": {"pain_points": ["too expensive"], "jobs_to_be_done": ["listen while studying"]}
            }
        ]
        result = agent._segment_batch_fallback(mock_inputs)
        segment_names = [s.segment_name for s in result.segments]
        self.assertIn("Students", segment_names)

    def test_segmentation_agent_fallback_premium_subscriber(self):
        """Premium subscriber review maps to 'Premium Subscribers'."""
        agent = UserSegmentationAgent(api_key=None)
        mock_inputs = [
            {
                "review": "I pay for premium and the app keeps crashing. Unacceptable for a subscription.",
                "rating": 1,
                "review_date": "2026-06-25",
                "analysis": {"pain_points": ["app crashes", "poor performance"], "jobs_to_be_done": []}
            }
        ]
        result = agent._segment_batch_fallback(mock_inputs)
        segment_names = [s.segment_name for s in result.segments]
        self.assertIn("Premium Subscribers", segment_names)

    def test_segmentation_agent_fallback_podcast_user(self):
        """Podcast user review maps to 'Podcast Users'."""
        agent = UserSegmentationAgent(api_key=None)
        mock_inputs = [
            {
                "review": "The podcast feature is broken. I use Spotify mainly for podcasts and episodes.",
                "rating": 2,
                "review_date": "2026-06-25",
                "analysis": {"pain_points": ["podcast broken"], "jobs_to_be_done": ["listen to podcasts"]}
            }
        ]
        result = agent._segment_batch_fallback(mock_inputs)
        segment_names = [s.segment_name for s in result.segments]
        self.assertIn("Podcast Users", segment_names)

    def test_segmentation_agent_fallback_fitness_user(self):
        """Fitness user review maps to 'Fitness Users'."""
        agent = UserSegmentationAgent(api_key=None)
        mock_inputs = [
            {
                "review": "I listen during my workout and gym sessions. Downloads keep failing on my treadmill.",
                "rating": 2,
                "review_date": "2026-06-25",
                "analysis": {"pain_points": ["offline fails"], "jobs_to_be_done": ["listen during workout"]}
            }
        ]
        result = agent._segment_batch_fallback(mock_inputs)
        segment_names = [s.segment_name for s in result.segments]
        self.assertIn("Fitness Users", segment_names)

    def test_segmentation_agent_fallback_regional_music_user(self):
        """Regional music user review maps to 'Regional Music Users'."""
        agent = UserSegmentationAgent(api_key=None)
        mock_inputs = [
            {
                "review": "The Bollywood and Hindi song catalog is very limited. I want more regional music.",
                "rating": 2,
                "review_date": "2026-06-25",
                "analysis": {"pain_points": ["missing bollywood songs"], "jobs_to_be_done": ["listen to hindi music"]}
            }
        ]
        result = agent._segment_batch_fallback(mock_inputs)
        segment_names = [s.segment_name for s in result.segments]
        self.assertIn("Regional Music Users", segment_names)

    def test_segmentation_agent_fallback_schema_validity(self):
        """Fallback output must return a valid UserSegmentSchema object."""
        agent = UserSegmentationAgent(api_key=None)
        mock_inputs = [
            {"review": "Ads are way too frequent on the free tier.", "rating": 2, "review_date": "2026-06-25", "analysis": {}},
            {"review": "I use premium and this app crashes daily.", "rating": 1, "review_date": "2026-06-25", "analysis": {}},
        ]
        result = agent._segment_batch_fallback(mock_inputs)
        self.assertIsInstance(result, UserSegmentSchema)
        self.assertGreater(len(result.segments), 0)
        for seg in result.segments:
            self.assertIsInstance(seg, UserSegment)
            self.assertGreater(len(seg.segment_name), 0)
            self.assertGreater(len(seg.description), 0)
            self.assertGreater(seg.review_count, 0)

    def test_segmentation_agent_with_mock_groq_client(self):
        """Mock Groq client response is correctly returned and processed."""
        agent = UserSegmentationAgent(api_key="mock-key")
        mock_output = UserSegmentSchema(
            segments=[
                UserSegment(
                    segment_name="Free Users",
                    description="Non-paying users bothered by limitations.",
                    traits=["Uses free tier", "Cannot skip freely"],
                    primary_challenges=["Excessive ads", "No offline access"],
                    jobs_to_be_done=["Listen to music for free", "Access basic features"],
                    representative_reviews=[
                        UserSegmentReview(
                            review="Can't skip songs and the ads are unbearable on the free version.",
                            rating=1,
                            review_date="2026-06-25"
                        )
                    ],
                    review_count=1
                )
            ]
        )
        agent.client = MagicMock()
        agent.client.chat.completions.create.return_value = mock_output

        mock_inputs = [
            {"review": "Can't skip songs and the ads are unbearable on the free version.", "rating": 1, "review_date": "2026-06-25"}
        ]
        result = agent.segment_batch(mock_inputs)

        self.assertEqual(len(result.segments), 1)
        self.assertEqual(result.segments[0].segment_name, "Free Users")
        self.assertEqual(result.segments[0].review_count, 1)
        self.assertEqual(result.segments[0].representative_reviews[0].review,
                         "Can't skip songs and the ads are unbearable on the free version.")


class TestUserSegmentationPipeline(unittest.TestCase):

    def test_pipeline_flow_with_mock_agent(self):
        """Pipeline correctly merges segment results across batches."""
        mock_agent = MagicMock()
        mock_agent.segment_batch.return_value = UserSegmentSchema(
            segments=[
                UserSegment(
                    segment_name="Free Users",
                    description="Non-paying users bothered by limitations.",
                    traits=["Uses free tier"],
                    primary_challenges=["Excessive ads"],
                    jobs_to_be_done=["Listen for free"],
                    representative_reviews=[
                        UserSegmentReview(
                            review="Too many ads in the free version.",
                            rating=2,
                            review_date="2026-06-25"
                        )
                    ],
                    review_count=2
                )
            ]
        )

        mock_analyzed_reviews = [
            {"original_review": "Too many ads in the free version.", "rating": 2, "review_date": "2026-06-25", "analysis": {}},
            {"original_review": "Can't skip songs on free tier.", "rating": 2, "review_date": "2026-06-25", "analysis": {}},
            {"original_review": "Great app for premium users!", "rating": 5, "review_date": "2026-06-25", "analysis": {}}
        ]

        pipeline = UserSegmentationPipeline(
            input_path="mock",
            output_dir="mock",
            segmentation_agent=mock_agent,
            batch_size=5
        )
        pipeline.load_reviews = lambda: mock_analyzed_reviews
        pipeline.save = lambda result: None  # No-op

        result = pipeline.analyze()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["segment_name"], "Free Users")
        self.assertEqual(result[0]["review_count"], 2)
        self.assertEqual(len(result[0]["representative_reviews"]), 1)

    def test_pipeline_fallback_on_api_error(self):
        """Pipeline falls back to heuristics when LLM API raises an exception."""
        mock_agent = MagicMock()
        mock_agent.segment_batch.side_effect = Exception("API connection failed")
        mock_agent._segment_batch_fallback.return_value = UserSegmentSchema(
            segments=[
                UserSegment(
                    segment_name="Casual Listeners",
                    description="Occasional listeners on free tier.",
                    traits=["Listens occasionally"],
                    primary_challenges=["Too many ads"],
                    jobs_to_be_done=["Enjoy music"],
                    representative_reviews=[
                        UserSegmentReview(
                            review="I just listen now and then, free version is okay.",
                            rating=3,
                            review_date="2026-06-25"
                        )
                    ],
                    review_count=1
                )
            ]
        )

        pipeline = UserSegmentationPipeline(
            input_path="mock",
            output_dir="mock",
            segmentation_agent=mock_agent,
            batch_size=5
        )
        pipeline.load_reviews = lambda: [
            {"original_review": "I just listen now and then, free version is okay.", "rating": 3, "review_date": "2026-06-25", "analysis": {}}
        ]
        pipeline.save = lambda result: None

        result = pipeline.analyze()

        # Should have fallen back and still returned segment results
        self.assertGreater(len(result), 0)
        mock_agent._segment_batch_fallback.assert_called_once()

    def test_pipeline_empty_reviews_returns_empty(self):
        """Pipeline returns empty list when no reviews are loaded."""
        mock_agent = MagicMock()
        pipeline = UserSegmentationPipeline(
            input_path="mock",
            output_dir="mock",
            segmentation_agent=mock_agent,
            batch_size=5
        )
        pipeline.load_reviews = lambda: []
        pipeline.save = lambda result: None

        result = pipeline.analyze()
        self.assertEqual(result, [])
        mock_agent.segment_batch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
