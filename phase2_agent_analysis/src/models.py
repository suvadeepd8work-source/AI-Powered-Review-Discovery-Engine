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

class AnalyzedReviewItem(BaseModel):
    review_index: int = Field(..., description="The 0-based index of the review in the provided input batch")
    sentiment: Literal['positive', 'neutral', 'negative'] = Field(..., description="Overall sentiment classification of the review")
    emotion: str = Field(..., description="Dominant emotion expressed in the review (e.g., frustration, satisfaction, disappointment, excitement, neutral)")
    pain_points: List[str] = Field(default=[], description="List of specific difficulties, issues, or friction points mentioned by the user")
    feature_requests: List[str] = Field(default=[], description="List of specific features, enhancements, or changes requested by the user")
    positive_feedback: List[str] = Field(default=[], description="Aspects of the app or experience that the user praised or liked")
    negative_feedback: List[str] = Field(default=[], description="Aspects of the app or experience that the user criticized or disliked")
    jobs_to_be_done: List[str] = Field(default=[], description="The core goals, tasks, or jobs the user is trying to accomplish with the app")

class AnalyzedReviewBatchOutput(BaseModel):
    batch_results: List[AnalyzedReviewItem] = Field(..., description="The list of analysis results for each review in the batch")


class SupportingReviewItem(BaseModel):
    review: str = Field(..., description="The original review text or complaint text")
    rating: int = Field(..., description="The user rating (1-5)")
    review_date: str = Field(..., description="The date of the review")


class ThemeCluster(BaseModel):
    theme_name: str = Field(..., description="The name of the theme cluster (e.g. 'Performance', 'Pricing', etc.)")
    description: str = Field(..., description="Brief summary description of the issues grouped under this theme")
    supporting_reviews: List[SupportingReviewItem] = Field(..., description="List of supporting reviews belonging to this theme cluster")


class ThemeClusterSchema(BaseModel):
    themes: List[ThemeCluster] = Field(..., description="List of theme clusters generated from reviews")


class UserSegmentReview(BaseModel):
    review: str = Field(..., description="A representative review text for this user segment")
    rating: int = Field(..., description="The user rating (1-5)")
    review_date: str = Field(..., description="The date of the review")


class UserSegment(BaseModel):
    segment_name: str = Field(..., description="The name of the user segment (e.g. 'Power Users', 'Casual Listeners')")
    description: str = Field(..., description="A brief description of this user segment's characteristics and usage patterns")
    traits: List[str] = Field(default=[], description="Key behavioral traits or characteristics of this segment (e.g., 'listens daily', 'uses offline mode')")
    primary_challenges: List[str] = Field(default=[], description="The main pain points or frustrations that this segment commonly experiences")
    jobs_to_be_done: List[str] = Field(default=[], description="Core goals and tasks this segment is trying to accomplish with the app")
    representative_reviews: List[UserSegmentReview] = Field(default=[], description="A sample of reviews from users belonging to this segment")
    review_count: int = Field(default=0, description="Approximate number of reviews attributed to this segment")


class UserSegmentSchema(BaseModel):
    segments: List[UserSegment] = Field(..., description="List of identified user segments")
