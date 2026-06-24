import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict
from groq import Groq
import instructor
from tenacity import retry, stop_after_attempt, wait_exponential

from models import ThemeClusterSchema, ThemeCluster, SupportingReviewItem
from prompts import CLUSTERING_SYSTEM_PROMPT

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
BATCH_SIZE = 50

# --- Predefined Keywords & Descriptions for Fallback & Normalization ---------
THEME_KEYWORDS: Dict[str, List[str]] = {
    "Recommendation Quality": ["recommendation", "recommend", "suggest", "algorithm", "preference", "similar song", "discover weekly", "daily mix", "taste"],
    "Discovery": ["discover", "find new", "explore", "search new", "hear new", "fresh", "unknown", "track discovery", "artist discovery"],
    "Playlist": ["playlist", "shuffle", "album", "queue", "list", "my songs", "folder", "mix", "add to"],
    "Search": ["search", "lookup", "find", "query", "type", "seek"],
    "Advertisements": ["ad", "ads", "advert", "advertisement", "commercial", "pop up", "pop-up", "sponsor", "annoy ad", "too many ads"],
    "Offline Listening": ["offline", "download", "no wifi", "airplane", "local", "connection", "no internet", "save", "data", "wifi"],
    "Pricing": ["price", "charge", "subscription", "premium", "pay", "fee", "cost", "money", "free", "dollars", "subscribe", "billing", "greedy", "scummy"],
    "Performance": ["crash", "lag", "bug", "freeze", "slow", "glitch", "error", "kick me out", "not loading", "broken", "stop", "close", "restart", "exit", "black screen", "loading"],
    "UI": ["ui", "interface", "layout", "look", "button", "screen", "visual", "design", "dark mode", "font", "lyrics", "banner", "tap", "theme"],
    "Store": ["store", "play store", "app store", "download", "install", "update", "google play", "apple store"]
}

THEME_DESCRIPTIONS: Dict[str, str] = {
    "Recommendation Quality": "Issues regarding music recommendation algorithms, repetitive songs, or taste profiling.",
    "Discovery": "Difficulty finding new music, lack of exposure to new artists/genres, or discovery hurdles.",
    "Playlist": "Frustrations with playlist management, queue ordering, or broken shuffle modes.",
    "Search": "Problems with search queries, finding specific tracks, or search functionality.",
    "Advertisements": "Complaints about excessive, repetitive, or intrusive advertisements on free tiers.",
    "Offline Listening": "Issues with offline playback, downloads, local files, or listening without internet/Wi-Fi.",
    "Pricing": "Frustrations with price increases, value of premium tiers, or pushy upgrade prompts.",
    "Performance": "Technical issues including app crashes, lag, slow loading times, errors, or freeze glitches.",
    "UI": "Complaints about user interface layout changes, missing lyrics, navigation, or visual styling.",
    "Store": "Problems updating the app, downloading from app stores, or installation issues."
}


def setup_logger(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    log_file = os.path.join(output_dir, "clustering.log")

    logger = logging.getLogger("ThemeClustering")
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


import re

def count_theme_matches(text: str, keywords: List[str]) -> int:
    # Tokenize text into words (lowercase)
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


class ThemeClusteringAgent:
    """Agent 4 — Theme Clustering (Groq LLM with Instructor validation)"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.client = instructor.patch(Groq(api_key=self.api_key)) if self.api_key else None
        if self.client:
            logger.info("Groq client initialized successfully for Theme Clustering.")
        else:
            logger.warning("GROQ_API_KEY not found. Clustering will run in local heuristic fallback mode.")

    def _cluster_batch_fallback(self, batch_reviews: List[dict]) -> ThemeClusterSchema:
        # Heuristically cluster reviews based on keyword matching
        clusters = {}
        for r in batch_reviews:
            review_text = r.get("original_review", r.get("review", ""))
            rating = r.get("rating", 3)
            date = r.get("review_date", "")

            # Combine text fields to scan for keywords
            lower_text = review_text.lower()
            analysis = r.get("analysis", {})
            for p in analysis.get("pain_points", []):
                lower_text += " " + p.lower()
            for n in analysis.get("negative_feedback", []):
                lower_text += " " + n.lower()

            best_theme = "Other / General Feedback"
            best_score = 0

            for theme, keywords in THEME_KEYWORDS.items():
                score = count_theme_matches(lower_text, keywords)
                if score > best_score:
                    best_score = score
                    best_theme = theme

            if best_theme not in clusters:
                desc = THEME_DESCRIPTIONS.get(best_theme, "General feedback or miscellaneous complaints.")
                clusters[best_theme] = {
                    "theme_name": best_theme,
                    "description": desc,
                    "supporting_reviews": []
                }

            clusters[best_theme]["supporting_reviews"].append({
                "review": review_text,
                "rating": rating,
                "review_date": date
            })


        theme_list = [
            ThemeCluster(
                theme_name=c["theme_name"],
                description=c["description"],
                supporting_reviews=[
                    SupportingReviewItem(**item)
                    for item in c["supporting_reviews"]
                ]
            )
            for c in clusters.values()
        ]
        return ThemeClusterSchema(themes=theme_list)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8), reraise=True)
    def cluster_batch(self, batch_reviews: List[dict]) -> ThemeClusterSchema:
        if not self.client:
            return self._cluster_batch_fallback(batch_reviews)

        # Prepare payload: send index and review text details
        payload = [
            {
                "index": idx,
                "review": r.get("original_review", r.get("review", "")),
                "rating": r.get("rating", 3),
                "review_date": r.get("review_date", "")
            }
            for idx, r in enumerate(batch_reviews)
        ]
        user_content = json.dumps(payload)

        try:
            logger.info(f"Sending batch of {len(batch_reviews)} reviews to Groq API for clustering...")
            start_time = time.time()
            response = self.client.chat.completions.create(
                model="llama-3-8b-8192", # Stable, fast structured extraction model
                response_model=ThemeClusterSchema,
                messages=[
                    {"role": "system", "content": CLUSTERING_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Reviews to cluster: {user_content}"}
                ],
                temperature=0.3
            )
            latency = time.time() - start_time
            logger.info(f"Received theme clustering response in {latency:.2f}s.")
            return response
        except Exception as e:
            logger.error(f"Error during Groq API clustering call: {e}")
            raise e


class ThemeClusteringPipeline:
    """Pipeline coordinating loading analyzed reviews, clustering, and storing results."""

    def __init__(self, input_path: str = INPUT_FILE, output_dir: str = OUTPUT_DIR, clustering_agent: Optional[ThemeClusteringAgent] = None, batch_size: int = BATCH_SIZE):
        self.input_path = input_path
        self.output_dir = output_dir
        self.clustering_agent = clustering_agent or ThemeClusteringAgent()
        self.batch_size = batch_size

    def load_reviews(self) -> list:
        logger.info(f"Loading analyzed reviews from {self.input_path}...")
        with open(self.input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data)} analyzed reviews.")
        return data

    def analyze(self) -> list:
        reviews = self.load_reviews()

        # Extract only reviews that indicate user problems/pain points
        problem_reviews = []
        for r in reviews:
            analysis = r.get("analysis", {})
            is_negative = (
                r.get("rating", 5) <= 3
                or analysis.get("sentiment") == "negative"
                or len(analysis.get("pain_points", [])) > 0
                or len(analysis.get("negative_feedback", [])) > 0
            )
            if is_negative:
                problem_reviews.append(r)

        total_problems = len(problem_reviews)
        logger.info(f"Filtered {total_problems} problem/complaint reviews out of {len(reviews)} total reviews.")

        if total_problems == 0:
            logger.warning("No problem reviews found for theme clustering.")
            return []

        merged_themes = {}

        for i in range(0, total_problems, self.batch_size):
            batch_chunk = problem_reviews[i:i + self.batch_size]
            logger.info(f"Processing clustering batch {i // self.batch_size + 1} ({i} to {min(i + self.batch_size, total_problems)} of {total_problems})...")

            try:
                batch_output = self.clustering_agent.cluster_batch(batch_chunk)
            except Exception as e:
                logger.error(f"Failed all retries for clustering batch {i // self.batch_size + 1}: {e}. Falling back to default heuristics.")
                batch_output = self.clustering_agent._cluster_batch_fallback(batch_chunk)

            # Merge results into output structure
            for theme_cluster in batch_output.themes:
                tname = theme_cluster.theme_name.strip()
                # Normalize tname matching predefined themes case-insensitively
                for pred_theme in THEME_KEYWORDS.keys():
                    if pred_theme.lower() == tname.lower():
                        tname = pred_theme
                        break

                if tname not in merged_themes:
                    desc = THEME_DESCRIPTIONS.get(tname, theme_cluster.description)
                    merged_themes[tname] = {
                        "theme_name": tname,
                        "description": desc,
                        "supporting_reviews": []
                    }

                # Append supporting reviews, preventing identical duplicate strings
                for rev in theme_cluster.supporting_reviews:
                    if not any(x["review"] == rev.review for x in merged_themes[tname]["supporting_reviews"]):
                        merged_themes[tname]["supporting_reviews"].append({
                            "review": rev.review,
                            "rating": rev.rating,
                            "review_date": rev.review_date
                        })

        # Sort themes by count of supporting reviews descending
        sorted_themes = sorted(merged_themes.values(), key=lambda x: len(x["supporting_reviews"]), reverse=True)

        return sorted_themes

    def save(self, result: list):
        os.makedirs(self.output_dir, exist_ok=True)
        themes_path = os.path.join(self.output_dir, "themes.json")

        logger.info(f"Saving theme clusters to {themes_path}...")
        with open(themes_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Print summary
        logger.info("\n" + "=" * 44)
        logger.info("  THEME CLUSTERING - SUMMARY")
        logger.info("=" * 44)
        for t in result:
            logger.info(f"  {t['theme_name']:<25} : {len(t['supporting_reviews'])} reviews")
        logger.info("=" * 44 + "\n")

    def run(self):
        result = self.analyze()
        self.save(result)


if __name__ == "__main__":
    pipeline = ThemeClusteringPipeline()
    pipeline.run()
