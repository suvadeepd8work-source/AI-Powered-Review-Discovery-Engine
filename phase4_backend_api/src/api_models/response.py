"""
models/response.py — Pydantic response schemas for all Phase 4 API endpoints.
All fields use Optional types where the underlying data may be absent,
ensuring graceful serialization even for partially populated pipelines.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# ── Reviews ──────────────────────────────────────────────────────────────────

class ReviewResponse(BaseModel):
    id: Optional[str] = None
    review_text: str
    sentiment: Optional[str] = None      # positive | neutral | negative
    category: Optional[str] = None       # recommendation | ui | search | performance | audio
    rating: Optional[int] = None         # 1–5
    platform: Optional[str] = None       # ios | android | reddit
    barriers: Optional[List[str]] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


class ReviewListResponse(BaseModel):
    total: int
    offset: int
    limit: int
    reviews: List[ReviewResponse]


# ── Themes ───────────────────────────────────────────────────────────────────

class ThemeResponse(BaseModel):
    theme_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    review_count: Optional[int] = None
    representative_reviews: Optional[List[str]] = Field(default_factory=list)
    sentiment_distribution: Optional[Dict[str, int]] = None

    model_config = {"extra": "ignore"}


# ── Segments ─────────────────────────────────────────────────────────────────

class SegmentResponse(BaseModel):
    segment_id: Optional[str] = None
    label: Optional[str] = None
    traits: Optional[List[str]] = Field(default_factory=list)
    challenges: Optional[List[str]] = Field(default_factory=list)
    review_count: Optional[int] = None
    listening_behaviors: Optional[List[str]] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


# ── Product Insights ──────────────────────────────────────────────────────────

class InsightResponse(BaseModel):
    insight_id: Optional[str] = None
    opportunity: Optional[str] = None
    target_segment: Optional[str] = None
    impact_score: Optional[float] = None   # 0.0 – 1.0
    feature_requests: Optional[List[str]] = Field(default_factory=list)
    pain_points: Optional[List[str]] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


# ── Executive Report ─────────────────────────────────────────────────────────

class ReportResponse(BaseModel):
    available: bool
    generated_at: Optional[str] = None
    summary: Optional[str] = None
    markdown_report: Optional[str] = None
    json_report: Optional[Dict[str, Any]] = None


# ── Latest Analysis Snapshot ──────────────────────────────────────────────────

class SentimentDistribution(BaseModel):
    positive: int = 0
    neutral: int = 0
    negative: int = 0


class LatestAnalysisResponse(BaseModel):
    data_available: bool
    total_reviews: int = 0
    total_themes: int = 0
    total_segments: int = 0
    sentiment_distribution: SentimentDistribution = Field(default_factory=SentimentDistribution)
    top_theme: Optional[str] = None
    top_segment: Optional[str] = None
    report_available: bool = False


# ── Pipeline ──────────────────────────────────────────────────────────────────

class PipelineTriggerResponse(BaseModel):
    run_id: str
    status: str
    message: str


class PipelineStatusResponse(BaseModel):
    run_id: str
    status: str
    current_phase: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_execution_time_s: Optional[float] = None
    error_message: Optional[str] = None


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str          # "ok" | "degraded"
    version: str
    data_available: bool
    report_available: bool
