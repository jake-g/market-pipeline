#!/bin/bash
# Helper script to update Yahoo Finance credentials automatically from macOS clipboard.
# Simply click "Copy as cURL" in Chrome and run this script!

if ! command -v pbpaste &> /dev/null; then
    echo "ERROR: pbpaste not found. This script requires macOS."
    exit 1
fi

CURL_DUMP=$(pbpaste)

if [[ -z "$CURL_DUMP" ]] || [[ "$CURL_DUMP" != *"curl "* ]] || [[ "$CURL_DUMP" != *"finance.yahoo.com"* ]]; then
    echo "ERROR: Clipboard does not seem to contain a valid Yahoo Finance cURL command."
    echo "Please go to https://finance.yahoo.com/portfolios in Chrome, open Network tab,"
    echo "find the 'portfolio' request, and select 'Copy as cURL'."
    exit 1
fi

echo "Updating credentials..."
# Activate the root virtual environment using existing script
# Run from the project root so paths in run_env_setup.sh resolve correctly
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
pushd "$PROJECT_ROOT" > /dev/null
source ./run_env_setup.sh
popd > /dev/null

echo "$CURL_DUMP" | python "$(dirname "$0")/yahoo_portfolio_fetcher.py" --update-creds --dump
