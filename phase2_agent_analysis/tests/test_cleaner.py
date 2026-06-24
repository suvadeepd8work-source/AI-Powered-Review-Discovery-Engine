import unittest
import sys
import os
from unittest.mock import MagicMock

# Adjust path to import src modules properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cleaner import ReviewCleanerAgent, DataCleanerAgent
from models import CleanedReviewOutput


class TestCleanerAgent(unittest.TestCase):

    def test_cleaner_agent_fallback(self):
        # Create cleaner without API Key
        cleaner = ReviewCleanerAgent(api_key=None)
        raw_text = "Hallo world!!!"
        result = cleaner.clean_review(raw_text)
        self.assertEqual(result.cleaned_text, raw_text)
        self.assertEqual(result.language, "en")
        self.assertFalse(result.is_spam)

    def test_cleaner_agent_with_mock_client(self):
        cleaner = ReviewCleanerAgent(api_key="mock-key")
        mock_output = CleanedReviewOutput(
            cleaned_text="Hello world",
            language="de",
            is_spam=False
        )
        
        # Mocking the instructor patched client call
        cleaner.client = MagicMock()
        cleaner.client.chat.completions.create.return_value = mock_output

        result = cleaner.clean_review("Hallo Welt")
        self.assertEqual(result.cleaned_text, "Hello world")
        self.assertEqual(result.language, "de")
        self.assertFalse(result.is_spam)


class TestDataCleanerPipeline(unittest.TestCase):

    def test_is_empty(self):
        self.assertTrue(DataCleanerAgent.is_empty(""))
        self.assertTrue(DataCleanerAgent.is_empty("   "))
        self.assertFalse(DataCleanerAgent.is_empty("Hello world"))

    def test_is_too_short(self):
        self.assertTrue(DataCleanerAgent.is_too_short("too short"))
        self.assertTrue(DataCleanerAgent.is_too_short("one two three four"))
        self.assertFalse(DataCleanerAgent.is_too_short("one two three four five"))
        self.assertFalse(DataCleanerAgent.is_too_short("this is a longer review content"))
        self.assertTrue(DataCleanerAgent.is_too_short("one two three 👍"))

    def test_is_emoji_only(self):
        self.assertTrue(DataCleanerAgent.is_emoji_only("👍👍👍"))
        self.assertTrue(DataCleanerAgent.is_emoji_only("😊"))
        self.assertTrue(DataCleanerAgent.is_emoji_only("🔥!!! 😊"))
        self.assertFalse(DataCleanerAgent.is_emoji_only("This is great 👍"))

    def test_clean_flow_with_mock_agent(self):
        # Mock cleaner agent
        mock_agent = MagicMock()
        
        # We will clean 3 reviews that pass initial filters
        # Review 1: "This is a great app!" -> cleaned to "This is a great app!", en, non-spam
        # Review 2: "Esto es una buena app" -> cleaned/translated to "This is a good app", en, non-spam
        # Review 3: "Spam message buy bitcoins online" -> cleaned to "Spam message buy bitcoins online", en, spam
        # Review 4: "Cannot be translated text here" -> cleaned to "Cannot be translated text here", fr, non-spam
        
        mock_agent.clean_review.side_effect = [
            CleanedReviewOutput(cleaned_text="This is a great app!", language="en", is_spam=False),
            CleanedReviewOutput(cleaned_text="This is a good app", language="en", is_spam=False),
            CleanedReviewOutput(cleaned_text="Spam message buy bitcoins online", language="en", is_spam=True),
            CleanedReviewOutput(cleaned_text="Cannot be translated text here", language="fr", is_spam=False)
        ]

        mock_reviews = [
            {"review": "", "rating": 5, "review_date": "2026-06-25", "app_version": "1.0", "thumbs_up_count": 0}, # empty
            {"review": "👍👍👍", "rating": 5, "review_date": "2026-06-25", "app_version": "1.0", "thumbs_up_count": 0}, # emoji-only
            {"review": "Too short", "rating": 5, "review_date": "2026-06-25", "app_version": "1.0", "thumbs_up_count": 0}, # too short
            {"review": "This is a great app!", "rating": 5, "review_date": "2026-06-25", "app_version": "1.0", "thumbs_up_count": 0}, # valid 1
            {"review": "this is a great app!", "rating": 4, "review_date": "2026-06-25", "app_version": "1.0", "thumbs_up_count": 0}, # duplicate (case-insensitive)
            {"review": "Esto es una buena app", "rating": 5, "review_date": "2026-06-25", "app_version": "1.0", "thumbs_up_count": 0}, # valid 2 (translated)
            {"review": "Spam message buy bitcoins online", "rating": 1, "review_date": "2026-06-25", "app_version": "1.0", "thumbs_up_count": 0}, # spam
            {"review": "Cannot be translated text here", "rating": 3, "review_date": "2026-06-25", "app_version": "1.0", "thumbs_up_count": 0}, # non-English
        ]

        agent = DataCleanerAgent(input_path="mock", output_dir="mock", cleaner_agent=mock_agent)
        agent.load_reviews = lambda: mock_reviews
        agent.save = lambda result: None # No-op save

        result = agent.clean()
        filtered = result["filtered_reviews"]
        stats = result["statistics"]

        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["review"], "This is a great app!")
        self.assertEqual(filtered[1]["review"], "This is a good app")

        self.assertEqual(stats["total_input"], 8)
        self.assertEqual(stats["removed_empty"], 1)
        self.assertEqual(stats["removed_emoji_only"], 1)
        self.assertEqual(stats["removed_too_short"], 1)
        self.assertEqual(stats["removed_duplicate"], 1)
        self.assertEqual(stats["removed_spam"], 1)
        self.assertEqual(stats["removed_non_english"], 1)
        self.assertEqual(stats["total_output"], 2)


if __name__ == '__main__':
    unittest.main()
