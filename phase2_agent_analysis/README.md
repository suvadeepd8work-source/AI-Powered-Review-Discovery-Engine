# Phase 2: Agent Analysis

![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen)
![Status](https://img.shields.io/badge/Status-Green-brightgreen)

This directory houses the Groq LLM integrated agents for cleaning review text (Agent 2) and categorizing discovery barriers (Agent 3).

## Contents
- `src/models.py`: Structured Pydantic LLM outputs.
- `src/prompts.py`: Cleaner and analyzer system prompts.
- `src/cleaner.py`: Data Cleaner agent implementation.
- `src/analyzer.py`: Review Analyzer agent implementation.
- `tests/test_cleaner.py`: Unit mock test cases.

## Setup & Running
1. Set Groq credentials:
   ```bash
   export GROQ_API_KEY="your-groq-key"
   ```
2. Run tests:
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```
