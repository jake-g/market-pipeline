#!/bin/bash
set -e

# Environment Setup
if [ -f "run_env_setup.sh" ]; then
    source ./run_env_setup.sh
fi

echo "📊 Starting Portfolio Batch Processor..."
export PYTHONPATH="$(pwd):$PYTHONPATH"
python3 reports/portfolios/portfolio_processor.py
echo "✅ Portfolio Metrics Generation Complete!"
