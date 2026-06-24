import os
import json
from datetime import datetime, timezone
from typing import Optional, List
from groq import Groq
import instructor
from tenacity import retry, stop_after_attempt, wait_exponential

from models import AnalyzedReviewOutput
from prompts import ANALYZER_SYSTEM_PROMPT

# --- Helper to load .env manually without external dependencies --------------
def load_dotenv(dotenv_path: str = ".env"):
    if os.path.exists(dotenv_path):
        print(f"[Dotenv] Loading environment variables from {dotenv_path}...")
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    # Strip quotes if any
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    os.environ[key] = val
    else:
        # Also check root directory of the workspace
        root_dotenv = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        if os.path.exists(root_dotenv):
            load_dotenv(root_dotenv)


# --- Load .env at import time ------------------------------------------------
load_dotenv()

INPUT_FILE = os.path.join("phase2_agent_analysis", "data", "output", "filtered_reviews.json")
OUTPUT_DIR = os.path.join("phase2_agent_analysis", "data", "output")


class ReviewAnalyzerAgent:
    """Agent 3 — Review Analyzer (Groq LLM with Instructor validation)"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.client = instructor.patch(Groq(api_key=self.api_key)) if self.api_key else None

    def _analyze_review_fallback(self, cleaned_text: str) -> AnalyzedReviewOutput:
        # Simple heuristic analysis fallback when API key is not present or calls fail
        sentiment = "neutral"
        emotion = "neutral"
        pain_points = []
        feature_requests = []
        positive_feedback = []
        negative_feedback = []
        jobs_to_be_done = []

        lower_text = cleaned_text.lower()

        # Heuristics for sentiment and emotion
        if any(w in lower_text for w in ["love", "great", "awesome", "excellent", "good", "amazing", "best", "perfect", "like"]):
            sentiment = "positive"
            emotion = "satisfaction"
            positive_feedback.append(cleaned_text)
        elif any(w in lower_text for w in ["bad", "stuck", "broken", "frustrated", "annoying", "hate", "worst", "fails", "crash", "error", "slow", "bug"]):
            sentiment = "negative"
            emotion = "frustration"
            pain_points.append(cleaned_text)
            negative_feedback.append(cleaned_text)

        # Heuristics for feature requests
        if any(w in lower_text for w in ["request", "wish", "add", "please", "need", "should"]):
            feature_requests.append(cleaned_text)

        # Heuristics for JTBD
        if "listen" in lower_text or "play" in lower_text or "find" in lower_text or "search" in lower_text:
            jobs_to_be_done.append(f"Use music application for playing or searching songs: {cleaned_text[:40]}...")

        return AnalyzedReviewOutput(
            sentiment=sentiment,
            emotion=emotion,
            pain_points=pain_points,
            feature_requests=feature_requests,
            positive_feedback=positive_feedback,
            negative_feedback=negative_feedback,
            jobs_to_be_done=jobs_to_be_done
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    def analyze_review(self, cleaned_text: str) -> AnalyzedReviewOutput:
        if not self.client:
            return self._analyze_review_fallback(cleaned_text)

        try:
            response = self.client.chat.completions.create(
                model="llama-3-8b-8192",
                response_model=AnalyzedReviewOutput,
                messages=[
                    {"role": "system", "content": ANALYZER_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Cleaned Review: '{cleaned_text}'"}
                ],
                temperature=0.1
            )
            return response
        except Exception as e:
            print(f"[Analyzer Agent] API call failed: {e}. Falling back to default heuristics.")
            return self._analyze_review_fallback(cleaned_text)


class DataAnalyzerPipeline:
    """Pipeline coordinating loading, analyzing, and storing review analysis."""

    def __init__(self, input_path: str = INPUT_FILE, output_dir: str = OUTPUT_DIR, analyzer_agent: Optional[ReviewAnalyzerAgent] = None):
        self.input_path = input_path
        self.output_dir = output_dir
        self.analyzer_agent = analyzer_agent or ReviewAnalyzerAgent()

    def load_reviews(self) -> list:
        print(f"[Analyzer] Loading filtered reviews from {self.input_path}...")
        with open(self.input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"[Analyzer] Loaded {len(data)} filtered reviews.")
        return data

    def analyze(self) -> dict:
        reviews = self.load_reviews()

        stats = {
            "total_analyzed": len(reviews),
            "sentiment_counts": {"positive": 0, "neutral": 0, "negative": 0},
            "emotion_counts": {},
            "total_pain_points": 0,
            "total_feature_requests": 0,
            "total_positive_feedback": 0,
            "total_negative_feedback": 0,
            "total_jtbd": 0,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

        analyzed_reviews = []

        for idx, review in enumerate(reviews):
            cleaned_text = review.get("review", "")
            if not cleaned_text:
                continue

            # Analyze review
            analysis = self.analyzer_agent.analyze_review(cleaned_text)

            # Update stats
            stats["sentiment_counts"][analysis.sentiment] = stats["sentiment_counts"].get(analysis.sentiment, 0) + 1
            stats["emotion_counts"][analysis.emotion] = stats["emotion_counts"].get(analysis.emotion, 0) + 1
            stats["total_pain_points"] += len(analysis.pain_points)
            stats["total_feature_requests"] += len(analysis.feature_requests)
            stats["total_positive_feedback"] += len(analysis.positive_feedback)
            stats["total_negative_feedback"] += len(analysis.negative_feedback)
            stats["total_jtbd"] += len(analysis.jobs_to_be_done)

            # Build enriched record
            enriched_record = {
                "original_review": cleaned_text,
                "rating": review.get("rating"),
                "review_date": review.get("review_date"),
                "app_version": review.get("app_version"),
                "thumbs_up_count": review.get("thumbs_up_count"),
                "analysis": {
                    "sentiment": analysis.sentiment,
                    "emotion": analysis.emotion,
                    "pain_points": analysis.pain_points,
                    "feature_requests": analysis.feature_requests,
                    "positive_feedback": analysis.positive_feedback,
                    "negative_feedback": analysis.negative_feedback,
                    "jobs_to_be_done": analysis.jobs_to_be_done
                }
            }
            analyzed_reviews.append(enriched_record)

            if (idx + 1) % 100 == 0:
                print(f"[Analyzer] Processed {idx + 1}/{len(reviews)} reviews...")

        return {"analyzed_reviews": analyzed_reviews, "statistics": stats}

    def save(self, result: dict):
        os.makedirs(self.output_dir, exist_ok=True)

        output_path = os.path.join(self.output_dir, "analyzed_reviews.json")
        stats_path = os.path.join(self.output_dir, "analysis_statistics.json")

        print(f"[Analyzer] Saving {len(result['analyzed_reviews'])} analyzed reviews to {output_path}...")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result["analyzed_reviews"], f, indent=2, ensure_ascii=False)

        print(f"[Analyzer] Saving analysis statistics to {stats_path}...")
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(result["statistics"], f, indent=2, ensure_ascii=False)

        # Print summary
        s = result["statistics"]
        print("\n" + "=" * 44)
        print("  REVIEW ANALYZER - SUMMARY")
        print("=" * 44)
        print(f"  Total analyzed:       {s['total_analyzed']}")
        print(f"  Sentiments:           Positive={s['sentiment_counts']['positive']} | Neutral={s['sentiment_counts']['neutral']} | Negative={s['sentiment_counts']['negative']}")
        print(f"  Pain Points found:    {s['total_pain_points']}")
        print(f"  Feature Requests:     {s['total_feature_requests']}")
        print(f"  Positive Comments:    {s['total_positive_feedback']}")
        print(f"  Negative Comments:    {s['total_negative_feedback']}")
        print(f"  JTBD Identified:      {s['total_jtbd']}")
        print("=" * 44 + "\n")

    def run(self):
        result = self.clean_and_analyze()
        self.save(result)

    def clean_and_analyze(self) -> dict:
        # Standard run alias
        return self.analyze()


if __name__ == "__main__":
    pipeline = DataAnalyzerPipeline()
    pipeline.run()
