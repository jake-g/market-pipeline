import argparse
import datetime
import logging

import config
from market_fetcher import MarketFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("backfill.log"),
              logging.StreamHandler()])
logger = logging.getLogger(__name__)


def main():
  parser = argparse.ArgumentParser(description="Backfill Historical News")
  parser.add_argument("--tickers",
                      type=str,
                      help="Comma-separated tickers (e.g. NVDA,AMD)")
  parser.add_argument("--sector",
                      type=str,
                      help="Sector name from config (e.g. 'Chips & Semi')")
  parser.add_argument("--days",
                      type=int,
                      default=365 * 2,
                      help="Days to look back (default 2 years)")
  args = parser.parse_args()

  fetcher = MarketFetcher()

  # Determine tickers
  target_tickers = []
  if args.tickers:
    target_tickers = [t.strip() for t in args.tickers.split(",")]
  elif args.sector:
    target_tickers = config.SECTORS.get(args.sector, [])

  if not target_tickers:
    # Default to a small test set if nothing specified
    logger.info(
        "No tickers specified. Defaulting to small test set: NVDA, TSLA")
    target_tickers = ["NVDA", "TSLA"]

  end_date = datetime.date.today()
  start_date = end_date - datetime.timedelta(days=args.days)

  logger.info(f"Starting Backfill for {len(target_tickers)} tickers.")
  logger.info(f"Range: {start_date} to {end_date}")
  logger.info(f"Available Keys: {len(fetcher._av_keys)}")

  if not fetcher._av_keys:
    logger.error("No API Keys found! Aborting.")
    return

  for ticker in target_tickers:
    logger.info(f"--- Processing {ticker} ---")
    try:
      # Updated to use the premium/historical method with explicit flag
      added = fetcher.fetch_historical_news_premium(ticker,
                                                    start_date,
                                                    end_date,
                                                    include_alphavantage=True)
      logger.info(f"Completed {ticker}: Added {added} items.")
    except Exception as e:
      logger.error(f"Failed {ticker}: {e}")

  # After News Backfill, update Financials & Fundamentals
  logger.info("--- Updating Financials & Fundamentals ---")
  try:
    # Use Alpha Vantage logic if keys are present (implied by this script's purpose)
    fetcher.update_financials(target_tickers, include_alphavantage=True)
    fetcher.update_fundamentals(target_tickers, include_alphavantage=True)
  except Exception as e:
    logger.error(f"Failed Financials/Fundamentals: {e}")


if __name__ == "__main__":
  main()
