#!/bin/bash
# Portfolio Automation Pipeline

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/../" # Move to project root

LOG_DIR="logs"
mkdir -p "$LOG_DIR"

echo "Running Unit Tests"
python3 -m unittest portfolios.test_portfolio_pipeline


echo "Running Code Formatting via run_format.sh"
./run_format.sh || true


echo "Fetching Yahoo Portfolios"
# Demo OFFLINE mode using cached portfolio.json:
# python3 -m portfolios.yahoo_portfolio_fetcher --local-json portfolios/portfolio.json 2>&1 | tee "$LOG_DIR/yahoo_portfolio_fetcher.log"

echo "Running in LIVE fetch mode using credentials from .env"
python3 -m portfolios.yahoo_portfolio_fetcher 2>&1 | tee "$LOG_DIR/yahoo_portfolio_fetcher.log"


echo "Processing Portfolios (Metrics Engine)"
python3 -m portfolios.portfolio_processor 2>&1 | tee "$LOG_DIR/portfolio_processor.log"


echo "Generating Comprehensive Markdown Report"
python3 -m portfolios.generate_portfolio_report 2>&1 | tee "$LOG_DIR/generate_portfolio_report.log"
