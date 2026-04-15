#!/bin/bash
# Helper script to update Yahoo Finance credentials.
# Simply click "Copy as cURL" in Chrome and run this script!

echo "Updating credentials..."
# Activate the root virtual environment using existing script
# Run from the project root so paths in run_env_setup.sh resolve correctly
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
pushd "$PROJECT_ROOT" > /dev/null
source ./run_env_setup.sh
popd > /dev/null

python "$(dirname "$0")/yahoo_portfolio_fetcher.py" --update-creds --dump
