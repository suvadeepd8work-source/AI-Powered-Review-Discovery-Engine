# Phase 3: Orchestration

![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen)
![Status](https://img.shields.io/badge/Status-Green-brightgreen)

This directory provides the pipeline orchestrator state machine to coordinate sequence logic across the 7 agents.

## Contents
- `src/state_db.py`: Job runs and logging schemas.
- `src/orchestrator.py`: Sequence pipeline engine.
- `tests/test_orchestrator.py`: Orchestrator mock cycle tests.

## Setup & Running
1. Run orchestrator test cycle:
   ```bash
   python src/orchestrator.py
   ```
2. Run tests:
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```
