from typing import List, Literal
from pydantic import BaseModel, Field

class CleanedReviewOutput(BaseModel):
    cleaned_text: str = Field(..., description="The standard, translated English text containing no gibberish or spam")
    language: str = Field(..., description="ISO 639-1 language code of the original text (e.g. 'en', 'es')")
    is_spam: bool = Field(..., description="True if the review is gibberish, spam, or advertisement")

class AnalyzedReviewOutput(BaseModel):
    sentiment: Literal['positive', 'neutral', 'negative'] = Field(..., description="Overall sentiment classification of the review")
    emotion: str = Field(..., description="Dominant emotion expressed in the review (e.g., frustration, satisfaction, disappointment, excitement, neutral)")
    pain_points: List[str] = Field(default=[], description="List of specific difficulties, issues, or friction points mentioned by the user")
    feature_requests: List[str] = Field(default=[], description="List of specific features, enhancements, or changes requested by the user")
    positive_feedback: List[str] = Field(default=[], description="Aspects of the app or experience that the user praised or liked")
    negative_feedback: List[str] = Field(default=[], description="Aspects of the app or experience that the user criticized or disliked")
    jobs_to_be_done: List[str] = Field(default=[], description="The core goals, tasks, or jobs the user is trying to accomplish with the app (e.g., discover new music, listen to offline podcasts)")

