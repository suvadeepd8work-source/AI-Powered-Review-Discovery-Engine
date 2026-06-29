import os
import sys
import json
import logging
import time
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict

from groq import Groq
import instructor
from tenacity import retry, stop_after_attempt, wait_exponential

# Path setup for imports
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if os.path.join(root_dir, "phase2_agent_analysis", "src") not in sys.path:
    sys.path.insert(0, os.path.join(root_dir, "phase2_agent_analysis", "src"))

from models import UserSegmentSchema, UserSegment, UserSegmentReview
from prompts import SEGMENTATION_SYSTEM_PROMPT


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

INPUT_FILE = os.path.join("phase2_agent_analysis", "data", "output", "analyzed_reviews.json")
OUTPUT_DIR = os.path.join("phase2_agent_analysis", "data", "output")
BATCH_SIZE = 120  # Reviews per batch sent to the LLM


# --- Predefined Segment Keywords & Descriptions for Fallback -----------------
SEGMENT_KEYWORDS: Dict[str, List[str]] = {
    "Casual Listeners": [
        "casual", "sometimes", "occasionally", "on and off", "background music",
        "free tier", "once in a while", "relax", "chill", "light listening", "leisure"
    ],
    "Power Users": [
        "power", "daily", "hours", "all day", "crossfade", "gapless", "equalizer",
        "heavy user", "advanced", "customiz", "library", "collection", "heavy listener",
        "always listening", "constant", "playlist management"
    ],
    "Students": [
        "student", "study", "studying", "homework", "school", "college", "university",
        "campus", "budget", "affordable", "discount", "broke", "cheap", "student plan"
    ],
    "Premium Subscribers": [
        "premium", "subscriber", "subscription", "i pay", "pay for", "paying",
        "premium user", "paying customer", "worth the money", "20 dollar", "10 dollar",
        "family plan", "duo plan", "individual plan"
    ],
    "Free Users": [
        "free", "free tier", "free version", "no premium", "can't skip", "skip limit",
        "ad break", "shuffle only", "locked", "can't choose", "not paying",
        "without premium", "free account", "no subscription"
    ],
    "Podcast Users": [
        "podcast", "podcasts", "audiobook", "audio book", "spoken word", "episode",
        "series", "host", "listen to podcast", "podcast feature", "news", "talk show"
    ],
    "Regional Music Users": [
        "bollywood", "hindi", "tamil", "telugu", "regional", "desi", "k-pop", "kpop",
        "korean", "japanese", "regional music", "local music", "vernacular", "bhojpuri",
        "marathi", "punjabi", "urdu", "local language", "regional artist", "language song"
    ],
    "Fitness Users": [
        "workout", "gym", "run", "running", "exercise", "jog", "jogging", "training",
        "cardio", "fitness", "walk", "walking", "sports", "athlete", "lifting",
        "treadmill", "cycling", "outdoor", "uninterrupted"
    ]
}

SEGMENT_DESCRIPTIONS: Dict[str, str] = {
    "Casual Listeners": "Users who listen occasionally for leisure, typically use the free tier, and are primarily frustrated by ad interruptions.",
    "Power Users": "Heavy daily listeners who use advanced features, manage large libraries, and expect a premium, full-featured experience.",
    "Students": "Budget-conscious users who listen while studying and actively seek affordable or discounted subscription plans.",
    "Premium Subscribers": "Paying users who expect flawless app performance and feel betrayed when crashes, bugs, or regressions occur.",
    "Free Users": "Non-paying users severely limited by ad interruptions, skip restrictions, and inability to choose songs or use offline mode.",
    "Podcast Users": "Users primarily interested in podcast content, audiobooks, or spoken word — not just music streaming.",
    "Regional Music Users": "Users listening to regional or local-language music (Bollywood, K-Pop, etc.) who want better regional catalogs and recommendations.",
    "Fitness Users": "Users who listen during workouts or outdoor activities, requiring uninterrupted playback and strong offline download capabilities."
}

SEGMENT_TRAITS: Dict[str, List[str]] = {
    "Casual Listeners": ["Listens occasionally", "Uses free tier", "Background music listener", "Low engagement with features"],
    "Power Users": ["Listens 4+ hours daily", "Manages large playlists", "Uses advanced audio settings", "Relies on app for daily mood"],
    "Students": ["Budget-sensitive", "Listens while studying", "Seeks student discounts", "Values ad-free experience"],
    "Premium Subscribers": ["Pays for premium plan", "Expects zero bugs", "Uses offline downloads", "High expectations from service"],
    "Free Users": ["No paid subscription", "Disrupted by ads", "Cannot skip freely", "Cannot choose specific songs"],
    "Podcast Users": ["Primary use is podcasts", "May use premium for podcast features", "Episode-based listening habits"],
    "Regional Music Users": ["Listens in regional/local language", "Disappointed by regional catalog gaps", "Switches apps for regional content"],
    "Fitness Users": ["Listens during physical activity", "Needs uninterrupted playback", "Relies on offline/downloaded music", "Uses playlists for workouts"]
}

SEGMENT_JTBD: Dict[str, List[str]] = {
    "Casual Listeners": ["Listen to music without friction", "Discover songs easily", "Enjoy music without interruptions"],
    "Power Users": ["Fine-tune the listening experience", "Manage a large music collection", "Get personalized recommendations"],
    "Students": ["Access affordable music streaming", "Listen while studying without distraction", "Explore new music on a budget"],
    "Premium Subscribers": ["Get a flawless premium experience", "Access all features reliably", "Justify subscription cost"],
    "Free Users": ["Listen to music for free", "Skip songs occasionally", "Access basic music discovery"],
    "Podcast Users": ["Listen to favorite podcasts", "Discover new shows", "Continue episodes seamlessly"],
    "Regional Music Users": ["Discover regional language artists", "Access local music catalog", "Get region-specific recommendations"],
    "Fitness Users": ["Maintain uninterrupted playback during workouts", "Download music for offline gym use", "Find high-energy workout playlists"]
}

SEGMENT_CHALLENGES: Dict[str, List[str]] = {
    "Casual Listeners": ["Too many ads on free tier", "Forced shuffle mode", "Can't choose specific songs without premium"],
    "Power Users": ["Bugs disrupting heavy usage", "Recommendation algorithms feel repetitive", "Missing advanced audio controls"],
    "Students": ["Cannot afford premium", "Student discount not easily accessible", "Ad volume too high on free tier"],
    "Premium Subscribers": ["App crashing despite paying", "Bugs not being fixed promptly", "Price hikes without improvements"],
    "Free Users": ["Cannot skip songs", "Ad frequency is excessive", "Offline mode not available"],
    "Podcast Users": ["Poor podcast discovery", "Podcast episodes missing", "Audio quality inconsistent"],
    "Regional Music Users": ["Missing regional artists in catalog", "Recommendations ignore regional preferences", "Language filtering broken"],
    "Fitness Users": ["App crashes during workouts", "Offline downloads fail", "No seamless Bluetooth/wearable integration"]
}


def setup_logger(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    log_file = os.path.join(output_dir, "segmentation.log")

    logger = logging.getLogger("UserSegmentation")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers on re-import
    if logger.handlers:
        logger.handlers.clear()

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(sh)

    return logger


logger = setup_logger(OUTPUT_DIR)


def count_segment_matches(text: str, keywords: List[str]) -> int:
    """Count how many segment keywords match the given text."""
    words = re.findall(r'\b\w+\b', text.lower())
    score = 0
    for kw in keywords:
        kw_lower = kw.lower()
        if " " in kw_lower:
            if re.search(r'\b' + re.escape(kw_lower) + r'\b', text.lower()):
                score += 1
        else:
            for word in words:
                if word == kw_lower or (len(kw_lower) > 4 and word.startswith(kw_lower)):
                    score += 1
                    break
    return score


class UserSegmentationAgent:
    """Agent 5 — User Segmentation (Groq LLM with Instructor validation)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.client = instructor.patch(Groq(api_key=self.api_key)) if self.api_key else None
        if self.client:
            logger.info("Groq client initialized successfully for User Segmentation.")
        else:
            logger.warning("GROQ_API_KEY not found. Segmentation will run in local heuristic fallback mode.")

    def _segment_batch_fallback(self, batch_reviews: List[dict]) -> UserSegmentSchema:
        """Heuristic keyword-based segmentation fallback (no API required)."""
        segments: Dict[str, dict] = {}

        for r in batch_reviews:
            review_text = r.get("original_review", r.get("review", ""))
            rating = r.get("rating", 3)
            date = r.get("review_date", "")

            # Build composite text (review + extracted analysis fields)
            lower_text = review_text.lower()
            analysis = r.get("analysis", {})
            for field in ["pain_points", "jobs_to_be_done", "feature_requests"]:
                for item in analysis.get(field, []):
                    lower_text += " " + item.lower()

            best_segment = "Casual Listeners"
            best_score = 0

            for seg_name, keywords in SEGMENT_KEYWORDS.items():
                score = count_segment_matches(lower_text, keywords)
                if score > best_score:
                    best_score = score
                    best_segment = seg_name

            if best_segment not in segments:
                segments[best_segment] = {
                    "segment_name": best_segment,
                    "description": SEGMENT_DESCRIPTIONS.get(best_segment, ""),
                    "traits": SEGMENT_TRAITS.get(best_segment, []),
                    "primary_challenges": SEGMENT_CHALLENGES.get(best_segment, []),
                    "jobs_to_be_done": SEGMENT_JTBD.get(best_segment, []),
                    "representative_reviews": [],
                    "review_count": 0
                }

            segments[best_segment]["review_count"] += 1

            # Keep up to 5 representative reviews per segment
            if len(segments[best_segment]["representative_reviews"]) < 5:
                segments[best_segment]["representative_reviews"].append({
                    "review": review_text,
                    "rating": rating,
                    "review_date": date
                })

        segment_list = [
            UserSegment(
                segment_name=s["segment_name"],
                description=s["description"],
                traits=s["traits"],
                primary_challenges=s["primary_challenges"],
                jobs_to_be_done=s["jobs_to_be_done"],
                representative_reviews=[
                    UserSegmentReview(**item) for item in s["representative_reviews"]
                ],
                review_count=s["review_count"]
            )
            for s in segments.values()
        ]
        return UserSegmentSchema(segments=segment_list)

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=30), reraise=True)
    def segment_batch(self, batch_reviews: List[dict]) -> UserSegmentSchema:
        """Send a batch of reviews to Groq LLM for user segmentation."""
        if not self.client:
            return self._segment_batch_fallback(batch_reviews)

        payload = [
            {
                "index": idx,
                "review": r.get("original_review", r.get("review", "")),
                "rating": r.get("rating", 3),
                "review_date": r.get("review_date", ""),
                "sentiment": r.get("analysis", {}).get("sentiment", ""),
                "pain_points": r.get("analysis", {}).get("pain_points", []),
                "jobs_to_be_done": r.get("analysis", {}).get("jobs_to_be_done", [])
            }
            for idx, r in enumerate(batch_reviews)
        ]
        user_content = json.dumps(payload)

        try:
            logger.info(f"Sending batch of {len(batch_reviews)} reviews to Groq API for segmentation...")
            start_time = time.time()
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                response_model=UserSegmentSchema,
                messages=[
                    {"role": "system", "content": SEGMENTATION_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Reviews to segment: {user_content}"}
                ],
                temperature=0.2
            )
            latency = time.time() - start_time
            logger.info(f"Received user segmentation response in {latency:.2f}s.")
            return response
        except Exception as e:
            logger.error(f"Error during Groq API segmentation call: {e}")
            raise e


class UserSegmentationPipeline:
    """Pipeline coordinating loading analyzed reviews, user segmentation, and storing results."""

    def __init__(
        self,
        input_path: str = INPUT_FILE,
        output_dir: str = OUTPUT_DIR,
        segmentation_agent: Optional[UserSegmentationAgent] = None,
        batch_size: int = BATCH_SIZE
    ):
        self.input_path = input_path
        self.output_dir = output_dir
        self.segmentation_agent = segmentation_agent or UserSegmentationAgent()
        self.batch_size = batch_size

    def load_reviews(self) -> list:
        logger.info(f"Loading analyzed reviews from {self.input_path}...")
        with open(self.input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} analyzed reviews.")
        return data

    def analyze_from_data(self, analyzed_reviews: list) -> list:
        """Segment reviews from in-memory data instead of loading from file."""
        total = len(analyzed_reviews)

        if total == 0:
            logger.warning("No reviews found for user segmentation.")
            return []

        logger.info(f"Starting user segmentation for {total} reviews in batches of {self.batch_size}...")

        merged_segments: Dict[str, dict] = {}
        total_batches = (total + self.batch_size - 1) // self.batch_size

        for batch_num, i in enumerate(range(0, total, self.batch_size), start=1):
            batch_chunk = analyzed_reviews[i: i + self.batch_size]
            logger.info(
                f"Processing segmentation batch {batch_num}/{total_batches} "
                f"(reviews {i + 1}–{min(i + self.batch_size, total)} of {total})..."
            )

            try:
                batch_output = self.segmentation_agent.segment_batch(batch_chunk)
            except Exception as e:
                logger.error(
                    f"Failed all retries for segmentation batch {batch_num}: {e}. "
                    "Falling back to heuristic segmentation."
                )
                batch_output = self.segmentation_agent._segment_batch_fallback(batch_chunk)

            for seg in batch_output.segments:
                seg_name = seg.segment_name.strip()

                for pred_seg in SEGMENT_KEYWORDS.keys():
                    if pred_seg.lower() == seg_name.lower():
                        seg_name = pred_seg
                        break

                if seg_name not in merged_segments:
                    merged_segments[seg_name] = {
                        "segment_name": seg_name,
                        "description": SEGMENT_DESCRIPTIONS.get(seg_name, seg.description),
                        "traits": SEGMENT_TRAITS.get(seg_name, seg.traits),
                        "primary_challenges": SEGMENT_CHALLENGES.get(seg_name, seg.primary_challenges),
                        "jobs_to_be_done": SEGMENT_JTBD.get(seg_name, seg.jobs_to_be_done),
                        "representative_reviews": [],
                        "review_count": 0
                    }

                merged_segments[seg_name]["review_count"] += seg.review_count

                existing_reviews = {r["review"] for r in merged_segments[seg_name]["representative_reviews"]}
                for rev in seg.representative_reviews:
                    if rev.review not in existing_reviews and len(merged_segments[seg_name]["representative_reviews"]) < 8:
                        merged_segments[seg_name]["representative_reviews"].append({
                            "review": rev.review,
                            "rating": rev.rating,
                            "review_date": rev.review_date
                        })
                        existing_reviews.add(rev.review)

        sorted_segments = sorted(
            merged_segments.values(),
            key=lambda x: x["review_count"],
            reverse=True
        )

        return sorted_segments

    def analyze(self) -> list:
        reviews = self.load_reviews()
        total = len(reviews)

        if total == 0:
            logger.warning("No reviews found for user segmentation.")
            return []

        logger.info(f"Starting user segmentation for {total} reviews in batches of {self.batch_size}...")

        # Accumulate segment data across all batches
        merged_segments: Dict[str, dict] = {}
        total_batches = (total + self.batch_size - 1) // self.batch_size

        for batch_num, i in enumerate(range(0, total, self.batch_size), start=1):
            batch_chunk = reviews[i: i + self.batch_size]
            logger.info(
                f"Processing segmentation batch {batch_num}/{total_batches} "
                f"(reviews {i + 1}–{min(i + self.batch_size, total)} of {total})..."
            )

            try:
                batch_output = self.segmentation_agent.segment_batch(batch_chunk)
            except Exception as e:
                logger.error(
                    f"Failed all retries for segmentation batch {batch_num}: {e}. "
                    "Falling back to heuristic segmentation."
                )
                batch_output = self.segmentation_agent._segment_batch_fallback(batch_chunk)

            # Merge segments across batches
            for seg in batch_output.segments:
                seg_name = seg.segment_name.strip()

                # Normalize to predefined segment names (case-insensitive)
                for pred_seg in SEGMENT_KEYWORDS.keys():
                    if pred_seg.lower() == seg_name.lower():
                        seg_name = pred_seg
                        break

                if seg_name not in merged_segments:
                    merged_segments[seg_name] = {
                        "segment_name": seg_name,
                        "description": SEGMENT_DESCRIPTIONS.get(seg_name, seg.description),
                        "traits": SEGMENT_TRAITS.get(seg_name, seg.traits),
                        "primary_challenges": SEGMENT_CHALLENGES.get(seg_name, seg.primary_challenges),
                        "jobs_to_be_done": SEGMENT_JTBD.get(seg_name, seg.jobs_to_be_done),
                        "representative_reviews": [],
                        "review_count": 0
                    }

                merged_segments[seg_name]["review_count"] += seg.review_count

                # Deduplicate and accumulate representative reviews (up to 8 per segment)
                existing_reviews = {r["review"] for r in merged_segments[seg_name]["representative_reviews"]}
                for rev in seg.representative_reviews:
                    if rev.review not in existing_reviews and len(merged_segments[seg_name]["representative_reviews"]) < 8:
                        merged_segments[seg_name]["representative_reviews"].append({
                            "review": rev.review,
                            "rating": rev.rating,
                            "review_date": rev.review_date
                        })
                        existing_reviews.add(rev.review)

        # Sort segments by review_count descending
        sorted_segments = sorted(
            merged_segments.values(),
            key=lambda x: x["review_count"],
            reverse=True
        )

        return sorted_segments

    def save(self, result: list):
        os.makedirs(self.output_dir, exist_ok=True)
        segments_path = os.path.join(self.output_dir, "segments.json")

        logger.info(f"Saving user segments to {segments_path}...")
        with open(segments_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Print summary table
        logger.info("\n" + "=" * 50)
        logger.info("  USER SEGMENTATION - SUMMARY")
        logger.info("=" * 50)
        for seg in result:
            logger.info(
                f"  {seg['segment_name']:<25} : {seg['review_count']:>5} reviews  "
                f"| {len(seg['representative_reviews'])} representative sample(s)"
            )
        logger.info("=" * 50 + "\n")

        # Statistics
        total_reviews = sum(s["review_count"] for s in result)
        stats_path = os.path.join(self.output_dir, "segmentation_statistics.json")
        stats = {
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_segments_identified": len(result),
            "total_reviews_segmented": total_reviews,
            "segments": [
                {
                    "segment_name": s["segment_name"],
                    "review_count": s["review_count"],
                    "percentage": round(s["review_count"] / total_reviews * 100, 1) if total_reviews > 0 else 0
                }
                for s in result
            ]
        }
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        logger.info(f"Segmentation statistics saved to {stats_path}.")

    def run(self):
        result = self.analyze()
        self.save(result)


if __name__ == "__main__":
    pipeline = UserSegmentationPipeline()
    pipeline.run()
