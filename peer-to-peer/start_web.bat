@echo off
echo ========================================
echo Multi-Agent Orchestrator - Web UI
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

echo Python found!
echo.

REM Check if Flask is installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Flask not found. Installing...
    pip install flask requests
    echo.
)

REM Check if config.json exists
if not exist config.json (
    echo WARNING: config.json not found!
    echo Please create a config.json file with your agent configuration.
    echo See WEB_UI_README.md for examples.
    pause
    exit /b 1
)

echo Starting Multi-Agent Orchestrator Web Server...
echo.
echo Open your browser and navigate to:
echo http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

python app_web.py

pause
