import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("logs/backfill_sentiment.log"),
                        logging.StreamHandler()
                    ])

# Constants
END_DATE = pd.Timestamp.now().normalize()


def backfill_sentiment(legacy_dir: Path, market_data_dir: Path):
  """
    Reads LSTM-processed sentiment data ({ticker}_daily_processed.csv) and converts to news_sentiment.tsv.
    Removes legacy 'Sentiment_Daily'/'News_Volume' from prices.tsv if present.
    """
  logging.info("Starting Sentiment Backfill...")

  if not market_data_dir.exists():
    logging.error(f"Market data directory not found: {market_data_dir}")
    return 0, 0

  tickers_root = market_data_dir / "tickers"
  if not tickers_root.exists():
    logging.error(f"Tickers directory not found: {tickers_root}")
    return 0, 0

  tickers = [d.name for d in tickers_root.iterdir() if d.is_dir()]
  logging.info(f"Found {len(tickers)} tickers in market data.")

  processed_count = 0
  skipped_count = 0
  cleaned_prices_count = 0
  deleted_empty_count = 0

  for ticker in tqdm(tickers, desc="Backfilling LSTM Data"):
    ticker_dir = tickers_root / ticker
    prices_path = ticker_dir / "prices.tsv"
    sentiment_out_path = ticker_dir / "news_sentiment.tsv"

    # Legacy Path: expected to be {ticker}_daily_processed.csv
    lstm_path = legacy_dir / f"{ticker}_daily_processed.csv"

    # 1. Clean prices.tsv (remove Sentiment/Volume if they exist)
    if prices_path.exists():
      try:
        df_prices = pd.read_csv(prices_path, sep='\t')
        cols_to_drop = [
            c for c in ['Sentiment_Daily', 'News_Volume']
            if c in df_prices.columns
        ]
        if cols_to_drop:
          df_prices.drop(columns=cols_to_drop, inplace=True)
          df_prices.to_csv(prices_path, sep='\t', index=False)
          cleaned_prices_count += 1
      except Exception as e:
        logging.error(f"Error cleaning prices.tsv for {ticker}: {e}")

    # 2. Create news_sentiment.tsv
    if not lstm_path.exists():
      skipped_count += 1
      continue

    try:
      # Load LSTM Data
      df_lstm = pd.read_csv(lstm_path, parse_dates=['date'])

      # Check needed columns
      if 'sentiment' not in df_lstm.columns or 'num_articles' not in df_lstm.columns:
        logging.warning(f"Missing columns in LSTM data for {ticker}")
        continue

      # Rename
      df_lstm.rename(columns={
          'date': 'Date',
          'sentiment': 'Sentiment_Daily',
          'num_articles': 'News_Volume'
      },
                     inplace=True)

      # Select columns
      df_out = df_lstm[['Date', 'Sentiment_Daily', 'News_Volume']].copy()

      # Logic: If News_Volume is 0, Set BOTH Sentiment and Volume to NaN
      df_out['News_Volume'] = df_out['News_Volume'].astype(float)

      mask_zero_vol = df_out['News_Volume'] == 0
      df_out.loc[mask_zero_vol, 'Sentiment_Daily'] = np.nan
      df_out.loc[mask_zero_vol, 'News_Volume'] = np.nan

      # Round sentiment
      df_out['Sentiment_Daily'] = df_out['Sentiment_Daily'].round(4)

      # Trim leading NaNs
      first_valid_idx = df_out['News_Volume'].first_valid_index()

      if first_valid_idx is None:
        logging.debug(f"No valid backfill data for {ticker}, skipping.")
        skipped_count += 1
        continue

      # Slice from first valid data
      df_out = df_out.loc[first_valid_idx:].copy()

      # Reset index to Date for reindexing
      df_out.set_index('Date', inplace=True)

      # Get the starting date
      start_date = df_out.index.min()

      # Create full business date range up to target END_DATE
      full_idx = pd.date_range(start=start_date, end=END_DATE, freq='B')

      # Reindex (fills missing dates with NaN)
      df_out = df_out.reindex(full_idx)

      # Reset index to make Date a column again
      df_out.index.name = 'Date'
      df_out.reset_index(inplace=True)

      # Merge with existing if present
      if sentiment_out_path.exists():
        try:
          existing_df = pd.read_csv(sentiment_out_path,
                                    sep='\t',
                                    parse_dates=['Date'])
          # Concat existing first so keep='first' preserves it
          combined_df = pd.concat([existing_df, df_out])
          # Deduplicate by Date, keeping existing data
          combined_df = combined_df.drop_duplicates(subset=['Date'],
                                                    keep='first')
          # Sort
          combined_df = combined_df.sort_values(by='Date')
          df_out = combined_df
        except Exception as e:
          logging.warning(
              f"Could not read existing {sentiment_out_path} for merging: {e}. Overwriting."
          )

      # Save
      df_out.to_csv(sentiment_out_path,
                    sep='\t',
                    index=False,
                    float_format='%.4f',
                    na_rep='')
      processed_count += 1

    except Exception as e:
      logging.error(f"Error processing {ticker}: {e}")
      skipped_count += 1

  logging.info(
      f"Sentiment Backfill complete. Processed {processed_count} tickers. Skipped {skipped_count}. Cleaned {cleaned_prices_count} prices files. Deleted {deleted_empty_count} empty sentiment files."
  )
  return processed_count, skipped_count


def backfill_insider(raw_insider_dir: Path, market_data_dir: Path):
  """
    Reads legacy insider trading CSVs and merges/creates insider_trading.tsv
    Match columns: date -> Date, shares -> Shares, amount -> Amount, buy_flag -> BuyFlag
    """
  logging.info("Starting Insider Backfill...")

  if not market_data_dir.exists():
    logging.error(f"Market data directory not found: {market_data_dir}")
    return 0

  if not raw_insider_dir.exists():
    logging.error(f"Raw Insider data directory not found: {raw_insider_dir}")
    return 0

  tickers_root = market_data_dir / "tickers"
  if not tickers_root.exists():
    logging.error(f"Tickers directory not found: {tickers_root}")
    return 0

  tickers = [d.name for d in tickers_root.iterdir() if d.is_dir()]
  logging.info(f"Checking {len(tickers)} tickers for insider backfill...")

  processed_count = 0
  skipped_count = 0

  for ticker in tqdm(tickers, desc="Backfilling Insider Data"):
    legacy_file = raw_insider_dir / f"{ticker}_insider_trades_daily.csv"
    target_file = tickers_root / ticker / "insider_trading.tsv"

    if not legacy_file.exists():
      skipped_count += 1
      continue

    try:
      # 1. Load Legacy Data
      df_legacy = pd.read_csv(legacy_file)

      # 2. Rename Columns
      df_legacy.rename(columns={
          'date': 'Date',
          'shares': 'Shares',
          'amount': 'Amount',
          'buy_flag': 'BuyFlag'
      },
                       inplace=True)

      # Ensure Column Existence
      required = ['Date', 'Shares', 'Amount', 'BuyFlag']
      if not all(col in df_legacy.columns for col in required):
        logging.warning(
            f"Skipping {ticker}: Insider legacy file missing columns. Found: {df_legacy.columns}"
        )
        continue

      # Standardize Data
      df_legacy['Date'] = pd.to_datetime(df_legacy['Date'], errors='coerce')
      df_legacy.dropna(subset=['Date'], inplace=True)
      df_legacy = df_legacy[required].copy()

      # 3. Merge with Existing
      if target_file.exists():
        try:
          existing_df = pd.read_csv(target_file, sep='\t')
          existing_df['Date'] = pd.to_datetime(existing_df['Date'],
                                               errors='coerce')

          # Concat: Existing FIRST (to prioritize it)
          combined_df = pd.concat([existing_df, df_legacy])

          # Deduplicate: Keep FIRST (Existing)
          combined_df.drop_duplicates(subset=['Date', 'BuyFlag'],
                                      keep='first',
                                      inplace=True)

        except Exception as e:
          logging.warning(
              f"Error reading existing insider file for {ticker}: {e}. Overwriting."
          )
          combined_df = df_legacy
      else:
        combined_df = df_legacy

      # 4. Sort and Save
      combined_df.sort_values(by='Date', inplace=True)
      combined_df.to_csv(target_file, sep='\t', index=False)
      processed_count += 1

    except Exception as e:
      logging.error(f"Error processing insider backfill for {ticker}: {e}")
      skipped_count += 1

  logging.info(
      f"Insider Backfill complete. Processed {processed_count} tickers. Skipped {skipped_count}."
  )
  return processed_count


def main():
  parser = argparse.ArgumentParser(
      description="Backfill Sentiment, Insider, and SPY/VIX Data")
  # Default paths based on project structure
  default_legacy_raw = Path(
      "LSTM_AI_Stock_Predictor-main/TrainingData/indicators_data/raw")
  default_legacy_processed = Path(
      "LSTM_AI_Stock_Predictor-main/TrainingData/indicators_data/processed")
  default_market = Path("market_data")

  parser.add_argument("--legacy-raw-dir",
                      type=Path,
                      default=default_legacy_raw,
                      help="Path to legacy raw data")
  parser.add_argument("--legacy-processed-dir",
                      type=Path,
                      default=default_legacy_processed,
                      help="Path to legacy processed data")
  parser.add_argument("--market-data-dir",
                      type=Path,
                      default=default_market,
                      help="Path to market_data root")
  args = parser.parse_args()

  # 1. Backfill Sentiment (LSTM)
  # Source: indicators_data/processed/stocksData
  sent_dir = args.legacy_processed_dir / "stocksData"
  if sent_dir.exists():
    backfill_sentiment(sent_dir, args.market_data_dir)
  else:
    logging.warning(f"Sentiment dir not found: {sent_dir}")

  # 2. Backfill Insider (Legacy CSVs)
  # Source: indicators_data/raw/insiderBuying
  insider_dir = args.legacy_raw_dir / "insiderBuying"
  if insider_dir.exists():
    backfill_insider(insider_dir, args.market_data_dir)
  else:
    logging.warning(f"Insider dir not found: {insider_dir}")


if __name__ == "__main__":
  main()
