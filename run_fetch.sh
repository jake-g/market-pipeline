#!/bin/bash
set -e

# Ensure logs directory exists
mkdir -p logs

start_time=$(date +%s)
echo "📅 Start Time: $(date)"


# Environment Setup
make setup

# Quick pre-flight Auth checks (Yahoo Finance & NotebookLM)
make test-auth

# Running Unit Tests (Fail-Fast before ingestion)
make test-unit

# Market Fetcher (Daily/Current)
t0=$(date +%s)
echo "📉 Running Market Fetcher (All Tickers)..."
# Market fetcher takes approximately 1.5 hours (Prices ~1m, Fundamentals ~10m, Financials ~30m, News ~60m).
python3 market_fetcher.py 2>&1 | tee logs/run_market_fetcher_full.log
t1=$(date +%s)
echo "✅ Market Fetcher finished in $((t1-t0))s."

# Shipping & Logistics Metrics (Bottenecks, Ais, Congestion)
ts0=$(date +%s)
echo "🚢 Running Shipping & Logistics Fetcher..."
python3 shipping_fetcher.py 2>&1 | tee logs/run_shipping_fetcher.log
ts1=$(date +%s)
echo "✅ Shipping Fetcher finished in $((ts1-ts0))s."

# Update Portfolios
make portfolio

# NotebookLM Summarization Tasks
echo "🗄️ Syncing Daily Aggregate News to NotebookLM Archive (Market Feed)..."
python3 reports/notebooklm_report.py --mode feed_upload 2>&1 | tee logs/sync_notebooklm_archive.log

echo "🗂️ Generating Periodic Reports (Daily + Missing Weekly/Monthly)..."
python3 reports/generate_periodic_reports.py 2>&1 | tee logs/generate_periodic_reports.log

echo "☁️ Syncing all rendered PDF reports to NotebookLM..."
python3 reports/notebooklm_report.py --mode report_upload 2>&1 | tee logs/sync_notebooklm_reports.log

# One off example tasks
# Historical Backfill (FNSPID)
# The script now checks config.DEFAULT_START_DATE internally and exits early if >= 2020.
# echo "📚 Checking Historical Backfill (FNSPID)..."
# python3 backfill/fnspid.py --limit 50000 2>&1 | tee logs/run_backfill_full.log

# Historical Shipping Backfill (Future/Paid API)
# echo "🚢 Running Historical Shipping Backfill..."
# ./run_historical_shipping.sh 2>&1 | tee logs/run_historical_shipping.log

# Backfill Sentiment Reference (One-Time / Historical)
# echo "🧠 Backfilling Sentiment Reference Data..."
# python3 backfill/legacy_data.py 2>&1 | tee logs/backfill_sentiment.log

# echo "📦 Zipping project for Colab..."
# zip -r market-pipeline.zip . -x "*.git*" "venv/*" "notebooks/.cache/*" "__pycache__/*" "*.DS_Store" "market-pipeline.zip" "logs/*"
# echo "👉 Upload this file when prompted by the Colab notebook."

# Generate static index for GitHub Pages
echo "🌐 Generating static index.json for dashboard..."
python3 market_dashboard_server.py --build 2>&1 | tee logs/generate_index.log

# Running Code Formatting & Validation at the end to clean up generated files
echo "🧹 Running Code Formatting & Validation..."
make format

end_time=$(date +%s)
total_time=$((end_time-start_time))

echo "🎉 Full Pipeline Complete."
echo "⏱️ Total Time: ${total_time}s"

echo "💾 Committing newly generated market data..."
git add market_data/
git add reports/news/*.md || true
git commit -m "Auto-update market data: $(date)" || echo "No new market data to commit."
