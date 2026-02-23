#!/bin/bash
# Wrapper script to quickly launch the Market Pipeline Dashboard server

# Ensure environment is sourced
source ./run_env_setup.sh

echo "Git Status:"
git status -s
echo "Starting Market Pipeline Dashboard Server..."
python3 market_dashboard_server.py
