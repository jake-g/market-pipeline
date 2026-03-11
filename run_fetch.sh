#!/bin/bash
set -e

# Ensure logs directory exists
mkdir -p logs

start_time=$(date +%s)

echo "🚀 Starting Full Market Data Pipeline..."
echo "📅 Start Time: $(date)"


# Environment Setup
source ./run_env_setup.sh

# Market Fetcher (Daily/Current)
t0=$(date +%s)
echo "📉 Running Market Fetcher (All Tickers)..."
# ETA Note: Based on the 2/25/2026 run, the full market fetcher (prices, fundamentals, financials, and rss news) takes approximately 10 minutes.
python3 market_fetcher.py 2>&1 | tee logs/run_market_fetcher_full.log
t1=$(date +%s)
echo "✅ Market Fetcher finished in $((t1-t0))s."

# Generate static index for GitHub Pages
echo "🌐 Generating static index.json for dashboard..."
python3 market_dashboard_server.py --build 2>&1 | tee logs/generate_index.log

# Update Portfolios
echo "📈 Running Portfolio Pipeline..."
./portfolios/run_portfolio_pipeline.sh

# Generate LLM Daily News Report
echo "🗄️ Syncing local Market News to NotebookLM Archive (Market Feed)..."
python3 reports/notebooklm_report.py --mode feed_upload 2>&1 | tee logs/sync_notebooklm_archive.log

echo "🗂️ Generating Periodic Reports (Daily + Missing Weekly/Monthly)..."
python3 reports/generate_periodic_reports.py 2>&1 | tee logs/generate_periodic_reports.log

echo "☁️ Syncing all rendered PDF reports to NotebookLM..."
python3 reports/notebooklm_report.py --mode report_upload 2>&1 | tee logs/sync_notebooklm_reports.log

echo "🧹 Running Code Formatting & Validation..."
./run_format.sh

# One off example tasks
# Historical Backfill (FNSPID)
# The script now checks config.DEFAULT_START_DATE internally and exits early if >= 2020.
# echo "📚 Checking Historical Backfill (FNSPID)..."
# python3 backfill/fnspid.py --limit 50000 2>&1 | tee logs/run_backfill_full.log

# Backfill Sentiment Reference (One-Time / Historical)
# echo "🧠 Backfilling Sentiment Reference Data..."
# python3 backfill/legacy_data.py 2>&1 | tee logs/backfill_sentiment.log

# echo "📦 Zipping project for Colab..."
# zip -r market-pipeline.zip . -x "*.git*" "venv/*" "notebooks/.cache/*" "__pycache__/*" "*.DS_Store" "market-pipeline.zip" "logs/*"
# echo "👉 Upload this file when prompted by the Colab notebook."

end_time=$(date +%s)
total_time=$((end_time-start_time))

echo "🎉 Full Pipeline Complete."
echo "⏱️ Total Time: ${total_time}s"

echo "💾 Committing newly generated market data..."
git add market_data/
git commit -m "Auto-update market data: $(date)" || echo "No new market data to commit."
