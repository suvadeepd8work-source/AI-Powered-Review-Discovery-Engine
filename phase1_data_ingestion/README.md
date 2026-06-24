# Phase 1: Data Ingestion

![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen)
![Status](https://img.shields.io/badge/Status-Green-brightgreen)

This directory contains the ingestion pipeline for retrieving, parsing, validating, and storing raw music reviews.

## Contents
- `src/schema.py`: Pydantic validation rules.
- `src/ingestion.py`: Primary csv/api parsing script.
- `tests/test_ingestion.py`: Ingestion test cases.

## Setup & Running
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run ingestion:
   ```bash
   python src/ingestion.py --file path/to/reviews.csv
   ```
3. Run tests:
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```
