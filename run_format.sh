#!/bin/bash
set -e

# Environment Setup
source ./run_env_setup.sh

# Run Pre-Commit Hooks (Validates typing via mypy, lints via pylint, formats via yapf, sorts via isort)
echo "🛠️  Running full pre-commit validation suite..."
pre-commit run --all-files

echo "✅ All styling, typing, and formatting checks passed!"
