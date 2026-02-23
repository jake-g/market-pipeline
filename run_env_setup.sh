#!/bin/bash
set -e

# Ensure logs directory exists
mkdir -p logs

# Environment Setup
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt --upgrade
else
    source venv/bin/activate
    # pip install -r requirements.txt --upgrade
fi
