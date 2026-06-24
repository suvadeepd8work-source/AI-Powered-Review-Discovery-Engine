from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/reviews", tags=["Reviews"])

class ReviewResponse(BaseModel):
    id: str
    review_text: str
    sentiment: str
    category: str
    rating: int

# Mock reviews dataset
MOCK_REVIEWS = [
    {
        "id": "1",
        "review_text": "I really struggle to find any new music, recommendations play the same tracks.",
        "sentiment": "negative",
        "category": "recommendation",
        "rating": 2
    },
    {
        "id": "2",
        "review_text": "Sound clarity and quality are absolutely amazing on headphones.",
        "sentiment": "positive",
        "category": "audio",
        "rating": 5
    }
]

@router.get("", response_model=List[ReviewResponse])
def get_reviews(
    sentiment: Optional[str] = Query(None, description="Filter by sentiment (positive, neutral, negative)"),
    category: Optional[str] = Query(None, description="Filter by category (recommendation, audio, etc.)")
):
    results = MOCK_REVIEWS
    if sentiment:
        results = [r for r in results if r["sentiment"] == sentiment.lower()]
    if category:
        results = [r for r in results if r["category"] == category.lower()]
    return results
