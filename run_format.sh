#!/bin/bash
set -e

# Environment Setup
source ./run_env_setup.sh

# Force correct formatting directly first across all py files
echo "🖌️  Forcing YAPF Python Formatting (2-space indent)..."
git ls-files '*.py' | xargs yapf -i --style="{based_on_style: google, indent_width: 2, column_limit: 80}"

# Run Pre-Commit Hooks (Validates typing via mypy, lints via pylint, formats via yapf, sorts via isort)
echo "🛠️  Running full pre-commit validation suite..."
pre-commit run --all-files

echo "✅ All styling, typing, and formatting checks passed!"
