#!/bin/bash
set -e

# Ensure logs directory exists
mkdir -p logs

# Environment Setup
if [ ! -d "venv" ]; then
    PYTHON_CMD=${PYTHON_CMD:-""}
    if [ -z "$PYTHON_CMD" ]; then
        if command -v python3.11 &>/dev/null; then
            PYTHON_CMD="python3.11"
        elif command -v python3 &>/dev/null; then
            PYTHON_CMD="python3"
        else
            PYTHON_CMD="python"
        fi
    fi
    echo "Creating virtual environment using $PYTHON_CMD..."
    $PYTHON_CMD -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt --upgrade
else
    source venv/bin/activate
    # pip install -r requirements.txt --upgrade
fi
