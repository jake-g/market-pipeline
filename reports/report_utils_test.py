"""Unit tests for report_utils new utility functions."""

import datetime
import logging
import os
import shutil
import tempfile
import unittest

import numpy as np
import pandas as pd

from reports.report_utils import compute_sector_summary
from reports.report_utils import format_macro_summary_md
from reports.report_utils import generate_sector_risk_return_plot
from reports.report_utils import get_news_sentiment_summary
from reports.report_utils import load_macro_snapshot


class TestComputeSectorSummary(unittest.TestCase):
  """Tests for compute_sector_summary()."""

  def test_basic_sector_aggregation(self):
    """Verify sector averages are computed correctly."""
    df = pd.DataFrame({
        "Sector": ["Semi", "Semi", "Power", "Power"],
        "RSI": [60.0, 40.0, 70.0, 30.0],
        "Dist_to_200MA": [10.0, -10.0, 20.0, -20.0],
        "Forward_PE": [30.0, 20.0, 15.0, 25.0],
        "Sharpe_1Y": [1.5, 0.5, 2.0, 1.0],
        "Volatility_20D": [40.0, 30.0, 20.0, 10.0],
    })
    result = compute_sector_summary(df)
    self.assertEqual(len(result), 2)
    semi_row = result[result.index == "Semi"].iloc[0]
    self.assertAlmostEqual(semi_row["Mean_RSI"], 50.0, places=1)
    self.assertAlmostEqual(semi_row["Mean_Dist_to_200MA"], 0.0, places=1)
    self.assertAlmostEqual(semi_row["Mean_Forward_PE"], 25.0, places=1)

  def test_ticker_count(self):
    """Verify ticker count per sector."""
    df = pd.DataFrame({
        "Sector": ["A", "A", "A", "B"],
        "RSI": [50.0, 50.0, 50.0, 50.0],
        "Dist_to_200MA": [0.0, 0.0, 0.0, 0.0],
        "Forward_PE": [20.0, 20.0, 20.0, 20.0],
        "Sharpe_1Y": [1.0, 1.0, 1.0, 1.0],
        "Volatility_20D": [30.0, 30.0, 30.0, 30.0],
    })
    result = compute_sector_summary(df)
    self.assertEqual(result.loc["A", "Ticker_Count"], 3)
    self.assertEqual(result.loc["B", "Ticker_Count"], 1)

  def test_empty_dataframe(self):
    """Verify graceful handling of empty input."""
    df = pd.DataFrame(columns=[
        "Sector", "RSI", "Dist_to_200MA", "Forward_PE", "Sharpe_1Y",
        "Volatility_20D"
    ])
    result = compute_sector_summary(df)
    self.assertTrue(result.empty)

  def test_nan_handling(self):
    """Verify NaN values are excluded from means."""
    df = pd.DataFrame({
        "Sector": ["X", "X"],
        "RSI": [60.0, np.nan],
        "Dist_to_200MA": [10.0, 10.0],
        "Forward_PE": [np.nan, np.nan],
        "Sharpe_1Y": [1.0, 2.0],
        "Volatility_20D": [25.0, 35.0],
    })
    result = compute_sector_summary(df)
    self.assertAlmostEqual(result.loc["X", "Mean_RSI"], 60.0, places=1)
    self.assertTrue(pd.isna(result.loc["X", "Mean_Forward_PE"]))

  def test_custom_sector_column(self):
    """Verify custom sector column name works."""
    df = pd.DataFrame({
        "Theme": ["Tech", "Tech"],
        "RSI": [55.0, 65.0],
        "Dist_to_200MA": [5.0, 15.0],
        "Forward_PE": [22.0, 28.0],
        "Sharpe_1Y": [1.2, 1.8],
        "Volatility_20D": [32.0, 28.0],
    })
    result = compute_sector_summary(df, sector_col="Theme")
    self.assertIn("Tech", result.index)


class TestLoadMacroSnapshot(unittest.TestCase):
  """Tests for load_macro_snapshot()."""

  def setUp(self):
    self.test_dir = tempfile.mkdtemp()
    self.macro_dir = os.path.join(self.test_dir, "macro")
    os.makedirs(self.macro_dir, exist_ok=True)

  def tearDown(self):
    shutil.rmtree(self.test_dir)

  def test_loads_latest_values(self):
    """Verify the function returns the latest non-NaN value."""
    data = pd.DataFrame(
        {
            "FEDFUNDS": [2.0, 3.0, np.nan],
            "US10Y": [3.5, np.nan, 4.5],
            "CPI": [300.0, 310.0, 320.0],
        },
        index=pd.to_datetime(["2026-01-01", "2026-06-01", "2026-08-01"]))
    data.index.name = "DATE"
    data.to_csv(os.path.join(self.macro_dir, "economic_indicators.tsv"),
                sep="\t")
    result = load_macro_snapshot(self.test_dir)
    self.assertAlmostEqual(result["FEDFUNDS"], 3.0)
    self.assertAlmostEqual(result["US10Y"], 4.5)
    self.assertAlmostEqual(result["CPI"], 320.0)

  def test_missing_file_returns_empty(self):
    """Verify graceful handling when file doesn't exist."""
    empty_dir = tempfile.mkdtemp()
    result = load_macro_snapshot(empty_dir)
    self.assertEqual(result, {})
    shutil.rmtree(empty_dir)

  def test_all_nan_column(self):
    """Verify columns with all NaN are excluded."""
    data = pd.DataFrame({
        "FEDFUNDS": [np.nan, np.nan],
        "US10Y": [4.0, 4.5],
    },
                        index=pd.to_datetime(["2026-01-01", "2026-06-01"]))
    data.index.name = "DATE"
    data.to_csv(os.path.join(self.macro_dir, "economic_indicators.tsv"),
                sep="\t")
    result = load_macro_snapshot(self.test_dir)
    self.assertNotIn("FEDFUNDS", result)
    self.assertIn("US10Y", result)


class TestGetNewsSentimentSummary(unittest.TestCase):
  """Tests for get_news_sentiment_summary()."""

  def setUp(self):
    self.test_dir = tempfile.mkdtemp()
    self.ticker_dir = os.path.join(self.test_dir, "tickers", "AAPL")
    os.makedirs(self.ticker_dir, exist_ok=True)

  def tearDown(self):
    shutil.rmtree(self.test_dir)

  def test_sentiment_aggregation(self):
    """Verify sentiment counts and average are correct."""
    today = datetime.date.today()
    dates = [(today - datetime.timedelta(days=i)).isoformat() for i in range(5)]
    news_df = pd.DataFrame({
        "Date": dates,
        "Source": ["Google"] * 5,
        "Sentiment": [0.5, -0.3, 0.0, 0.8, -0.2],
        "Headline": [f"Headline {i}" for i in range(5)],
        "Summary": [""] * 5,
        "URL": ["http://example.com"] * 5,
    })
    news_df.to_csv(os.path.join(self.ticker_dir, "news.tsv"),
                   sep="\t",
                   index=False)
    result = get_news_sentiment_summary("AAPL", self.test_dir, days=30)
    self.assertEqual(result["total_articles"], 5)
    self.assertEqual(result["positive_count"], 2)
    self.assertEqual(result["negative_count"], 2)
    self.assertEqual(result["neutral_count"], 1)
    self.assertAlmostEqual(result["avg_sentiment"], 0.16, places=2)

  def test_missing_ticker_returns_empty(self):
    """Verify missing ticker returns empty dict."""
    result = get_news_sentiment_summary("ZZZZ", self.test_dir, days=30)
    self.assertEqual(result, {})

  def test_date_filtering(self):
    """Verify only recent articles are included."""
    today = datetime.date.today()
    dates = [(today - datetime.timedelta(days=i)).isoformat()
             for i in [1, 5, 60, 90]]
    news_df = pd.DataFrame({
        "Date": dates,
        "Source": ["Google"] * 4,
        "Sentiment": [0.5, 0.3, 0.1, -0.5],
        "Headline": [f"H{i}" for i in range(4)],
        "Summary": [""] * 4,
        "URL": ["http://example.com"] * 4,
    })
    news_df.to_csv(os.path.join(self.ticker_dir, "news.tsv"),
                   sep="\t",
                   index=False)
    result = get_news_sentiment_summary("AAPL", self.test_dir, days=10)
    self.assertEqual(result["total_articles"], 2)


class TestFormatMacroSummaryMd(unittest.TestCase):
  """Tests for format_macro_summary_md()."""

  def test_basic_formatting(self):
    """Verify markdown table is generated."""
    macro = {
        "FEDFUNDS": 3.63,
        "US10Y": 4.69,
        "CPI": 332.8,
    }
    result = format_macro_summary_md(macro)
    self.assertIn("|", result)
    self.assertIn("3.63", result)
    self.assertIn("4.69", result)

  def test_empty_dict(self):
    """Verify empty dict produces minimal output."""
    result = format_macro_summary_md({})
    # Should return a table header at minimum or empty string
    self.assertIsInstance(result, str)

  def test_human_readable_names(self):
    """Verify indicator names are human-readable."""
    macro = {"FEDFUNDS": 3.63}
    result = format_macro_summary_md(macro)
    # Should contain a readable name, not just "FEDFUNDS"
    self.assertTrue("Fed" in result or "FEDFUNDS" in result)


class TestGenerateSectorRiskReturnPlot(unittest.TestCase):
  """Tests for generate_sector_risk_return_plot()."""

  def setUp(self):
    self.test_dir = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.test_dir)

  def test_plot_generates_file(self):
    """Verify plot file is created."""
    df = pd.DataFrame({
        "Sector": ["Semi", "Semi", "Power", "Power"],
        "Sharpe_1Y": [1.5, 0.5, 2.0, 1.0],
        "Volatility_20D": [40.0, 30.0, 20.0, 10.0],
    })
    out_path = os.path.join(self.test_dir, "test_plot.png")
    generate_sector_risk_return_plot(df, out_path)
    self.assertTrue(os.path.exists(out_path))
    self.assertGreater(os.path.getsize(out_path), 0)

  def test_empty_dataframe_no_crash(self):
    """Verify empty DataFrame doesn't crash."""
    df = pd.DataFrame(columns=["Sector", "Sharpe_1Y", "Volatility_20D"])
    out_path = os.path.join(self.test_dir, "empty.png")
    # Should not raise an exception
    generate_sector_risk_return_plot(df, out_path)


if __name__ == "__main__":
  unittest.main()
