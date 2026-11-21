@echo off
rem IronPulse - run on Windows without Docker
rem First run creates a virtual environment and installs the requirements.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 (
        echo Python 3 was not found. Install it from https://www.python.org/downloads/
        echo and tick "Add Python to PATH" during setup.
        pause
        exit /b 1
    )
    echo Installing requirements...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

if not exist exports mkdir exports
echo Starting IronPulse Fitness Management System...
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 pause
