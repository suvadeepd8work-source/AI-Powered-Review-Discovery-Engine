from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import pipeline, reviews

app = FastAPI(
    title="AI-Powered Review Discovery Engine API",
    description="Backend services for ingesting and analyzing music reviews using AI agents and Groq LLMs.",
    version="1.0.0"
)

# Setup CORS policy configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include subrouters
app.include_router(pipeline.router, prefix="/api")
app.include_router(reviews.router, prefix="/api")

@app.get("/")
def read_root():
    return {
        "project": "AI-Powered Review Discovery Engine",
        "documentation": "/docs",
        "status": "healthy"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
