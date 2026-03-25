#!/bin/bash
# Portfolio Automation Pipeline

set -e
set -o pipefail  # Crucial to fail if internal python fails

# Required on macOS for Homebrew-installed tools like Graphviz (dot)
export PATH="$PATH:/opt/homebrew/bin"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/../" # Move to project root

LOG_DIR="logs"
mkdir -p "$LOG_DIR"

# Ensure Environment is securely configured
source ./run_env_setup.sh

echo "Running Unit Tests"
python3 -m unittest portfolios.test_portfolio_pipeline


echo "Running Code Formatting via run_format.sh"
./run_format.sh || true


echo "Fetching Yahoo Portfolios"
if [[ " $* " == *" --offline "* ]]; then
    echo "Running in OFFLINE fetch mode using cached portfolio.json"
    python3 -m portfolios.yahoo_portfolio_fetcher --local-json portfolios/portfolio.json 2>&1 | tee "$LOG_DIR/yahoo_portfolio_fetcher.log"
else
    echo "Running in LIVE fetch mode using credentials from .env"
    python3 -m portfolios.yahoo_portfolio_fetcher 2>&1 | tee "$LOG_DIR/yahoo_portfolio_fetcher.log"
fi


echo "Processing Portfolios (Metrics Engine)"
python3 -m portfolios.portfolio_processor 2>&1 | tee "$LOG_DIR/portfolio_processor.log"


echo "Generating Comprehensive Markdown Report"
python3 reports/generate_portfolio_report.py 2>&1 | tee "$LOG_DIR/generate_portfolio_report.log"
