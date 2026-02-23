import os
import shutil
import unittest
from pathlib import Path

import pandas as pd

from backfill import legacy_data as backfill_script


class TestImportLegacyData(unittest.TestCase):

  def setUp(self):
    self.test_dir = Path("test_backfill_data")
    self.market_dir = self.test_dir / "market_data" / "tickers"
    self.lstm_dir = self.test_dir / "LSTM_AI_Stock_Predictor-main" / "TrainingData" / "indicators_data" / "processed" / "stocksData"
    self.raw_insider_dir = self.test_dir / "LSTM_AI_Stock_Predictor-main" / "TrainingData" / "indicators_data" / "raw" / "insiderBuying"

    # Setup Dirs
    self.market_dir.mkdir(parents=True, exist_ok=True)
    self.lstm_dir.mkdir(parents=True, exist_ok=True)
    self.raw_insider_dir.mkdir(parents=True, exist_ok=True)

    # Patch Module Paths
    backfill_script.MARKET_DATA_DIR = self.market_dir
    backfill_script.LSTM_DATA_DIR = self.lstm_dir
    backfill_script.RAW_INSIDER_DIR = self.raw_insider_dir
    backfill_script.END_DATE = pd.Timestamp("2026-02-01")  # Shorten for test

  def tearDown(self):
    if self.test_dir.exists():
      shutil.rmtree(self.test_dir)

  def test_backfill_sentiment(self):
    ticker = "TEST"
    ticker_dir = self.market_dir / ticker
    ticker_dir.mkdir()

    # 1. Create Prices (Dirty)
    prices_df = pd.DataFrame({
        'Date': ['2023-01-01'],
        'Close': [100],
        'Sentiment_Daily': [0.5],  # Should be removed
        'News_Volume': [10]  # Should be removed
    })
    prices_df.to_csv(ticker_dir / "prices.tsv", sep='\t', index=False)

    # 2. Create LSTM Data (Source)
    lstm_df = pd.DataFrame({
        'date': ['2023-01-01', '2023-01-02'],
        'sentiment': [0.1, 0.2],
        'num_articles': [5, 0]  # 0 volume should become NaN
    })
    lstm_df.to_csv(self.lstm_dir / f"{ticker}_daily_processed.csv", index=False)

    # 3. Run Backfill
    backfill_script.backfill_sentiment(self.lstm_dir, self.market_dir.parent)

    # 4. Verify Prices Cleaned
    cleaned_prices = pd.read_csv(ticker_dir / "prices.tsv", sep='\t')
    self.assertNotIn('Sentiment_Daily', cleaned_prices.columns)
    self.assertNotIn('News_Volume', cleaned_prices.columns)

    # 5. Verify Sentiment Created
    sent_path = ticker_dir / "news_sentiment.tsv"
    self.assertTrue(sent_path.exists())

    sent_df = pd.read_csv(sent_path, sep='\t')
    self.assertIn('Sentiment_Daily', sent_df.columns)
    self.assertIn('News_Volume', sent_df.columns)

  def test_backfill_insider(self):
    ticker = "TEST_INSIDER"
    ticker_dir = self.market_dir / ticker
    ticker_dir.mkdir()

    # 1. Create Legacy Insider Data
    legacy_df = pd.DataFrame({
        'date': ['2023-01-01', '2023-01-02'],
        'shares': [100, -50],
        'amount': [1000, -500],
        'buy_flag': [1, 0]
    })
    legacy_df.to_csv(self.raw_insider_dir /
                     f"{ticker}_insider_trades_daily.csv",
                     index=False)

    # 2. Create Existing Data (to test merge)
    existing_df = pd.DataFrame({
        'Date': ['2023-01-01'],
        'Shares': [999],  # Different value to check prioritization
        'Amount': [9999],
        'BuyFlag': [1]
    })
    existing_df.to_csv(ticker_dir / "insider_trading.tsv",
                       sep='\t',
                       index=False)

    # 3. Run Backfill
    backfill_script.backfill_insider(self.raw_insider_dir,
                                     self.market_dir.parent)

    # 4. Verify Merge
    insider_path = ticker_dir / "insider_trading.tsv"
    self.assertTrue(insider_path.exists())

    merged_df = pd.read_csv(insider_path, sep='\t')

    # Should keep existing 2023-01-01 (999 shares) and add 2023-01-02
    # Actually logic is: keep='first' on drop_duplicates(subset=['Date', 'BuyFlag'])
    # Existing has (2023-01-01, 1). Legacy has (2023-01-01, 1).
    # We concat [existing, legacy]. keep='first' -> should keep existing.

    row_1 = merged_df[(merged_df['Date'] == '2023-01-01') &
                      (merged_df['BuyFlag'] == 1)]
    self.assertEqual(row_1['Shares'].values[0], 999)

    row_2 = merged_df[merged_df['Date'] == '2023-01-02']
    self.assertEqual(row_2['Shares'].values[0], -50)


if __name__ == "__main__":
  unittest.main()
