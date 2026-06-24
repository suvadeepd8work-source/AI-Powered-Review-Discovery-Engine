import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, List
from groq import Groq
import instructor
from tenacity import retry, stop_after_attempt, wait_exponential

from models import AnalyzedReviewOutput, AnalyzedReviewItem, AnalyzedReviewBatchOutput
from prompts import ANALYZER_SYSTEM_PROMPT

# --- Helper to load .env manually without external dependencies --------------
def load_dotenv(dotenv_path: str = ".env"):
    if os.path.exists(dotenv_path):
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    os.environ[key] = val
    else:
        root_dotenv = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        if os.path.exists(root_dotenv):
            load_dotenv(root_dotenv)


# --- Load .env at import time ------------------------------------------------
load_dotenv()

INPUT_FILE = os.path.join("phase2_agent_analysis", "data", "output", "filtered_reviews.json")
OUTPUT_DIR = os.path.join("phase2_agent_analysis", "data", "output")
BATCH_SIZE = 15


def setup_logger(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    log_file = os.path.join(output_dir, "analyzer.log")

    logger = logging.getLogger("ReviewAnalyzer")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if logger.handlers:
        logger.handlers.clear()

    # File Handler
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(fh)

    # Stream Handler
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(sh)

    return logger


logger = setup_logger(OUTPUT_DIR)


class ReviewAnalyzerAgent:
    """Agent 3 — Review Analyzer (Groq LLM with Instructor validation)"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.client = instructor.patch(Groq(api_key=self.api_key)) if self.api_key else None
        if self.client:
            logger.info("Groq client initialized successfully for batch analysis.")
        else:
            logger.warning("GROQ_API_KEY not found. Analyzer will run in local heuristic fallback mode.")

    def _analyze_review_fallback(self, cleaned_text: str) -> AnalyzedReviewOutput:
        # Simple local heuristic analysis fallback
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

    def _analyze_batch_fallback(self, batch_texts: List[str]) -> AnalyzedReviewBatchOutput:
        # Heuristically process batch
        results = []
        for idx, text in enumerate(batch_texts):
            single = self._analyze_review_fallback(text)
            item = AnalyzedReviewItem(
                review_index=idx,
                sentiment=single.sentiment,
                emotion=single.emotion,
                pain_points=single.pain_points,
                feature_requests=single.feature_requests,
                positive_feedback=single.positive_feedback,
                negative_feedback=single.negative_feedback,
                jobs_to_be_done=single.jobs_to_be_done
            )
            results.append(item)
        return AnalyzedReviewBatchOutput(batch_results=results)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8), reraise=True)
    def analyze_batch(self, batch_texts: List[str]) -> AnalyzedReviewBatchOutput:
        if not self.client:
            return self._analyze_batch_fallback(batch_texts)

        # Prepare payload
        payload = [
            {"index": idx, "text": text}
            for idx, text in enumerate(batch_texts)
        ]
        user_content = json.dumps(payload)

        try:
            logger.info(f"Sending batch of {len(batch_texts)} reviews to Groq API...")
            start_time = time.time()
            response = self.client.chat.completions.create(
                model="llama-3-8b-8192",
                response_model=AnalyzedReviewBatchOutput,
                messages=[
                    {"role": "system", "content": ANALYZER_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Reviews Batch: {user_content}"}
                ],
                temperature=0.1
            )
            latency = time.time() - start_time
            logger.info(f"Received batch analysis response in {latency:.2f}s.")
            return response
        except Exception as e:
            logger.error(f"Error during Groq API batch completion: {e}")
            raise e

    # Maintain single-review method for backward compatibility & tests
    def analyze_review(self, cleaned_text: str) -> AnalyzedReviewOutput:
        batch_res = self.analyze_batch([cleaned_text])
        if batch_res.batch_results:
            first = batch_res.batch_results[0]
            return AnalyzedReviewOutput(
                sentiment=first.sentiment,
                emotion=first.emotion,
                pain_points=first.pain_points,
                feature_requests=first.feature_requests,
                positive_feedback=first.positive_feedback,
                negative_feedback=first.negative_feedback,
                jobs_to_be_done=first.jobs_to_be_done
            )
        return self._analyze_review_fallback(cleaned_text)


class DataAnalyzerPipeline:
    """Pipeline coordinating loading, batch-analyzing, retrying, and storing review analysis."""

    def __init__(self, input_path: str = INPUT_FILE, output_dir: str = OUTPUT_DIR, analyzer_agent: Optional[ReviewAnalyzerAgent] = None, batch_size: int = BATCH_SIZE):
        self.input_path = input_path
        self.output_dir = output_dir
        self.analyzer_agent = analyzer_agent or ReviewAnalyzerAgent()
        self.batch_size = batch_size

    def load_reviews(self) -> list:
        logger.info(f"Loading filtered reviews from {self.input_path}...")
        with open(self.input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} filtered reviews.")
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
        total_reviews = len(reviews)

        for i in range(0, total_reviews, self.batch_size):
            batch_chunk = reviews[i:i + self.batch_size]
            batch_texts = [r.get("review", "") for r in batch_chunk]

            logger.info(f"Processing batch {i // self.batch_size + 1} ({i} to {min(i + self.batch_size, total_reviews)} of {total_reviews})...")

            # Execute batch with retries and fallback
            try:
                batch_output = self.analyzer_agent.analyze_batch(batch_texts)
            except Exception as e:
                logger.error(f"Failed all retries for batch {i // self.batch_size + 1}: {e}. Falling back to default heuristics.")
                # Fallback directly
                batch_output = self.analyzer_agent._analyze_batch_fallback(batch_texts)

            # Map results back to original items
            for item in batch_output.batch_results:
                orig_idx = i + item.review_index
                if orig_idx >= total_reviews:
                    continue

                review_item = batch_chunk[item.review_index]

                # Update stats
                stats["sentiment_counts"][item.sentiment] = stats["sentiment_counts"].get(item.sentiment, 0) + 1
                stats["emotion_counts"][item.emotion] = stats["emotion_counts"].get(item.emotion, 0) + 1
                stats["total_pain_points"] += len(item.pain_points)
                stats["total_feature_requests"] += len(item.feature_requests)
                stats["total_positive_feedback"] += len(item.positive_feedback)
                stats["total_negative_feedback"] += len(item.negative_feedback)
                stats["total_jtbd"] += len(item.jobs_to_be_done)

                # Build record
                enriched_record = {
                    "original_review": review_item.get("review", ""),
                    "rating": review_item.get("rating"),
                    "review_date": review_item.get("review_date"),
                    "app_version": review_item.get("app_version"),
                    "thumbs_up_count": review_item.get("thumbs_up_count"),
                    "analysis": {
                        "sentiment": item.sentiment,
                        "emotion": item.emotion,
                        "pain_points": item.pain_points,
                        "feature_requests": item.feature_requests,
                        "positive_feedback": item.positive_feedback,
                        "negative_feedback": item.negative_feedback,
                        "jobs_to_be_done": item.jobs_to_be_done
                    }
                }
                analyzed_reviews.append(enriched_record)

        return {"analyzed_reviews": analyzed_reviews, "statistics": stats}

    def save(self, result: dict):
        os.makedirs(self.output_dir, exist_ok=True)

        output_path = os.path.join(self.output_dir, "analyzed_reviews.json")
        stats_path = os.path.join(self.output_dir, "analysis_statistics.json")

        logger.info(f"Saving {len(result['analyzed_reviews'])} analyzed reviews to {output_path}...")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result["analyzed_reviews"], f, indent=2, ensure_ascii=False)

        logger.info(f"Saving analysis statistics to {stats_path}...")
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(result["statistics"], f, indent=2, ensure_ascii=False)

        # Print summary
        s = result["statistics"]
        logger.info("\n" + "=" * 44)
        logger.info("  REVIEW ANALYZER - SUMMARY")
        logger.info("=" * 44)
        logger.info(f"  Total analyzed:       {s['total_analyzed']}")
        logger.info(f"  Sentiments:           Positive={s['sentiment_counts']['positive']} | Neutral={s['sentiment_counts']['neutral']} | Negative={s['sentiment_counts']['negative']}")
        logger.info(f"  Pain Points found:    {s['total_pain_points']}")
        logger.info(f"  Feature Requests:     {s['total_feature_requests']}")
        logger.info(f"  Positive Comments:    {s['total_positive_feedback']}")
        logger.info(f"  Negative Comments:    {s['total_negative_feedback']}")
        logger.info(f"  JTBD Identified:      {s['total_jtbd']}")
        logger.info("=" * 44 + "\n")

    def run(self):
        result = self.clean_and_analyze()
        self.save(result)

    def clean_and_analyze(self) -> dict:
        return self.analyze()


if __name__ == "__main__":
    pipeline = DataAnalyzerPipeline()
    pipeline.run()
