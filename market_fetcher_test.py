# pylint: disable=protected-access, unspecified-encoding
import datetime
import logging
import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from market_fetcher import MarketFetcher


class TestMarketFetcherIntegration(unittest.TestCase):
  """
    Unified test suite for MarketFetcher.
    Covers:
    - Pipeline Integration (Fetching Prices, Backfill)
    - Structure Verification (TSV formats, folders)
    - Schema Generation & Audit
    """

  def setUp(self):
    # Configure logging to show actual output during tests if needed, or suppress
    logging.basicConfig(level=logging.ERROR)

    self.test_dir = Path(".test_data")
    self.cache_dir = Path(".test_cache")
    # Clean up start
    if self.test_dir.exists():
      shutil.rmtree(self.test_dir)
    if self.cache_dir.exists():
      shutil.rmtree(self.cache_dir)

    self.fetcher = MarketFetcher(data_dir=str(self.test_dir),
                                 cache_dir=str(self.cache_dir))
    self.ticker = "AAPL"

    # Ensure ticker dir exists for manual setup tests
    self.ticker_dir = self.test_dir / "tickers" / self.ticker
    self.ticker_dir.mkdir(parents=True, exist_ok=True)

  def tearDown(self):
    # Clean up end
    if self.test_dir.exists():
      shutil.rmtree(self.test_dir)
    if self.cache_dir.exists():
      shutil.rmtree(self.cache_dir)
    # Remove generated reports
    for f in ["DATA_SCHEMA.md", "DATA_STATS.md"]:
      if os.path.exists(f):
        os.remove(f)

class TestMarketFetcherDataIO(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.ERROR)
    self.test_dir = Path(".test_data")
    self.cache_dir = Path(".test_cache")
    self.ticker = "AAPL"
    self.ticker_dir = self.test_dir / "tickers" / self.ticker
    self.ticker_dir.mkdir(parents=True, exist_ok=True)
    self.fetcher = MarketFetcher(data_dir=str(self.test_dir), cache_dir=str(self.cache_dir))

  def tearDown(self):
    if self.test_dir.exists(): shutil.rmtree(self.test_dir)
    if self.cache_dir.exists(): shutil.rmtree(self.cache_dir)

  def test_deduplication_and_update(self):
    # print("\n🧪 Testing TSV Deduplication & Append...")
    news_tsv = self.ticker_dir / "news.tsv"

    # 1. create initial file
    df1 = pd.DataFrame([{
        'Date': '2024-01-01',
        'Source': 'Test',
        'Headline': 'Old News',
        'Sentiment': 0.0,
        'URL': 'http://test.com/1',
        'Summary': 'Old'
    }])
    df1.to_csv(news_tsv, sep='\t', index=False)

    # 2. Append Duplicate + New
    new_items = [
        {
            'date_str': '2024-01-01',
            'source': 'Test',
            'title': 'Old News Updated',
            'link': 'http://test.com/1',
            'sentiment': 0.1,
            'summary': 'Updated'
        },  # Duplicate URL
        {
            'date_str': '2024-01-02',
            'source': 'Test',
            'title': 'New News',
            'link': 'http://test.com/2',
            'sentiment': 0.5,
            'summary': 'New'
        }  # New
    ]

    self.fetcher._save_news_tsv(self.ticker, new_items)

    # 3. Verify
    df_final = pd.read_csv(news_tsv, sep='\t')
    self.assertEqual(len(df_final), 2, "Should have 2 items")

    # Check sort order (Newest First, then Highest Sentiment)
    # We expect 2024-01-02 (0.5) first
    # If we had same date, higher sentiment should be first.

    self.assertEqual(df_final.iloc[0]['Date'], '2024-01-02')
    self.assertEqual(df_final.iloc[1]['Date'], '2024-01-01')

  def test_news_sorting_sentiment(self):
    # Specific test for same-day sentiment sorting
    news_tsv = self.ticker_dir / "news.tsv"

    test_cases = [
        ("Sorted Mixed", [
            {
                'date': '2024-01-01',
                'source': 'A',
                'title': 'Bad',
                'sentiment': -0.5,
                'link': '1',
                'summary': ''
            },
            {
                'date': '2024-01-01',
                'source': 'B',
                'title': 'Good',
                'sentiment': 0.9,
                'link': '2',
                'summary': ''
            },
            {
                'date': '2024-01-01',
                'source': 'C',
                'title': 'Neutral',
                'sentiment': 0.0,
                'link': '3',
                'summary': ''
            },
        ], [0.9, 0.0, -0.5]),
        ("All Same", [
            {
                'date': '2024-01-01',
                'source': 'A',
                'title': 'A',
                'sentiment': 0.5,
                'link': '1',
                'summary': ''
            },
            {
                'date': '2024-01-01',
                'source': 'B',
                'title': 'B',
                'sentiment': 0.5,
                'link': '2',
                'summary': ''
            },
        ], [0.5, 0.5]),
    ]

    for name, items, expected_sentiments in test_cases:
      with self.subTest(name=name):
        # Clear previous file
        if news_tsv.exists():
          news_tsv.unlink()

        self.fetcher._save_news_tsv(self.ticker, items)
        df = pd.read_csv(news_tsv, sep='\t')

        self.assertEqual(len(df), len(expected_sentiments))
        for i, exp in enumerate(expected_sentiments):
          self.assertAlmostEqual(df.iloc[i]['Sentiment'], exp)

  def test_fuzzy_deduplicate_quality(self):
    """Test that fuzzy deduplication keeps the higher quality item and penalizes Google."""
    data = {
        'Date': ['2023-01-01', '2023-01-01', '2023-01-01'],
        'Headline': [
            'Market is crashing hard', 'Market is crashing hard today',
            'Market is crashing hard now'
        ],
        'Sentiment': [0.0, 0.5, 0.5],
        'Summary': [
            'Short summary', 'This is a much longer summary with more details',
            'Even more detail here'
        ],
        'Source': ['Blog', 'AlphaVantage',
                   'Google News'],  # Google News should be heavily penalized
        'URL': ['http://a.com', 'http://b.com', 'http://c.com']
    }
    df = pd.DataFrame(data)

    # Run dedup
    deduped = self.fetcher._fuzzy_deduplicate(df, threshold=0.8)

    # Should keep the second one (index 1) because it has Sentiment, longer summary, better source
    # Google News (index 2) should be dropped despite having sentiment and summary
    self.assertEqual(len(deduped), 1)
    self.assertEqual(deduped.iloc[0]['URL'], 'http://b.com')
    self.assertEqual(deduped.iloc[0]['Source'], 'AlphaVantage')

  def test_ticker_naming_preservation(self):
    # Verify ^ and = are kept
    test_tickers = ["^GSPC", "CL=F", "EURUSD=X", "BTC-USD"]
    for ticker in test_tickers:
      with self.subTest(ticker=ticker):
        path = self.fetcher.get_ticker_path(ticker)
        self.assertEqual(path.name, ticker,
                         f"Expected {ticker}, got {path.name}")

  def test_full_pipeline_structure(self):
    # print("\n🧪 Testing Full Pipeline Structure...")

    # 1. Update Prices
    self.fetcher.update_prices([self.ticker], start_date="2024-01-01")
    self.assertTrue((self.ticker_dir / "prices.tsv").exists())

    # 2. Backfill (Skipped - logic moved/removed)
    # self.fetcher.backfill_benzinga_history(...)
    # We manually verify if it creates a file if data found.

    # 3. Mock News for Audit Verification if empty
    news_tsv = self.ticker_dir / "news.tsv"
    if not news_tsv.exists():
      df = pd.DataFrame([{
          'Date': '2024-01-01',
          'Source': 'Mock',
          'Headline': 'Mock',
          'Sentiment': 0.0,
          'URL': 'http://mock',
          'Summary': 'Mock'
      }])
      df.to_csv(news_tsv, sep='\t', index=False)

    # 4. Generate & Audit
    self.fetcher.generate_data_schema()
    self.fetcher.generate_data_stats()

    # Verify Reports
    self.assertTrue(os.path.exists(self.test_dir / "SCHEMA.md"))
    self.assertTrue(os.path.exists(self.test_dir / "STATS.md"))

    with open(self.test_dir / "SCHEMA.md") as f:
      content = f.read()
      self.assertIn("news.tsv", content)
      self.assertIn("Summary", content)

    with open(self.test_dir / "STATS.md") as f:
      content = f.read()
      self.assertIn(self.ticker, content)
      self.assertIn("Global Metrics", content)

  def test_topic_folder_structure(self):
    # print("\n🧪 Testing Topic Folder Structure...")
    topic = "AI"
    topic_dir = self.test_dir / "topics" / topic
    topic_dir.mkdir(parents=True, exist_ok=True)
    (topic_dir / "news.tsv").touch()  # Empty is fine directly or with headers

    # Just check if audit picks it up (it might error on empty TSV but handled gracefully?)
    # Let's write headers to be safe
    with open(topic_dir / "news.tsv", 'w') as f:
      f.write("Date\tSource\tHeadline\tSentiment\tURL\tSummary\n")

    self.fetcher.generate_data_stats()
    with open(self.test_dir / "STATS.md") as f:
      content = f.read()
      self.assertIn("AI", content)

  @patch("market_fetcher.Downloader")
  def test_insider_trading(self, mock_downloader_cls):
    # Setup mock
    mock_dl = mock_downloader_cls.return_value
    mock_dl.get.return_value = None  # create_mock_filings would be better but simple pass is enough to test flow

    # We need to mock the file system part effectively or just test that interactions happen
    # Since logic depends on downloaded files, we might need to fake the file existence
    # or just trust the mock is called correctly.
    # Let's just verify it calls downloader.get

    self.fetcher.update_insider_trading([self.ticker])

    # Verify it tried to parse/download
    # Since we didn't create fake files, it won't produce output, but shouldn't crash
    mock_dl.get.assert_called()

  def test_insider_trading_cached(self):
    # Verify downloader is NOT called if cached
    cache_key = f"insider_meta_{self.ticker}"
    self.fetcher._save_cache(cache_key, True)

    with patch("market_fetcher.Downloader") as mock_dl_cls:
      self.fetcher.update_insider_trading([self.ticker])
      mock_dl_cls.assert_not_called()

class TestMarketFetcherExtraction(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.ERROR)
    self.test_dir = Path(".test_data")
    self.cache_dir = Path(".test_cache")
    self.ticker = "AAPL"
    self.ticker_dir = self.test_dir / "tickers" / self.ticker
    self.ticker_dir.mkdir(parents=True, exist_ok=True)
    self.fetcher = MarketFetcher(data_dir=str(self.test_dir), cache_dir=str(self.cache_dir))

  def tearDown(self):
    if self.test_dir.exists(): shutil.rmtree(self.test_dir)
    if self.cache_dir.exists(): shutil.rmtree(self.cache_dir)

  @patch("market_fetcher.requests.get")
  def test_alphavantage_sentiment(self, mock_get):
    # Mock Response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "feed": [{
            "time_published": "20240101T000000",
            "title": "Mock AV News",
            "url": "http://av.mock",
            "overall_sentiment_score": 0.5,
            "summary": "Mock Summary"
        }]
    }
    mock_get.return_value = mock_response

    # Run
    # Run
    items = self.fetcher._fetch_alphavantage_news([self.ticker])

    # Verify
    self.assertEqual(len(items), 1)
    self.assertEqual(items[0]['title'], "Mock AV News")
    self.assertEqual(items[0]['sentiment'], 0.5)

  @patch("market_fetcher.yf.download")
  def test_update_prices(self, mock_download):
    # Setup
    mock_df = pd.DataFrame(
        {
            'Open': [150.0],
            'High': [155.0],
            'Low': [149.0],
            'Close': [152.0],
            'Volume': [1000]
        },
        index=pd.to_datetime(['2024-01-01']))
    mock_download.return_value = mock_df

    # Run
    self.fetcher.update_prices([self.ticker])

    # Verify
    files = list(self.ticker_dir.glob("prices.tsv"))
    self.assertEqual(len(files), 1)
    df = pd.read_csv(files[0], sep='\t', index_col=0)
    self.assertIn('Close', df.columns)
    self.assertEqual(df.index[0], '2024-01-01')

  @patch("market_fetcher.yf.Ticker")
  def test_update_fundamentals(self, mock_ticker_cls):
    # Setup
    mock_ticker = mock_ticker_cls.return_value
    mock_ticker.info = {
        "pegRatio": 1.5,
        "forwardPE": 20,
        "earningsGrowth": 0.15,
        "sector": "Technology"
    }
    mock_ticker.earnings_dates = pd.DataFrame(
        {
            "EPS Estimate": [1.0],
            "Reported EPS": [1.1]
        },
        index=pd.to_datetime(['2024-01-01']))
    mock_ticker.quarterly_cashflow = pd.DataFrame(
        {"Capital Expenditures": [-1000]}, index=pd.to_datetime(['2024-01-01']))

    # Run
    self.fetcher.update_fundamentals([self.ticker])

    # Verify
    self.assertTrue((self.ticker_dir / "fundamentals.tsv").exists())
    self.assertTrue((self.ticker_dir / "earnings.tsv").exists())
    # Financials are now handled by update_financials, so we don't expect it here
    # self.assertTrue((self.ticker_dir / "financials_quarterly.tsv").exists())

    # Check content
    with open(self.ticker_dir / "fundamentals.tsv") as f:
      content = f.read()
      self.assertIn("pegRatio", content)

  @patch("market_fetcher.yf.Ticker")
  def test_update_financials(self, mock_ticker_cls):
    # Setup
    mock_ticker = mock_ticker_cls.return_value

    # Mock Yahoo Data (Metrics x Date) - needs transposition
    dates = pd.to_datetime(['2024-01-01', '2023-10-01'])
    mock_fin = pd.DataFrame({
        dates[0]: [100.0, 50.0],
        dates[1]: [90.0, 45.0]
    },
                            index=["Total Revenue", "Net Income"])

    mock_ticker.quarterly_financials = mock_fin
    mock_ticker.quarterly_balance_sheet = pd.DataFrame()
    mock_ticker.quarterly_cashflow = pd.DataFrame(
    )  # Empty to test partial data

    # Run
    self.fetcher.update_financials([self.ticker], include_alphavantage=False)

    # Verify
    fin_file = self.ticker_dir / "financials_quarterly.tsv"
    self.assertTrue(fin_file.exists())

    df = pd.read_csv(fin_file, sep='\t', index_col=0)
    # Check Transposition: Index should be Date, Columns should be Metrics
    self.assertIn("Total Revenue", df.columns)
    self.assertIn("2024-01-01", df.index)
    self.assertEqual(df.loc["2024-01-01", "Total Revenue"], 100.0)

  def test_update_macro(self):
    # Mock FRED response
    mock_df = pd.DataFrame({"CPIAUCSL": [300.0]},
                           index=pd.to_datetime(['2024-01-01']))

    # Patch read_csv ONLY for the fetcher call
    with patch("market_fetcher.pd.read_csv", return_value=mock_df):
      # Patch config to avoid loop
      with patch("market_fetcher.FRED_SERIES", {"CPI": "CPIAUCSL"}):
        self.fetcher.update_macro()

    # Verify (read_csv is real here)
    macro_file = self.test_dir / "macro" / "economic_indicators.tsv"
    self.assertTrue(macro_file.exists())
    df = pd.read_csv(macro_file, sep='\t', index_col=0)
    self.assertIn("CPI", df.columns)

  @patch("market_fetcher.requests.get")
  def test_alphavantage_sentiment_missing_date(self, mock_get):
    # Mock Response with one valid and one invalid date
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "feed": [
            {
                "time_published": "20240101T000000",
                "title": "Valid News",
                "url": "http://av.mock/1",
                "overall_sentiment_score": 0.5,
                "summary": "Valid Summary"
            },
            {
                "time_published": "",  # Invalid
                "title": "Invalid News",
                "url": "http://av.mock/2",
                "overall_sentiment_score": -0.5,
                "summary": "Invalid Summary"
            }
        ]
    }
    mock_get.return_value = mock_response

    # Run
    # Run
    items = self.fetcher._fetch_alphavantage_news([self.ticker])

    # Verify
    # Should only have 1 item
    self.assertEqual(len(items), 1)
    self.assertEqual(items[0]['title'], "Valid News")

    # Ensure invalid one is gone
    invalid = [i for i in items if i['title'] == "Invalid News"]
    self.assertFalse(
        invalid, "Invalid news item with missing date should be filtered out")

  def test_alphavantage_date_parsing(self):
    """Basic test for AlphaVantage date parsing with various formats."""
    test_cases = [
        ("Standard", "20260219T143000", "2026-02-19"),
        ("No Time", "20260219T000000", "2026-02-19"),
        ("Old Year", "20200101T120000", "2020-01-01"),
    ]

    for name, input_date, expected_date_str in test_cases:
      with self.subTest(name=name):
        with patch("market_fetcher.requests.get") as mock_get:
          mock_response = MagicMock()
          mock_response.status_code = 200
          mock_response.json.return_value = {
              "feed": [{
                  "time_published": input_date,
                  "title": "AV News",
                  "url": "http://av.com",
                  "overall_sentiment_score": 0.5,
                  "source": "AlphaVantage"
              }]
          }
          mock_get.return_value = mock_response

          # Use unique ticker per subTest to ensure cache safety
          test_ticker = f"AV_DATE_{name.replace(' ', '_')}"
          (self.test_dir / "tickers" / test_ticker).mkdir(parents=True,
                                                          exist_ok=True)

          items = self.fetcher._fetch_alphavantage_news([test_ticker])

          self.assertTrue(len(items) > 0)
          self.assertEqual(items[0]['date_str'], expected_date_str)

  @patch("market_fetcher.requests.get")
  @patch("market_fetcher.yf.Ticker")
  def test_update_fundamentals_with_av_refined(self, mock_ticker_cls, mock_get):
    # Setup Yahoo
    mock_ticker = mock_ticker_cls.return_value
    mock_ticker.info = {"pegRatio": 1.5, "trailingPE": 20.0}

    # Setup AV
    self.fetcher._av_keys = ["DUMMY_KEY"]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Symbol": self.ticker,
        "MarketCapitalization": "1000000",
        "PERatio": "25.0",  # Divergent (25 vs 20)
        "PEGRatio": "1.2",  # Divergent (1.2 vs 1.5)
        "ForwardPE": "18.0"  # New field
    }
    mock_get.return_value = mock_response

    # Run with AV enabled
    # We no longer expect a divergence warning here.
    self.fetcher.update_fundamentals([self.ticker], include_alphavantage=True)

    # Verify File Content
    fund_file = self.ticker_dir / "fundamentals.tsv"
    self.assertTrue(fund_file.exists())

    with open(fund_file) as f:
      content = f.read()
      # Yahoo values should be preserved
      self.assertIn("pegRatio\t1.5", content)
      self.assertIn("trailingPE\t20.0", content)

      # AV value added WITHOUT prefix
      self.assertIn("forwardPE\t18.0", content)

      # Ensure NO AV_ prefix
      self.assertNotIn("AV_forwardPE", content)

  @patch("market_fetcher.requests.get")
  def test_fetch_historical_news_premium(self, mock_get):
    self.fetcher._av_keys = ["DUMMY_KEY"]
    # Mock AV Response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "feed": [{
            "time_published": "20200101T000000",
            "title": "Old News",
            "url": "http://old.news",
            "overall_sentiment_score": 0.5,
            "summary": "Summary"
        }]
    }
    mock_get.return_value = mock_response

    # Test Disabled
    count = self.fetcher.fetch_historical_news_premium(
        self.ticker,
        datetime.date(2020, 1, 1),
        datetime.date(2020, 1, 7),
        include_alphavantage=False)
    self.assertEqual(count, 0)

    # Test Enabled - Use a dedicated ticker to avoid cache issues
    hist_ticker = "HIST_TEST"
    (self.test_dir / "tickers" / hist_ticker).mkdir(parents=True, exist_ok=True)

    count = self.fetcher.fetch_historical_news_premium(
        hist_ticker,
        datetime.date(2020, 1, 1),
        datetime.date(2020, 1, 7),
        include_alphavantage=True)
    self.assertEqual(count, 1)

    # Verify File
    news_file = self.test_dir / "tickers" / hist_ticker / "news.tsv"
    self.assertTrue(news_file.exists())
    with open(news_file) as f:
      content = f.read()
      self.assertIn("(AV-Hist)", content)

  @patch("market_fetcher.MarketFetcher._load_cache")
  @patch("market_fetcher.requests.get")
  def test_fetch_historical_news_premium_cached(self, mock_get,
                                                mock_load_cache):
    self.fetcher._av_keys = ["DUMMY_KEY"]
    # Setup Cache Hit
    mock_load_cache.return_value = {
        "feed": [{
            "time_published": "20200101T000000",
            "title": "Cached News",
            "url": "http://cached.news",
            "overall_sentiment_score": 0.9,
            "summary": "Cached"
        }]
    }

    # Run
    hist_ticker = "HIST_CACHE_TEST"
    (self.test_dir / "tickers" / hist_ticker).mkdir(parents=True, exist_ok=True)

    count = self.fetcher.fetch_historical_news_premium(
        hist_ticker,
        datetime.date(2020, 1, 1),
        datetime.date(2020, 1, 7),
        include_alphavantage=True)

    # Verify
    self.assertEqual(count, 1)
    mock_get.assert_not_called()  # Should NOT fetch if cached

  def test_caching_empty_data_and_expiry(self):
    """Test that missing data is cached as empty and expiration is honored."""
    test_ticker = "CACHE_EMPTY_TEST"
    (self.test_dir / "tickers" / test_ticker).mkdir(parents=True, exist_ok=True)

    cache_key = f"yf_quarterly_financials_{test_ticker}"

    # 1. First run: Mock Yahoo to fail, should cache empty DataFrame
    with patch("market_fetcher.yf.Ticker") as mock_ticker_cls:
      mock_ticker = mock_ticker_cls.return_value
      # Emulate missing data by throwing an exception
      type(mock_ticker).quarterly_financials = property(lambda self: getattr(self, "missing", None))

      self.fetcher.update_financials([test_ticker], include_alphavantage=False)

      # Verify empty DataFrame is cached
      data = self.fetcher._load_cache(cache_key)
      self.assertIsNotNone(data)
      self.assertTrue(data.empty)

    # 2. Second run: Mock Yahoo to return data, but cache shouldn't be expired yet
    with patch("market_fetcher.yf.Ticker") as mock_ticker_cls:
      mock_ticker_cls.side_effect = Exception("Should not be called, cache hit expected")

      self.fetcher.update_financials([test_ticker], include_alphavantage=False)

      # Cache should still be the empty DataFrame
      data = self.fetcher._load_cache(cache_key)
      self.assertTrue(data.empty)

    # 3. Third run: Expire the cache manually
    import time
    cache_path = self.fetcher._get_cache_path(cache_key)
    # set modification time to old (expired)
    old_time = time.time() - 90000  # expire config.CACHE_EXPIRY_FUNDAMENTALS
    os.utime(cache_path, (old_time, old_time))

    # Now mock Yahoo to return real data
    with patch("market_fetcher.yf.Ticker") as mock_ticker_cls:
      mock_ticker = mock_ticker_cls.return_value
      mock_ticker.quarterly_financials = pd.DataFrame(
          {pd.to_datetime('2024-01-01'): [100.0]}, index=["Revenue"]
      )
      mock_ticker.quarterly_balance_sheet = pd.DataFrame()
      mock_ticker.quarterly_cashflow = pd.DataFrame()

      self.fetcher.update_financials([test_ticker], include_alphavantage=False)

      # Verify the new data is fetched and cached
      data = self.fetcher._load_cache(cache_key)
      self.assertFalse(data.empty)
      self.assertEqual(data.loc["Revenue", pd.to_datetime('2024-01-01')], 100.0)

if __name__ == "__main__":
  unittest.main()
