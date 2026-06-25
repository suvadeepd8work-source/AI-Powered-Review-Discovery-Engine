"""
routes/reviews.py — Analyzed review search and filtering.

GET /api/reviews
  Query params:
    q          — full-text search string (case-insensitive, matches review_text)
    sentiment  — filter: positive | neutral | negative
    category   — filter: recommendation | ui | search | performance | audio
    platform   — filter: ios | android | reddit
    limit      — max results (default 50, max 200)
    offset     — pagination offset (default 0)
"""

from fastapi import APIRouter, Query
from typing import List, Optional

from data_loader import loader
from api_models.response import ReviewResponse, ReviewListResponse

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("", response_model=ReviewListResponse, summary="Search & Filter Reviews")
def get_reviews(
    q:         Optional[str] = Query(None, description="Full-text search in review text"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment: positive | neutral | negative"),
    category:  Optional[str] = Query(None, description="Filter by category: recommendation | ui | search | performance | audio"),
    platform:  Optional[str] = Query(None, description="Filter by platform: ios | android | reddit"),
    limit:     int = Query(50, ge=1, le=200, description="Max number of results (1–200)"),
    offset:    int = Query(0,  ge=0,         description="Pagination offset"),
):
    """
    Returns analyzed reviews with optional full-text search and filtering.

    All filters are case-insensitive. Results are paginated via **limit** and **offset**.
    Returns an empty list when the pipeline has not produced output yet.
    """
    reviews = loader.load_analyzed_reviews()

    # Apply filters
    if q:
        q_lower = q.lower()
        reviews = [r for r in reviews if q_lower in str(r.get("review_text", "")).lower()]

    if sentiment:
        s_lower = sentiment.lower()
        reviews = [r for r in reviews if str(r.get("sentiment", "")).lower() == s_lower]

    if category:
        c_lower = category.lower()
        reviews = [r for r in reviews if str(r.get("category", "")).lower() == c_lower]

    if platform:
        p_lower = platform.lower()
        reviews = [r for r in reviews if str(r.get("platform", "")).lower() == p_lower]

    total = len(reviews)
    page  = reviews[offset : offset + limit]

    result = []
    for i, r in enumerate(page):
        result.append(ReviewResponse(
            id=r.get("id") or r.get("review_id") or str(offset + i + 1),
            review_text=r.get("review_text") or r.get("cleaned_text") or r.get("text", ""),
            sentiment=r.get("sentiment"),
            category=r.get("category"),
            rating=r.get("rating"),
            platform=r.get("platform") or r.get("source"),
            barriers=r.get("extracted_barriers") or r.get("barriers", []),
        ))

    return ReviewListResponse(total=total, offset=offset, limit=limit, reviews=result)
