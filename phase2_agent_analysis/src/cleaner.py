import os
import re
import json
from datetime import datetime, timezone
from typing import Optional
from groq import Groq
import instructor
from langdetect import detect, LangDetectException
from tenacity import retry, stop_after_attempt, wait_exponential

from models import CleanedReviewOutput
from prompts import CLEANER_SYSTEM_PROMPT

# --- Constants ---------------------------------------------------------------
INPUT_FILE = os.path.join("phase2_agent_analysis", "data", "input", "reviews.json")
OUTPUT_DIR = os.path.join("phase2_agent_analysis", "data", "output")
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended
    "\U00002600-\U000026FF"  # misc symbols
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero-width joiner
    "\U00000023\U000020E3"   # keycap #
    "\U0000002A\U000020E3"   # keycap *
    "\U00000030-\U00000039\U000020E3"  # keycap digits
    "\U0000200B"             # zero-width space
    "\U0000FE0F"             # variation selector
    "]+",
    flags=re.UNICODE
)
MIN_WORD_COUNT = 5


class ReviewCleanerAgent:
    """Agent 2 — Review Cleaner (Groq LLM with Instructor validation)"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.client = instructor.patch(Groq(api_key=self.api_key)) if self.api_key else None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    def clean_review(self, raw_text: str) -> CleanedReviewOutput:
        if not self.client:
            # Fallback if no API key is present
            lang = "en"
            try:
                lang = detect(raw_text)
            except LangDetectException:
                pass
            return CleanedReviewOutput(
                cleaned_text=raw_text,
                language=lang,
                is_spam=False
            )
        try:
            response = self.client.chat.completions.create(
                model="llama-3-8b-8192",
                response_model=CleanedReviewOutput,
                messages=[
                    {"role": "system", "content": CLEANER_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Raw Review: '{raw_text}'"}
                ],
                temperature=0.1
            )
            return response
        except Exception as e:
            print(f"[Cleaner Agent] API call failed: {e}. Falling back to default.")
            lang = "en"
            try:
                lang = detect(raw_text)
            except LangDetectException:
                pass
            return CleanedReviewOutput(
                cleaned_text=raw_text,
                language=lang,
                is_spam=False
            )


class DataCleanerAgent:
    """Agent 2 — Data Cleaner (Orchestrator pipeline)

    Reads raw reviews from Phase 1 output and applies the following filters:
      1. Remove empty / whitespace-only reviews
      2. Remove reviews with fewer than 5 words
      3. Remove emoji-only reviews (no meaningful text after stripping emojis)
      4. Remove duplicate reviews (case-insensitive)
      5. Runs ReviewCleanerAgent (Groq LLM) to translate to English, filter spam, and standardize.
    
    Outputs:
      - filtered_reviews.json  (clean review list)
      - statistics.json        (cleaning run statistics)
    """

    def __init__(self, input_path: str = INPUT_FILE, output_dir: str = OUTPUT_DIR, cleaner_agent: Optional[ReviewCleanerAgent] = None):
        self.input_path = input_path
        self.output_dir = output_dir
        self.cleaner_agent = cleaner_agent or ReviewCleanerAgent()

    def load_reviews(self) -> list:
        print(f"[Cleaner] Loading reviews from {self.input_path}...")
        with open(self.input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"[Cleaner] Loaded {len(data)} raw reviews.")
        return data

    @staticmethod
    def is_empty(text: str) -> bool:
        return not text or not text.strip()

    @staticmethod
    def is_too_short(text: str) -> bool:
        # Strip emojis before counting words so "good 👍" counts as 1 word
        stripped = EMOJI_PATTERN.sub('', text).strip()
        words = stripped.split()
        return len(words) < MIN_WORD_COUNT

    @staticmethod
    def is_emoji_only(text: str) -> bool:
        stripped = EMOJI_PATTERN.sub('', text).strip()
        # Also strip common punctuation and whitespace
        stripped = re.sub(r'[\s\.,!?;:\-\'"]+', '', stripped)
        return len(stripped) == 0

    def clean(self) -> dict:
        reviews = self.load_reviews()

        stats = {
            "total_input": len(reviews),
            "removed_empty": 0,
            "removed_too_short": 0,
            "removed_emoji_only": 0,
            "removed_duplicate": 0,
            "removed_non_english": 0,
            "removed_spam": 0,
            "total_removed": 0,
            "total_output": 0,
            "cleaning_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

        filtered = []
        seen_texts = set()

        for review in reviews:
            text = review.get("review", "")

            # 1. Empty check
            if self.is_empty(text):
                stats["removed_empty"] += 1
                continue

            # 2. Emoji-only check
            if self.is_emoji_only(text):
                stats["removed_emoji_only"] += 1
                continue

            # 3. Too-short check (fewer than 5 words)
            if self.is_too_short(text):
                stats["removed_too_short"] += 1
                continue

            # 4. Duplicate check (case-insensitive, whitespace-normalized)
            normalized = text.strip().lower()
            if normalized in seen_texts:
                stats["removed_duplicate"] += 1
                continue
            seen_texts.add(normalized)

            # 5. LLM Clean & Translate & Spam Check
            cleaned_res = self.cleaner_agent.clean_review(text)

            if cleaned_res.is_spam:
                stats["removed_spam"] += 1
                continue

            # If language detection / translation results in a non-English text, filter it out
            if cleaned_res.language != "en":
                stats["removed_non_english"] += 1
                continue

            # Store the standardized, translated text
            review["review"] = cleaned_res.cleaned_text
            filtered.append(review)

        stats["total_removed"] = (
            stats["removed_empty"]
            + stats["removed_too_short"]
            + stats["removed_emoji_only"]
            + stats["removed_duplicate"]
            + stats["removed_non_english"]
            + stats["removed_spam"]
        )
        stats["total_output"] = len(filtered)

        return {"filtered_reviews": filtered, "statistics": stats}

    def save(self, result: dict):
        os.makedirs(self.output_dir, exist_ok=True)

        reviews_path = os.path.join(self.output_dir, "filtered_reviews.json")
        stats_path = os.path.join(self.output_dir, "statistics.json")

        print(f"[Cleaner] Saving {len(result['filtered_reviews'])} clean reviews to {reviews_path}...")
        with open(reviews_path, 'w', encoding='utf-8') as f:
            json.dump(result["filtered_reviews"], f, indent=2, ensure_ascii=False)

        print(f"[Cleaner] Saving statistics to {stats_path}...")
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(result["statistics"], f, indent=2, ensure_ascii=False)

        # Print summary
        s = result["statistics"]
        print("\n" + "=" * 44)
        print("  DATA CLEANER - SUMMARY")
        print("=" * 44)
        print(f"  Input reviews:        {s['total_input']}")
        print(f"  Removed (empty):      {s['removed_empty']}")
        print(f"  Removed (too short):  {s['removed_too_short']}")
        print(f"  Removed (emoji-only): {s['removed_emoji_only']}")
        print(f"  Removed (duplicate):  {s['removed_duplicate']}")
        print(f"  Removed (non-English):{s['removed_non_english']}")
        print(f"  Removed (spam):       {s['removed_spam']}")
        print(f"  Total removed:        {s['total_removed']}")
        print(f"  Output reviews:       {s['total_output']}")
        print("=" * 44 + "\n")

    def run(self):
        result = self.clean()
        self.save(result)


if __name__ == "__main__":
    agent = DataCleanerAgent()
    agent.run()
