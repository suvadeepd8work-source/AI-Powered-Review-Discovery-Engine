import os
from typing import Optional
from groq import Groq
import instructor
from models import AnalyzedReviewOutput
from prompts import ANALYZER_SYSTEM_PROMPT
from tenacity import retry, stop_after_attempt, wait_exponential

class ReviewAnalyzerAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        # Wrapping client using instructor for structured extraction
        self.client = instructor.patch(Groq(api_key=self.api_key)) if self.api_key else None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    def analyze_review(self, cleaned_text: str) -> AnalyzedReviewOutput:
        if not self.client:
            # Fallback if no API key is present
            return AnalyzedReviewOutput(
                sentiment="neutral",
                category="other",
                discovery_friction_flag=False,
                extracted_barriers=[]
            )

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

if __name__ == "__main__":
    analyzer = ReviewAnalyzerAgent()
    sample = "The smart playlist recommendations just keep looping the same 5 songs. I can't find anything new."
    result = analyzer.analyze_review(sample)
    print(f"Cleaned Text: {sample}")
    print(f"Sentiment: {result.sentiment} | Category: {result.category}")
    print(f"Discovery Friction Found: {result.discovery_friction_flag}")
    print(f"Barriers: {result.extracted_barriers}")
