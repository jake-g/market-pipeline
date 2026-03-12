#!/usr/bin/env python3
import argparse
import asyncio
import datetime
import logging
import os
import subprocess
import sys
from typing import Optional

from dateutil.relativedelta import relativedelta
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from notebooklm_client import MarketNewsClient
from reports.notebooklm_report import generate_report
from reports.report_utils import get_recent_news

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "rendered")


def is_report_missing(filename: str) -> bool:
  """Checks if the corresponding .pdf or .md file is missing from the reports structure."""
  pdf_path = os.path.join(REPORTS_DIR, filename.replace('.md', '.pdf'))
  md_path = os.path.join(os.path.dirname(REPORTS_DIR), filename)
  return not (os.path.exists(pdf_path) and os.path.exists(md_path))


def generate_monthly_reports(start_year: int = 2026):
  """Generates missing monthly reports from the start year up to the LAST completed month."""
  today = datetime.date.today()
  # Only consider fully completed months
  first_day_of_current_month = datetime.date(today.year, today.month, 1)

  current = datetime.date(start_year, 1, 1)
  while current < first_day_of_current_month:
    next_month = current + relativedelta(months=1)
    last_day_of_month = next_month - relativedelta(days=1)

    filename = f"{current.strftime('%Y-%m')}_MONTHLY_REPORT.md"
    if is_report_missing(filename):
      logger.info(f"Missing Monthly Report found: {filename}")

      logger.info(
          f"Executing native python call for monthly: {current.strftime('%Y-%m-%d')} to {last_day_of_month.strftime('%Y-%m-%d')}"
      )
      asyncio.run(
          generate_report(market_data_dir=config.MARKET_DATA_DIR,
                          mode="monthly",
                          start_date_str=current.strftime("%Y-%m-%d"),
                          end_date_str=last_day_of_month.strftime("%Y-%m-%d")))
    else:
      logger.debug(f"Monthly report present: {filename}")

    current = next_month


def generate_weekly_reports(start_year: int = 2026, start_month: int = 3):
  """
  Generates missing weekly reports starting from the specified year/month
  up to the LAST completed week (Sunday to Saturday).
  """
  today = datetime.date.today()

  # Start at the provided year/month
  current_date = datetime.date(start_year, start_month, 1)

  # Find the first Sunday of this month to start the weekly boundary correctly
  while current_date.weekday() != 6:  # 6 is Sunday
    current_date += datetime.timedelta(days=1)

  # Iterate week by week until we hit the current week
  while True:
    week_end = current_date + datetime.timedelta(days=6)  # Saturday

    # If the end of this week is in the future, the week isn't "over" yet
    if week_end >= today:
      break

    filename = f"{week_end.strftime('%m-%d')}_WEEKLY_REPORT.md"
    if is_report_missing(filename):
      logger.info(f"Missing Weekly Report found: {filename}")

      logger.info(
          f"Executing native python call for weekly: {current_date.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
      )
      asyncio.run(
          generate_report(market_data_dir=config.MARKET_DATA_DIR,
                          mode="weekly",
                          start_date_str=current_date.strftime("%Y-%m-%d"),
                          end_date_str=week_end.strftime("%Y-%m-%d")))
    else:
      logger.debug(f"Weekly report present: {filename}")

    current_date += datetime.timedelta(days=7)


def generate_daily_report():
  """Generates the standard daily report for the current day."""
  logger.info("Generating Daily Report...")

  logger.info("Executing native python call for daily report")
  asyncio.run(
      generate_report(market_data_dir=config.MARKET_DATA_DIR, mode="daily"))


def main():
  parser = argparse.ArgumentParser(
      description="Auto-generate missing historical NotebookLM reports.")
  parser.add_argument(
      "--monthly-start-year",
      type=int,
      default=2026,
      help="Year to begin checking for missing monthly reports.")
  parser.add_argument(
      "--weekly-start-month",
      type=str,
      default="2026-03",
      help="YYYY-MM to begin checking for missing weekly reports.")
  parser.add_argument("--dry-run",
                      action="store_true",
                      help="Print what would be generated without executing.")

  args = parser.parse_args()

  logger.info("==========================================")
  logger.info("Scanning for missing Historical NotebookLM Reports...")
  logger.info("==========================================\n")

  # 2. Backfill any missing historical scopes
  generate_monthly_reports(start_year=args.monthly_start_year)

  parts = args.weekly_start_month.split('-')
  generate_weekly_reports(start_year=int(parts[0]), start_month=int(parts[1]))

  # 3. Generate the daily rollout
  generate_daily_report()

  logger.info("\n✅ Periodic report generation sweep complete.")


if __name__ == "__main__":
  main()
