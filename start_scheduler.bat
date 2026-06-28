@echo off
REM Scheduler Startup Script for Windows
REM This script starts the pipeline scheduler for weekly automated execution

echo ========================================
echo Pipeline Scheduler Startup
echo ========================================
echo.

REM Change to the correct directory
cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Using system Python.
)

REM Check if scheduler_config.json exists
if not exist "phase3_orchestration\scheduler_config.json" (
    echo ERROR: scheduler_config.json not found!
    echo Please ensure the configuration file exists.
    pause
    exit /b 1
)

REM Start the scheduler
echo Starting pipeline scheduler...
echo Schedule: Every Monday at 10:00 AM IST
echo Press Ctrl+C to stop the scheduler
echo.

python phase3_orchestration\src\scheduler.py --mode schedule

REM If scheduler exits, pause to show any errors
if errorlevel 1 (
    echo.
    echo Scheduler exited with errors.
    pause
)
