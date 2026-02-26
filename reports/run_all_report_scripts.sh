#!/bin/bash
# reports/run_all_report_scripts.sh
# Execute all Python scripts within reports subdirectories to regenerate reports and metrics.

# Get the script's directory (reports/)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Establish Pythonic Module Resolution for report_utils from the Project Root
PROJECT_ROOT="$( cd "$DIR/.." && pwd )"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
echo "Generating All Market Reports & Metrics"

# Process Portfolio Metrics First
echo ""
echo "[1/3] Processing Portfolios to Generate Metrics (.tsv)..."
cd "$DIR/portfolios" || exit 1
python3 portfolio_processor.py
echo "Portfolios processed successfully."

# Run Intrinsic Value Example Report
echo ""
echo "[2/4] Generating Intrinsic Value Example Report..."
cd "$DIR/intrinsic_value_analysis" || exit 1
python3 intrinsic_value_report.py
echo "Intrinsic Value Report generated."

# Run NVDA Trade Analysis
echo ""
echo "[3/4] Generating NVDA Earnings Trade Report..."
cd "$DIR/02-25_NVDA_earnings_trade" || exit 1
python3 nvda_trade_analysis.py
echo "NVDA Report generated."

# Run Growth Portfolio Analysis
echo ""
echo "[4/4] Generating Growth Portfolio Outlook Report..."
cd "$DIR/02-25_growth_portfolio_plan" || exit 1
python3 growth_portfolio_plan.py
echo "Growth Portfolio Report generated."
echo ""
echo "✅ All reports and metrics successfully regenerated."
