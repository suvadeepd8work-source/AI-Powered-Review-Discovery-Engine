"""
main.py — FastAPI application entry point for the Phase 4 Backend API.

Registers all routers, CORS middleware, and global exception handlers.
"""

import os
import sys

# Ensure src/ is on the path (needed when launching with uvicorn from any directory)
src_dir = os.path.dirname(__file__)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routes import pipeline, reviews, insights, health
from config import API_TITLE, API_VERSION

# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=API_TITLE,
    description=(
        "Backend services for the AI-Powered Review Discovery Engine. "
        "Exposes endpoints for review search, theme clusters, user segments, "
        "product insights, executive reports, pipeline control, and health checks."
    ),
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global error handlers ─────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": str(request.url),
        },
    )

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router,   prefix="/api")
app.include_router(pipeline.router, prefix="/api")
app.include_router(reviews.router,  prefix="/api")
app.include_router(insights.router, prefix="/api")

# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"], summary="Root Health Check")
def read_root():
    """Lightweight root endpoint — confirms the API is reachable."""
    return {
        "project": "AI-Powered Review Discovery Engine",
        "version": API_VERSION,
        "documentation": "/docs",
        "status": "healthy",
        "endpoints": {
            "health":         "/api/health",
            "reviews":        "/api/reviews",
            "themes":         "/api/insights/themes",
            "segments":       "/api/insights/segments",
            "insights":       "/api/insights/insights",
            "report":         "/api/insights/report",
            "latest":         "/api/insights/latest",
            "pipeline_run":   "POST /api/pipeline/run",
            "pipeline_status":"GET  /api/pipeline/status/{run_id}",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
