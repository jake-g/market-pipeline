#!/bin/bash
set -e

# Environment Setup
source ./run_env_setup.sh

echo "📊 Starting Portfolio Batch Processor..."
cd reports/portfolios
python3 portfolio_processor.py
echo "✅ Portfolio Metrics Generation Complete!"
