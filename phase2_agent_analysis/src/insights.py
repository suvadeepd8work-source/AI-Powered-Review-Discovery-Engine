import os
import sys
import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Optional, List, Dict

from groq import Groq
import instructor
from tenacity import retry, stop_after_attempt, wait_exponential

# Path setup for imports
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if os.path.join(root_dir, "phase2_agent_analysis", "src") not in sys.path:
    sys.path.insert(0, os.path.join(root_dir, "phase2_agent_analysis", "src"))

from models import ProductInsight, ProductInsightSchema
from prompts import INSIGHTS_SYSTEM_PROMPT


# --- Helper to load .env manually -------------------------------------------
def load_dotenv(dotenv_path: str = ".env"):
    if os.path.exists(dotenv_path):
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")
    else:
        root_dotenv = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        if os.path.exists(root_dotenv):
            load_dotenv(root_dotenv)


load_dotenv()

ANALYZED_REVIEWS_FILE = os.path.join("phase2_agent_analysis", "data", "output", "analyzed_reviews.json")
THEMES_FILE           = os.path.join("phase2_agent_analysis", "data", "output", "themes.json")
SEGMENTS_FILE         = os.path.join("phase2_agent_analysis", "data", "output", "segments.json")
OUTPUT_DIR            = os.path.join("phase2_agent_analysis", "data", "output")

# Top-N items fed to the LLM to keep token count manageable
TOP_N_PAIN_POINTS   = 15
TOP_N_FEATURES      = 15
MAX_THEME_REVIEWS   = 3   # representative reviews per theme to include
MAX_SEGMENT_REVIEWS = 2   # representative reviews per segment to include


# --- Heuristic fallback data -------------------------------------------------
FALLBACK_FRUSTRATIONS = [
    {
        "title": "Excessive advertisement frequency on free tier",
        "description": "Free-tier users are bombarded with ads between almost every song, making the listening experience highly disruptive and pushing users away from the platform.",
        "category": "Top Frustration",
        "severity": 9, "frequency": 0, "impact": 8,
        "affected_segments": ["Casual Listeners", "Free Users"],
        "supporting_evidence": ["Too many ads — can't listen without constant interruptions", "The ads play after every single song now, it's unbearable"],
        "recommended_action": "Reduce ad frequency to a maximum of 1 ad per 3 songs and cap ad session length at 30 seconds."
    },
    {
        "title": "App crashes and freezes during active playback",
        "description": "Users report frequent app crashes, black screens, and freeze-ups that interrupt music playback, especially on older devices and after recent updates.",
        "category": "Top Frustration",
        "severity": 10, "frequency": 0, "impact": 9,
        "affected_segments": ["Premium Subscribers", "Power Users"],
        "supporting_evidence": ["App keeps crashing every time I open it", "Fix your app — we pay for this and it freezes constantly"],
        "recommended_action": "Prioritize crash-fix releases targeting the most common device/OS combinations reported in crash logs. Add proactive crash detection and auto-recovery."
    },
    {
        "title": "Shuffle mode plays same songs repeatedly",
        "description": "Users on both free and premium tiers complain that the shuffle algorithm repeatedly plays the same limited pool of songs, ignoring their wider library.",
        "category": "Top Frustration",
        "severity": 8, "frequency": 0, "impact": 7,
        "affected_segments": ["Casual Listeners", "Power Users"],
        "supporting_evidence": ["Shuffle plays the same 20 songs every day", "My 2000-song library and it repeats the same tracks"],
        "recommended_action": "Overhaul the shuffle algorithm to use a true randomization model that weights against recently played tracks and ensures full library rotation."
    },
    {
        "title": "Premium price increases without feature improvements",
        "description": "Long-term subscribers report feeling undervalued as subscription prices have increased multiple times without noticeable improvements to the product experience.",
        "category": "Top Frustration",
        "severity": 8, "frequency": 0, "impact": 8,
        "affected_segments": ["Premium Subscribers", "Students"],
        "supporting_evidence": ["Price went up again but nothing new was added", "Paying $20/month and still getting crashes and bugs"],
        "recommended_action": "Communicate product improvements proactively in-app with each price increase. Introduce a loyalty discount for long-term subscribers."
    },
    {
        "title": "Offline downloads fail or disappear unexpectedly",
        "description": "Users who rely on offline listening frequently report that downloaded tracks vanish after app updates or that downloads fail to complete, leaving them without music.",
        "category": "Top Frustration",
        "severity": 8, "frequency": 0, "impact": 9,
        "affected_segments": ["Fitness Users", "Premium Subscribers"],
        "supporting_evidence": ["All my downloads disappeared after the update", "Downloads keep failing at 95% — completely useless offline"],
        "recommended_action": "Implement a downloads integrity check that verifies downloaded tracks after each app update and re-downloads any corrupted or missing files automatically."
    }
]

FALLBACK_FEATURE_REQUESTS = [
    {
        "title": "Ability to skip songs freely on free tier",
        "description": "Free-tier users consistently request the ability to skip songs without limits, citing that forced listening to disliked songs is a primary reason for churn.",
        "category": "Feature Request",
        "severity": 7, "frequency": 0, "impact": 8,
        "affected_segments": ["Free Users", "Casual Listeners"],
        "supporting_evidence": ["Let me skip songs without premium — just reduce the skips per hour", "Even 6 skips per hour would be acceptable"],
        "recommended_action": "Introduce a limited skip allowance (e.g. 6 skips/hour) for free-tier users as a middle ground between full-lock and unlimited skips."
    },
    {
        "title": "Crossfade and audio equalizer controls",
        "description": "Power users frequently request crossfade between tracks and a built-in audio equalizer for fine-grained sound control, features available in competing apps.",
        "category": "Feature Request",
        "severity": 5, "frequency": 0, "impact": 7,
        "affected_segments": ["Power Users", "Premium Subscribers"],
        "supporting_evidence": ["I need an EQ — other apps have had this for years", "Crossfade between songs would make this app perfect"],
        "recommended_action": "Ship a 5-band equalizer and crossfade duration slider as a premium feature in the audio settings."
    },
    {
        "title": "Improved regional and local language music catalog",
        "description": "Users seeking Bollywood, K-Pop, and other regional music report significant catalog gaps and poor localized recommendations compared to competitors.",
        "category": "Feature Request",
        "severity": 6, "frequency": 0, "impact": 8,
        "affected_segments": ["Regional Music Users", "Casual Listeners"],
        "supporting_evidence": ["The Hindi song catalog is very limited", "K-Pop recommendations are always the same 10 songs"],
        "recommended_action": "Expand regional music licensing partnerships and build regional-language recommendation models trained on local listening patterns."
    },
    {
        "title": "Sleep timer and auto-stop functionality",
        "description": "Users who listen while falling asleep or exercising request a sleep timer to automatically pause playback after a set duration.",
        "category": "Feature Request",
        "severity": 4, "frequency": 0, "impact": 6,
        "affected_segments": ["Casual Listeners", "Students"],
        "supporting_evidence": ["I fall asleep to music — a sleep timer would be perfect", "Need auto-stop after 30 minutes for bedtime listening"],
        "recommended_action": "Add a native sleep timer accessible from the now-playing screen with preset options (15, 30, 45, 60 minutes) and a custom duration picker."
    },
    {
        "title": "Collaborative playlist editing with friends",
        "description": "Users request the ability to create and edit playlists collaboratively in real-time with friends or family, a social feature that strengthens retention.",
        "category": "Feature Request",
        "severity": 4, "frequency": 0, "impact": 7,
        "affected_segments": ["Casual Listeners", "Students"],
        "supporting_evidence": ["Would love to add songs to a playlist with my friends", "Social listening and shared playlists would make this amazing"],
        "recommended_action": "Implement collaborative playlist functionality with invite links, real-time song additions, and voting on song order."
    }
]

FALLBACK_QUICK_WINS = [
    {
        "title": "Reduce first-open ad delay for free users",
        "description": "Free-tier users are shown ads immediately upon opening the app before they even start listening. Delaying the first ad by 2 songs would dramatically improve first impressions.",
        "category": "Quick Win",
        "severity": 6, "frequency": 0, "impact": 7,
        "affected_segments": ["Free Users", "Casual Listeners"],
        "supporting_evidence": ["An ad plays before I even start my first song"],
        "recommended_action": "Delay the first advertisement until after the user has listened to at least 2 songs in a session."
    },
    {
        "title": "Show download progress and failure notifications",
        "description": "Users are unaware when downloads fail silently. Adding clear progress indicators and failure notifications would reduce frustration and support tickets.",
        "category": "Quick Win",
        "severity": 5, "frequency": 0, "impact": 6,
        "affected_segments": ["Fitness Users", "Premium Subscribers"],
        "supporting_evidence": ["I didn't know my download failed until I was offline"],
        "recommended_action": "Add per-track download progress bars and a notification when a download fails with a one-tap retry action."
    },
    {
        "title": "Add 'Recently Played' history to home screen",
        "description": "Users frequently request quick access to recently played songs and albums. A prominent 'Continue Listening' row on the home screen is a low-effort, high-satisfaction addition.",
        "category": "Quick Win",
        "severity": 3, "frequency": 0, "impact": 7,
        "affected_segments": ["Casual Listeners", "Power Users"],
        "supporting_evidence": ["I always have to search again for what I was listening to"],
        "recommended_action": "Surface a 'Continue Listening' row at the top of the home screen showing the last 6 played tracks/albums."
    }
]

FALLBACK_LONG_TERM = [
    {
        "title": "AI-powered hyper-personalized discovery engine",
        "description": "Users overwhelmingly want better music discovery that goes beyond current recommendation algorithms. Building a contextual recommendation engine (time of day, activity, mood) would differentiate the platform.",
        "category": "Long-term Opportunity",
        "severity": 6, "frequency": 0, "impact": 10,
        "affected_segments": ["Power Users", "Casual Listeners", "Students"],
        "supporting_evidence": ["The recommendations are always the same", "I want to discover music I actually like — not just popular songs"],
        "recommended_action": "Invest in a contextual recommendation engine that factors in time-of-day, listening history patterns, mood signals, and explicit user preference signals."
    },
    {
        "title": "Flexible monetization model for free-tier users",
        "description": "A significant portion of negative reviews stem from the perceived value gap between free and premium. Introducing a watch-an-ad-to-skip tier or affordable micro-subscriptions could convert free users.",
        "category": "Long-term Opportunity",
        "severity": 7, "frequency": 0, "impact": 9,
        "affected_segments": ["Free Users", "Students", "Casual Listeners"],
        "supporting_evidence": ["The jump from free to premium is too expensive", "I'd pay a small amount monthly but not the full subscription price"],
        "recommended_action": "Design and test intermediate monetization tiers: a 'Lite' plan with ad-skip tokens, a student bundle, and a family-shared plan with individual profiles."
    },
    {
        "title": "Deep platform stability and performance initiative",
        "description": "Persistent crash and performance reports suggest underlying technical debt. A dedicated 6-month platform stability initiative would dramatically improve review scores and reduce churn.",
        "category": "Long-term Opportunity",
        "severity": 9, "frequency": 0, "impact": 10,
        "affected_segments": ["Premium Subscribers", "Power Users"],
        "supporting_evidence": ["Every update breaks something new", "Been using this app for 5 years — it used to be rock solid"],
        "recommended_action": "Allocate a dedicated engineering squad for 2 quarters focused exclusively on performance benchmarks, memory leak fixes, startup time optimization, and crash rate reduction."
    }
]


def setup_logger(output_dir: str) -> logging.Logger:
    os.makedirs(output_dir, exist_ok=True)
    log_file = os.path.join(output_dir, "insights.log")

    logger = logging.getLogger("ProductInsights")
    logger.setLevel(logging.INFO)
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


def _aggregate_pain_points(analyzed_reviews: List[dict], top_n: int = TOP_N_PAIN_POINTS) -> List[Dict]:
    """Count the most frequently mentioned pain points across all analyzed reviews."""
    counter: Counter = Counter()
    for r in analyzed_reviews:
        for pp in r.get("analysis", {}).get("pain_points", []):
            if pp.strip():
                counter[pp.strip().lower()] += 1
    return [{"text": k, "count": v} for k, v in counter.most_common(top_n)]


def _aggregate_feature_requests(analyzed_reviews: List[dict], top_n: int = TOP_N_FEATURES) -> List[Dict]:
    """Count the most frequently mentioned feature requests across all analyzed reviews."""
    counter: Counter = Counter()
    for r in analyzed_reviews:
        for fr in r.get("analysis", {}).get("feature_requests", []):
            if fr.strip():
                counter[fr.strip().lower()] += 1
    return [{"text": k, "count": v} for k, v in counter.most_common(top_n)]


def _summarize_themes(themes: List[dict]) -> List[Dict]:
    """Condense themes to title + description + review count + sample reviews."""
    result = []
    for t in themes:
        reviews = t.get("supporting_reviews", [])
        sample = [r["review"] for r in reviews[:MAX_THEME_REVIEWS]]
        result.append({
            "theme_name": t["theme_name"],
            "description": t["description"],
            "review_count": len(reviews),
            "sample_reviews": sample
        })
    return result


def _summarize_segments(segments: List[dict]) -> List[Dict]:
    """Condense segments to name + description + review_count + traits + challenges."""
    result = []
    for s in segments:
        result.append({
            "segment_name": s["segment_name"],
            "description": s["description"],
            "review_count": s["review_count"],
            "traits": s.get("traits", []),
            "primary_challenges": s.get("primary_challenges", []),
        })
    return result


class ProductInsightAgent:
    """Agent 6 — Product Insight Generator (Groq LLM with Instructor validation)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.client = instructor.patch(Groq(api_key=self.api_key)) if self.api_key else None
        if self.client:
            logger.info("Groq client initialized for Product Insight Generation.")
        else:
            logger.warning("GROQ_API_KEY not found. Using heuristic fallback insights.")

    def _fallback_insights(self, pain_point_counts: Dict[str, int], feature_counts: Dict[str, int]) -> ProductInsightSchema:
        """Return pre-built heuristic insights, injecting real frequency counts where available."""
        def inject_freq(items, counts):
            result = []
            for item in items:
                item = dict(item)
                # Try to find a matching count from real data
                key_words = item["title"].lower().split()
                best_match = 0
                for phrase, cnt in counts.items():
                    if any(w in phrase for w in key_words):
                        best_match = max(best_match, cnt)
                item["frequency"] = best_match if best_match > 0 else max(1, len(counts) // 4)
                result.append(ProductInsight(**item))
            return result

        return ProductInsightSchema(
            top_frustrations=inject_freq(FALLBACK_FRUSTRATIONS, pain_point_counts),
            feature_requests=inject_freq(FALLBACK_FEATURE_REQUESTS, feature_counts),
            quick_wins=inject_freq(FALLBACK_QUICK_WINS, pain_point_counts),
            long_term_opportunities=inject_freq(FALLBACK_LONG_TERM, pain_point_counts)
        )

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=30), reraise=True)
    def generate_insights(
        self,
        themes: List[dict],
        segments: List[dict],
        top_pain_points: List[Dict],
        top_feature_requests: List[Dict]
    ) -> ProductInsightSchema:
        """Send synthesized data to Groq LLM and generate structured product insights."""
        if not self.client:
            pain_counts = {p["text"]: p["count"] for p in top_pain_points}
            feat_counts = {f["text"]: f["count"] for f in top_feature_requests}
            return self._fallback_insights(pain_counts, feat_counts)

        payload = {
            "themes": _summarize_themes(themes),
            "segments": _summarize_segments(segments),
            "top_pain_points": top_pain_points,
            "top_feature_requests": top_feature_requests
        }
        user_content = json.dumps(payload, ensure_ascii=False)

        try:
            logger.info("Sending synthesized data to Groq API for product insight generation...")
            logger.info(f"  Themes: {len(themes)} | Segments: {len(segments)} | "
                        f"Pain Points: {len(top_pain_points)} | Feature Requests: {len(top_feature_requests)}")
            start_time = time.time()

            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                response_model=ProductInsightSchema,
                messages=[
                    {"role": "system", "content": INSIGHTS_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Synthesize the following data into product insights:\n{user_content}"}
                ],
                temperature=0.5,
                max_tokens=4096
            )
            latency = time.time() - start_time
            logger.info(f"Received product insights response in {latency:.2f}s.")
            return response
        except Exception as e:
            logger.error(f"Error during Groq API product insights call: {e}")
            raise e


class ProductInsightPipeline:
    """Pipeline coordinating data loading, insight generation, and saving results."""

    def __init__(
        self,
        analyzed_reviews_path: str = ANALYZED_REVIEWS_FILE,
        themes_path: str = THEMES_FILE,
        segments_path: str = SEGMENTS_FILE,
        output_dir: str = OUTPUT_DIR,
        insight_agent: Optional[ProductInsightAgent] = None
    ):
        self.analyzed_reviews_path = analyzed_reviews_path
        self.themes_path = themes_path
        self.segments_path = segments_path
        self.output_dir = output_dir
        self.insight_agent = insight_agent or ProductInsightAgent()

    def load_data(self):
        logger.info("Loading input data for Product Insight Generator...")

        with open(self.analyzed_reviews_path, "r", encoding="utf-8") as f:
            analyzed_reviews = json.load(f)
        logger.info(f"  Loaded {len(analyzed_reviews)} analyzed reviews.")

        if os.path.exists(self.themes_path):
            with open(self.themes_path, "r", encoding="utf-8") as f:
                themes = json.load(f)
            logger.info(f"  Loaded {len(themes)} theme clusters.")
        else:
            logger.warning("  themes.json not found — proceeding without theme data.")
            themes = []

        if os.path.exists(self.segments_path):
            with open(self.segments_path, "r", encoding="utf-8") as f:
                segments = json.load(f)
            logger.info(f"  Loaded {len(segments)} user segments.")
        else:
            logger.warning("  segments.json not found — proceeding without segment data.")
            segments = []

        return analyzed_reviews, themes, segments

    def analyze_from_data(self, analyzed_reviews: list, themes: list, segments: list) -> ProductInsightSchema:
        """Generate insights from in-memory data instead of loading from files."""
        top_pain_points = _aggregate_pain_points(analyzed_reviews, TOP_N_PAIN_POINTS)
        top_feature_requests = _aggregate_feature_requests(analyzed_reviews, TOP_N_FEATURES)

        logger.info(f"Top pain points identified: {len(top_pain_points)}")
        logger.info(f"Top feature requests identified: {len(top_feature_requests)}")

        if top_pain_points:
            logger.info("  Most frequent pain points:")
            for pp in top_pain_points[:5]:
                logger.info(f"    #{pp['count']:>4}x — {pp['text'][:70]}")

        if top_feature_requests:
            logger.info("  Most requested features:")
            for fr in top_feature_requests[:5]:
                logger.info(f"    #{fr['count']:>4}x — {fr['text'][:70]}")

        try:
            insights = self.insight_agent.generate_insights(
                themes=themes,
                segments=segments,
                top_pain_points=top_pain_points,
                top_feature_requests=top_feature_requests
            )
        except Exception as e:
            logger.error(f"All retries failed for insight generation: {e}. Using fallback insights.")
            pain_counts = {p["text"]: p["count"] for p in top_pain_points}
            feat_counts = {f["text"]: f["count"] for f in top_feature_requests}
            insights = self.insight_agent._fallback_insights(pain_counts, feat_counts)

        return insights

    def analyze(self) -> ProductInsightSchema:
        analyzed_reviews, themes, segments = self.load_data()

        # Aggregate frequency counts from reviewed analysis
        top_pain_points = _aggregate_pain_points(analyzed_reviews, TOP_N_PAIN_POINTS)
        top_feature_requests = _aggregate_feature_requests(analyzed_reviews, TOP_N_FEATURES)

        logger.info(f"Top pain points identified: {len(top_pain_points)}")
        logger.info(f"Top feature requests identified: {len(top_feature_requests)}")

        if top_pain_points:
            logger.info("  Most frequent pain points:")
            for pp in top_pain_points[:5]:
                logger.info(f"    #{pp['count']:>4}x — {pp['text'][:70]}")

        if top_feature_requests:
            logger.info("  Most requested features:")
            for fr in top_feature_requests[:5]:
                logger.info(f"    #{fr['count']:>4}x — {fr['text'][:70]}")

        try:
            insights = self.insight_agent.generate_insights(
                themes=themes,
                segments=segments,
                top_pain_points=top_pain_points,
                top_feature_requests=top_feature_requests
            )
        except Exception as e:
            logger.error(f"All retries failed for insight generation: {e}. Using fallback insights.")
            pain_counts = {p["text"]: p["count"] for p in top_pain_points}
            feat_counts = {f["text"]: f["count"] for f in top_feature_requests}
            insights = self.insight_agent._fallback_insights(pain_counts, feat_counts)

        return insights

    def save(self, insights: ProductInsightSchema):
        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, "product_insights.json")

        # Convert to serializable dict grouped by category
        output = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_insights": (
                    len(insights.top_frustrations) +
                    len(insights.feature_requests) +
                    len(insights.quick_wins) +
                    len(insights.long_term_opportunities)
                ),
                "top_frustrations_count": len(insights.top_frustrations),
                "feature_requests_count": len(insights.feature_requests),
                "quick_wins_count": len(insights.quick_wins),
                "long_term_opportunities_count": len(insights.long_term_opportunities)
            },
            "top_frustrations": [i.model_dump() for i in sorted(
                insights.top_frustrations, key=lambda x: x.severity * x.impact, reverse=True
            )],
            "feature_requests": [i.model_dump() for i in sorted(
                insights.feature_requests, key=lambda x: x.frequency * x.impact, reverse=True
            )],
            "quick_wins": [i.model_dump() for i in sorted(
                insights.quick_wins, key=lambda x: x.impact, reverse=True
            )],
            "long_term_opportunities": [i.model_dump() for i in sorted(
                insights.long_term_opportunities, key=lambda x: x.impact, reverse=True
            )]
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"\nProduct insights saved to {output_path}")
        logger.info("\n" + "=" * 56)
        logger.info("  PRODUCT INSIGHT GENERATOR - SUMMARY")
        logger.info("=" * 56)
        logger.info(f"  {'Category':<28} {'Count':>5}  {'Avg Severity':>12}  {'Avg Impact':>10}")
        logger.info("  " + "-" * 54)

        categories = [
            ("Top Frustrations",       insights.top_frustrations),
            ("Feature Requests",       insights.feature_requests),
            ("Quick Wins",             insights.quick_wins),
            ("Long-term Opportunities",insights.long_term_opportunities)
        ]
        for cat_name, items in categories:
            if items:
                avg_sev = sum(i.severity for i in items) / len(items)
                avg_imp = sum(i.impact for i in items) / len(items)
                logger.info(f"  {cat_name:<28} {len(items):>5}  {avg_sev:>12.1f}  {avg_imp:>10.1f}")

        logger.info("=" * 56)
        logger.info("\n  TOP 3 PRIORITY INSIGHTS (severity × impact):")
        all_insights = (
            insights.top_frustrations +
            insights.feature_requests +
            insights.quick_wins +
            insights.long_term_opportunities
        )
        for i, ins in enumerate(sorted(all_insights, key=lambda x: x.severity * x.impact, reverse=True)[:3], 1):
            logger.info(f"  {i}. [{ins.category}] {ins.title}")
            logger.info(f"     Severity={ins.severity} | Impact={ins.impact} | Frequency={ins.frequency}")
        logger.info("=" * 56 + "\n")

    def run(self):
        insights = self.analyze()
        self.save(insights)


if __name__ == "__main__":
    pipeline = ProductInsightPipeline()
    pipeline.run()
