import unittest
from fastapi.testclient import TestClient
import sys
import os

# Adjust path to import src modules properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from main import app

class TestApiRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("project", response.json())

    def test_get_reviews_default(self):
        response = self.client.get("/api/reviews")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        self.assertGreaterEqual(len(response.json()), 1)

    def test_get_reviews_filtered(self):
        response = self.client.get("/api/reviews?sentiment=negative")
        self.assertEqual(response.status_code, 200)
        for item in response.json():
            self.assertEqual(item["sentiment"], "negative")

    def test_pipeline_run_trigger(self):
        response = self.client.post("/api/pipeline/run")
        self.assertEqual(response.status_code, 200)
        self.assertIn("run_id", response.json())

if __name__ == '__main__':
    unittest.main()
