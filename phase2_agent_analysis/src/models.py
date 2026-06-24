from typing import List, Literal
from pydantic import BaseModel, Field, model_validator

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


# ── Agent 6: Product Insight Generator ──────────────────────────────────────

class ProductInsight(BaseModel):
    title: str = Field(..., description="A concise title for this insight (e.g. 'App crashes on startup for Premium users')")
    description: str = Field(..., description="A detailed explanation of the insight, what is causing it, and who it affects")
    category: str = Field(..., description="Category of insight: one of 'Top Frustration', 'Feature Request', 'Quick Win', 'Long-term Opportunity'")
    severity: int = Field(..., ge=1, le=10, description="Severity score 1-10: how serious is the problem or opportunity (10 = critical)")
    frequency: int = Field(..., ge=1, description="Approximate number of reviews that mention or imply this insight")
    impact: int = Field(..., ge=1, le=10, description="Impact score 1-10: potential positive impact on user satisfaction if addressed (10 = transformative)")
    affected_segments: List[str] = Field(default=[], description="List of user segments most affected by this insight (e.g. ['Premium Subscribers', 'Power Users'])")
    supporting_evidence: List[str] = Field(default=[], description="1-3 direct review quotes or paraphrases that exemplify this insight")
    recommended_action: str = Field(..., description="A concrete, actionable recommendation for the product team to address this insight")


class ProductInsightSchema(BaseModel):
    top_frustrations: List[ProductInsight] = Field(default=[], description="The most severe and frequent user pain points and complaints")
    feature_requests: List[ProductInsight] = Field(default=[], description="The most commonly requested new features or improvements")
    quick_wins: List[ProductInsight] = Field(default=[], description="High-impact improvements that are relatively easy to implement quickly")
    long_term_opportunities: List[ProductInsight] = Field(default=[], description="Strategic product opportunities that require more investment but offer significant long-term value")


# ── Agent 7: Executive Report Generator ──────────────────────────────────────

class ExecutiveReportMetrics(BaseModel):
    total_reviews: int = Field(..., description="Total count of reviews processed")
    average_rating: float = Field(..., description="Average user rating across all reviews")
    sentiment_distribution: dict = Field(..., description="Counts and percentages of positive, neutral, and negative sentiment")
    emotion_distribution: dict = Field(..., description="Counts and percentages of different emotions identified")
    total_pain_points: int = Field(..., description="Total aggregated number of pain points identified")
    total_feature_requests: int = Field(..., description="Total aggregated number of feature requests identified")

class ExecutiveReportTheme(BaseModel):
    theme_name: str = Field(..., description="Name of the theme")
    description: str = Field(..., description="Brief description of the theme")
    review_count: int = Field(..., description="Number of reviews classified under this theme")
    percentage: float = Field(..., description="Percentage of problem reviews this theme represents")

class ExecutiveReportSegment(BaseModel):
    segment_name: str = Field(..., description="Name of the user segment")
    description: str = Field(..., description="Profile details for this user segment")
    review_count: int = Field(..., description="Number of reviews attributed to this segment")
    percentage: float = Field(..., description="Percentage of total reviews this segment represents")

class ExecutiveReportInsight(BaseModel):
    title: str = Field(..., description="Concise description of the insight")
    description: str = Field(..., description="Detailed explanation of the findings")
    category: str = Field(..., description="Insight category: e.g. Top Frustration, Feature Request")
    severity: int = Field(..., ge=1, le=10, description="Severity score (1-10)")
    impact: int = Field(..., ge=1, le=10, description="Impact score (1-10)")
    priority_score: int = Field(default=0, description="Combined priority score (severity * impact)")
    affected_segments: List[str] = Field(..., description="User segments affected by this insight")
    recommended_action: str = Field(..., description="Recommended action to address this insight")

    @model_validator(mode='after')
    def calculate_priority(self) -> 'ExecutiveReportInsight':
        self.priority_score = self.severity * self.impact
        return self

class ExecutiveReportPriorityMatrix(BaseModel):
    do_now: List[str] = Field(..., description="High severity & high impact initiatives (Do Now)")
    quick_wins: List[str] = Field(..., description="Low severity & high impact initiatives (Quick Wins)")
    plan: List[str] = Field(..., description="High severity & low impact initiatives (Plan)")
    backlog: List[str] = Field(..., description="Low severity & low impact initiatives (Backlog)")

class ExecutiveReportRecommendation(BaseModel):
    title: str = Field(..., description="Actionable recommendation title")
    description: str = Field(..., description="Detailed explanation of what should be done")
    timeframe: Literal['Immediate', 'Short-term', 'Long-term'] = Field(..., description="Expected timeframe for actioning")
    actionable_steps: List[str] = Field(..., description="Bullet points detailing how to implement")

class ExecutiveReportSchema(BaseModel):
    executive_summary: str = Field(..., description="A high-level synthesis of findings, user sentiment trends, and strategic direction")
    key_metrics: ExecutiveReportMetrics = Field(..., description="Critical statistical summaries of review data")
    top_themes: List[ExecutiveReportTheme] = Field(..., description="List of problem themes ranked by size")
    user_segments: List[ExecutiveReportSegment] = Field(..., description="Summary of user behavioral segments and sizes")
    major_pain_points: List[ExecutiveReportInsight] = Field(..., description="Top frustrations categorized and analyzed")
    feature_requests: List[ExecutiveReportInsight] = Field(..., description="Top feature requests categorized and analyzed")
    priority_matrix: ExecutiveReportPriorityMatrix = Field(..., description="Action items mapped to prioritization quadrants")
    recommendations: List[ExecutiveReportRecommendation] = Field(..., description="Actionable recommendations grouped by timeline")
