#!/usr/bin/env python3
import argparse
import datetime
import logging
import os
import sys

# Add root project dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_fetcher import MarketFetcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_backfill(start_str: str, end_str: str, thorough: bool = False):
  logger.info(
      f"Initializing MarketFetcher for Topic Backfill (Thorough: {thorough})..."
  )
  fetcher = MarketFetcher()

  try:
    start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
  except ValueError as e:
    logger.error(f"Invalid date format. Expected YYYY-MM-DD: {e}")
    sys.exit(1)

  if start_date >= end_date:
    logger.error("Start date must be strictly before end date.")
    sys.exit(1)

  logger.info(f"Target Date Range: {start_date} to {end_date}")

  total_added = fetcher.fetch_historical_topic_news(start_date=start_date,
                                                    end_date=end_date,
                                                    thorough=thorough)

  logger.info("====================================")
  logger.info(f"BACKFILL COMPLETE")
  logger.info(f"Total News Summaries Indexed: {total_added}")
  logger.info("====================================")


if __name__ == "__main__":
  parser = argparse.ArgumentParser(
      description="Backfill Historical Topic News via Google RSS")
  parser.add_argument("--start",
                      type=str,
                      required=True,
                      help="Start Date (YYYY-MM-DD)")
  parser.add_argument("--end",
                      type=str,
                      required=True,
                      help="End Date (YYYY-MM-DD)")
  parser.add_argument(
      "--thorough",
      action="store_true",
      help="If set, fetches in slower, more granular 90-day intervals.")
  args = parser.parse_args()

  run_backfill(args.start, args.end, thorough=args.thorough)
