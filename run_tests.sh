#!/bin/bash
set -e

echo "🧪 Running All Tests..."
source ./run_env_setup.sh

echo "📉 Market Fetcher Unit Tests..."
python3 -m unittest market_fetcher_test.py

echo "📉 Market Fetcher Integration (Test Mode)..."
# Using limits to ensure quick execution
python3 market_fetcher.py --limit-tickers 3 --limit-topics 2 --news-days 3 --news-limit 3 2>&1 | tee logs/run_market_fetcher_test.log

echo "🧠 LSTM Backfill Integration Test..."
python3 -m unittest backfill/legacy_data_test.py

# echo "📓 Dashboard Notebook Validation (Optional)..."
# python3 notebooks/notebook_test.py notebooks/market_dashboard.ipynb

echo "🧹 Code Quality & Formatting Validation..."
./run_format.sh

echo "🌐 Generating static index.json for dashboard..."
python3 market_dashboard_server.py --build 2>&1 | tee logs/generate_index.log

echo "✅ All Tests Passed!"
