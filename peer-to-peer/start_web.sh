#!/bin/bash

echo "========================================"
echo "Multi-Agent Orchestrator - Web UI"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "Python found: $(python3 --version)"
echo ""

# Check if Flask is installed
if ! python3 -c "import flask" &> /dev/null; then
    echo "Flask not found. Installing..."
    pip3 install flask requests
    echo ""
fi

# Check if config.json exists
if [ ! -f "config.json" ]; then
    echo "WARNING: config.json not found!"
    echo "Please create a config.json file with your agent configuration."
    echo "See WEB_UI_README.md for examples."
    exit 1
fi

echo "Starting Multi-Agent Orchestrator Web Server..."
echo ""
echo "Open your browser and navigate to:"
echo "http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 app_web.py
