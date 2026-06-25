"""
routes/health.py — Health check endpoint.

GET /api/health
  Returns API version, status, and whether pipeline output data exists.
"""

from fastapi import APIRouter
from data_loader import loader
from api_models.response import HealthResponse
from config import API_VERSION

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse, summary="Health Check")
def health_check():
    """
    Returns the API health status and data availability flags.

    - **status**: `ok` if the API is running, `degraded` if data is missing.
    - **data_available**: True when the pipeline has run and produced analyzed reviews.
    - **report_available**: True when the executive report files exist.
    """
    data_ok   = loader.data_available()
    report_ok = loader.report_available()
    return HealthResponse(
        status="ok" if data_ok else "degraded",
        version=API_VERSION,
        data_available=data_ok,
        report_available=report_ok,
    )
