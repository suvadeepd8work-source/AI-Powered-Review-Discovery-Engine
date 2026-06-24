from typing import List, Literal
from pydantic import BaseModel, Field

class CleanedReviewOutput(BaseModel):
    cleaned_text: str = Field(..., description="The standard, translated English text containing no gibberish or spam")
    language: str = Field(..., description="ISO 639-1 language code of the original text (e.g. 'en', 'es')")
    is_spam: bool = Field(..., description="True if the review is gibberish, spam, or advertisement")

class AnalyzedReviewOutput(BaseModel):
    sentiment: Literal['positive', 'neutral', 'negative'] = Field(..., description="Sentiment classification of the review text")
    category: Literal['recommendation', 'ui', 'search', 'performance', 'audio', 'other'] = Field(..., description="Primary topic of the review")
    discovery_friction_flag: bool = Field(..., description="True if user specifically struggles to discover or search for music")
    extracted_barriers: List[str] = Field(default=[], description="Bullet list of specific barriers (e.g., 'repetitive songs', 'bad playlist suggestions')")
