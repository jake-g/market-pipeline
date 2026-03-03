#!/bin/bash
# reports/run_all_report_scripts.sh
# Execute all Python scripts within reports subdirectories to regenerate reports and metrics.

# Get the script's directory (reports/)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Establish Pythonic Module Resolution for report_utils from the Project Root
PROJECT_ROOT="$( cd "$DIR/.." && pwd )"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
echo "Generating All Market Reports & Metrics"

# Run Intrinsic Value Example Report
echo ""
echo "Generating Intrinsic Value Example Report..."
cd "$DIR/intrinsic_value_analysis" || exit 1
python3 intrinsic_value_report.py
echo "Intrinsic Value Report generated."

# Run NVDA Trade Analysis
echo ""
echo "Generating NVDA Earnings Trade Report..."
cd "$DIR/02-25_NVDA_earnings_trade" || exit 1
python3 nvda_trade_analysis.py
echo "NVDA Report generated."
