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
from reports.notebooklm_client import MarketNewsClient
from reports.notebooklm_report import generate_report
from reports.report_utils import get_recent_news

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.dirname(os.path.abspath(__file__))
NEWS_DIR = os.path.join(REPORTS_DIR, "news")
RENDERED_DIR = os.path.join(REPORTS_DIR, "rendered")


def is_report_missing(filename: str) -> bool:
  """Checks if the corresponding .pdf or .md file is missing from the reports structure."""
  pdf_path = os.path.join(RENDERED_DIR, filename.replace('.md', '.pdf'))
  md_path = os.path.join(NEWS_DIR, filename)  # New location in reports/news/
  return not (os.path.exists(pdf_path) and os.path.exists(md_path))


def _run_report_with_retry(mode: str,
                           start_date_str: str,
                           end_date_str: Optional[str] = None):
  """Executes generate_report with 1 retry on exception/SystemExit."""
  for attempt in range(1, 3):
    try:
      asyncio.run(
          generate_report(market_data_dir=config.MARKET_DATA_DIR,
                          mode=mode,
                          start_date_str=start_date_str,
                          end_date_str=end_date_str,
                          backfill_news=False))
      return
    except (Exception, SystemExit) as e:
      if attempt < 2:
        logger.warning(
            f"Attempt {attempt} for {mode} report ({start_date_str}) failed: {e}. Retrying in 5s..."
        )
        import time
        time.sleep(5)
      else:
        logger.error(
            f"Failed {mode} report ({start_date_str}) after {attempt} attempts: {e}"
        )


def generate_yearly_reports(start_year: int = 2024,
                            end_year: int = 2025,
                            dry_run: bool = False):
  """Generates missing yearly reports for the specified range."""

  for year in range(start_year, end_year + 1):
    filename = f"{year}_YEARLY_REPORT.md"
    start_date_str = f"{year}-01-01"
    end_date_str = f"{year}-12-31"

    if is_report_missing(filename):
      logger.info(f"Missing Yearly Report found: {filename}")
      if not dry_run:
        _run_report_with_retry("yearly", start_date_str, end_date_str)
    else:
      logger.debug(f"Yearly report present: {filename}")


def generate_prospective_reports(target_year: int = 2026,
                                 dry_run: bool = False):
  """Generates a prospective report for the given year."""
  filename = f"{target_year}_PROSPECTIVE_REPORT.md"
  start_date_str = f"{target_year}-01-01"
  end_date_str = f"{target_year}-12-31"

  if is_report_missing(filename):
    logger.info(f"Missing Prospective Report found: {filename}")
    if not dry_run:
      _run_report_with_retry("yearly_prospective", start_date_str, end_date_str)
  else:
    logger.debug(f"Prospective report present: {filename}")


def generate_monthly_reports(start_year: int = 2025, dry_run: bool = False):
  """Generates missing monthly reports from the start year up to the LAST completed month."""
  today = datetime.date.today()
  # Only consider fully completed months
  first_day_of_current_month = datetime.date(today.year, today.month, 1)

  current = datetime.date(start_year, 1, 1)
  while current < first_day_of_current_month:
    next_month = current + relativedelta(months=1)
    last_day_of_month = next_month - relativedelta(days=1)

    filename = f"{current.strftime('%m')}_MONTHLY_REPORT.md"
    if is_report_missing(filename):
      logger.info(f"Missing Monthly Report found: {filename}")

      if not dry_run:
        _run_report_with_retry("monthly", current.strftime("%Y-%m-%d"),
                               last_day_of_month.strftime("%Y-%m-%d"))
    else:
      logger.debug(f"Monthly report present: {filename}")

    current = next_month


def generate_weekly_reports(start_year: int = 2026,
                            start_month: int = 3,
                            dry_run: bool = False):
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

    # If the end of this week is in the future, we still want to skip it, but maybe break if it's too far out
    if week_end >= today:
      # If the start of the week is also >= today, we're fully in the future, break
      if current_date >= today:
        break
      # Otherwise, this is the CURRENT incomplete week, just break because we only want fully completed weeks
      break

    filename = f"{week_end.strftime('%m-%d')}_WEEKLY_REPORT.md"
    if is_report_missing(filename):
      logger.info(f"Missing Weekly Report found: {filename}")

      if not dry_run:
        _run_report_with_retry("weekly", current_date.strftime("%Y-%m-%d"),
                               week_end.strftime("%Y-%m-%d"))
    else:
      logger.debug(f"Weekly report present: {filename}")

    current_date += datetime.timedelta(days=7)


def generate_daily_reports(start_date: str = "2026-03-06",
                           dry_run: bool = False):
  """Generates missing daily reports starting from the specified date (skipping weekends)."""
  try:
    current_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
  except ValueError:
    current_date = datetime.date(2026, 3, 6)

  today = datetime.date.today()

  while current_date <= today:
    # Skip Weekends (Saturday=5, Sunday=6)
    if current_date.weekday() < 5:
      filename = f"{current_date.strftime('%m-%d')}_DAILY_REPORT.md"

      # We consider daily reports generated *for* that day to be represented by the filename
      # The global project requires just the limit date.
      if is_report_missing(filename):
        logger.info(f"Missing Daily Report found: {filename}")
        if not dry_run:
          _run_report_with_retry("daily", current_date.strftime("%Y-%m-%d"))
      else:
        logger.debug(f"Daily report present: {filename}")

    current_date += datetime.timedelta(days=1)


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
      default="2026-01",
      help="YYYY-MM to begin checking for missing weekly reports.")
  parser.add_argument("--dry-run",
                      action="store_true",
                      help="Print what would be generated without executing.")

  parser.add_argument("--only-daily",
                      action="store_true",
                      help="Only generate daily reports.")
  parser.add_argument("--only-weekly",
                      action="store_true",
                      help="Only generate weekly reports.")
  parser.add_argument("--only-monthly",
                      action="store_true",
                      help="Only generate monthly reports.")
  parser.add_argument("--only-prospective",
                      action="store_true",
                      help="Only generate prospective reports.")
  args = parser.parse_args()

  logger.info("==========================================")
  logger.info("Scanning for missing Historical NotebookLM Reports...")
  logger.info("==========================================\n")

  run_all = not (args.only_daily or args.only_weekly or args.only_monthly or
                 args.only_prospective)

  if run_all or args.only_daily:
    generate_daily_reports(start_date="2026-03-06", dry_run=args.dry_run)

  if run_all or args.only_weekly:
    parts = args.weekly_start_month.split('-')
    generate_weekly_reports(start_year=int(parts[0]),
                            start_month=int(parts[1]),
                            dry_run=args.dry_run)

  if run_all or args.only_monthly:
    current_year = datetime.date.today().year
    for y in range(2026, current_year + 1):
      generate_monthly_reports(start_year=y, dry_run=args.dry_run)

  if run_all or args.only_prospective:
    current_year = datetime.date.today().year
    generate_prospective_reports(target_year=current_year, dry_run=args.dry_run)

  logger.info("\n✅ Periodic report generation sweep complete.")


if __name__ == "__main__":
  main()
