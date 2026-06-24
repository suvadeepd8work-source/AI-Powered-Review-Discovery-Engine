# Phase 4: Backend API

![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen)
![Status](https://img.shields.io/badge/Status-Green-brightgreen)

This directory contains the FastAPI server exposing endpoints for starting jobs, retrieving review lists, and tracking status.

## Contents
- `src/main.py`: Entry point setting CORS policies and routing modules.
- `src/routes/pipeline.py`: Job start and progress checks.
- `src/routes/reviews.py`: Filtered review database search.
- `tests/test_routes.py`: API integration routes test suite.

## Setup & Running
1. Run development server:
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```
2. Run tests:
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```
