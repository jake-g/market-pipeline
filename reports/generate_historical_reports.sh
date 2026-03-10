#!/bin/bash
set -e

# Ensure logs directory exists
mkdir -p logs

echo "🚀 Starting Historical Market Report Generation..."

# Environment Setup
source ./run_env_setup.sh

# Weekly Reports (February 2026)
WEEKS=(
    "02-01:02-07"
    "02-08:02-14"
    "02-15:02-21"
    "02-22:02-28"
)

for WEEK in "${WEEKS[@]}"
do
    IFS=':' read -r START END <<< "$WEEK"
    START_DATE="2026-${START}"
    END_DATE="2026-${END}"
    echo "======================================"
    echo "Generating WEEKLY report for $START_DATE to $END_DATE..."
    echo "======================================"
    python3 "reports/notebooklm_report.py" --mode weekly --start "$START_DATE" --end "$END_DATE"
done

# Monthly Reports
DAYS_IN_MONTH=(
    "01:31"
    "02:28"
    "03:31"
)

for MONTH_INFO in "${DAYS_IN_MONTH[@]}"
do
    IFS=':' read -r MONTH LAST_DAY <<< "$MONTH_INFO"

    START_DATE="2026-${MONTH}-01"
    END_DATE="2026-${MONTH}-${LAST_DAY}"

    echo "======================================"
    echo "Generating MONTHLY report for 2026-$MONTH..."
    echo "======================================"
    python3 "reports/notebooklm_report.py" --mode monthly --start "$START_DATE" --end "$END_DATE"
done

# Yearly Reports
YEARS=("2018" "2019" "2020" "2021" "2022" "2023" "2024" "2025")
for YEAR in "${YEARS[@]}"
do
    START_DATE="${YEAR}-01-01"
    END_DATE="${YEAR}-12-31"

    echo "======================================"
    echo "Generating YEARLY report for $YEAR..."
    echo "======================================"
    python3 "reports/notebooklm_report.py" --mode yearly --start "$START_DATE" --end "$END_DATE"
done

echo "🎉 Historical Report Generation Complete."
