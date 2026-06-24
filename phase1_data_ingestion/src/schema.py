from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class RawReviewSchema(BaseModel):
    review_text: str = Field(..., min_length=1, description="The body/text of the user review")
    rating: int = Field(..., ge=1, le=5, description="The user rating from 1 to 5")
    review_date: datetime = Field(..., description="Timestamp of the review creation")
    app_version: Optional[str] = Field(None, description="App version associated with the review")
    platform: str = Field(..., description="The platform name ('ios' or 'android')")

    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v: str) -> str:
        platform_lower = v.lower().strip()
        if platform_lower not in ('ios', 'android'):
            raise ValueError("Platform must be either 'ios' or 'android'")
        return platform_lower
