import unittest
import sys
import os
from datetime import datetime

# Adjust path to import src modules properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ingestion import ReviewIngestionPipeline
from schema import RawReviewSchema

class TestIngestionPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = ReviewIngestionPipeline(db_conn_str="sqlite:///:memory:")

    def test_validation_valid_record(self):
        valid_data = [{
            "review_text": "Love the recommendations, discovered 5 new songs today!",
            "rating": 5,
            "review_date": "2026-06-25T01:00:00Z",
            "app_version": "4.5.1",
            "platform": "ios"
        }]
        validated = self.pipeline.validate_records(valid_data)
        self.assertEqual(len(validated), 1)
        self.assertIsInstance(validated[0], RawReviewSchema)
        self.assertEqual(validated[0].rating, 5)

    def test_validation_invalid_rating(self):
        invalid_data = [{
            "review_text": "Bad suggestions.",
            "rating": 6, # Invalid rating
            "review_date": "2026-06-25T01:00:00Z",
            "platform": "android"
        }]
        validated = self.pipeline.validate_records(invalid_data)
        self.assertEqual(len(validated), 0)

    def test_validation_invalid_platform(self):
        invalid_data = [{
            "review_text": "Nice interface",
            "rating": 4,
            "review_date": "2026-06-25T01:00:00Z",
            "platform": "web" # Invalid platform
        }]
        validated = self.pipeline.validate_records(invalid_data)
        self.assertEqual(len(validated), 0)

if __name__ == '__main__':
    unittest.main()
