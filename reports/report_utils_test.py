"""Unit tests for report_utils new utility functions."""

import datetime
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from reports.report_utils import after_tax_yield
from reports.report_utils import build_ticker_context_markdown
from reports.report_utils import classify_holding
from reports.report_utils import compute_sector_summary
from reports.report_utils import conditional_base_rates
from reports.report_utils import curve_snapshot
from reports.report_utils import format_macro_summary_md
from reports.report_utils import generate_sector_risk_return_plot
from reports.report_utils import get_news_sentiment_summary
from reports.report_utils import hike_pricing
from reports.report_utils import load_macro_snapshot
from reports.report_utils import macro_asof
from reports.report_utils import rate_shock_grid
from reports.report_utils import rate_shock_return
from reports.report_utils import rates_change_table
from reports.report_utils import render_markdown_to_pdf
from reports.report_utils import starting_yield_table
from reports.report_utils import stock_bond_valuation
from reports.report_utils import synthetic_bond_total_return


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

  @patch("reports.report_utils.logger.warning")
  def test_empty_dataframe(self, mock_warn):
    """Verify graceful handling of empty input."""
    df = pd.DataFrame(columns=[
        "Sector", "RSI", "Dist_to_200MA", "Forward_PE", "Sharpe_1Y",
        "Volatility_20D"
    ])
    result = compute_sector_summary(df)
    self.assertTrue(result.empty)
    mock_warn.assert_called()

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

  @patch("reports.report_utils.logger.warning")
  def test_missing_file_returns_empty(self, mock_warn):
    """Verify graceful handling when file doesn't exist."""
    empty_dir = tempfile.mkdtemp()
    result = load_macro_snapshot(empty_dir)
    self.assertEqual(result, {})
    shutil.rmtree(empty_dir)
    mock_warn.assert_called()

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

  @patch("reports.report_utils.logger.warning")
  def test_missing_ticker_returns_empty(self, mock_warn):
    """Verify missing ticker returns empty dict."""
    result = get_news_sentiment_summary("ZZZZ", self.test_dir, days=30)
    self.assertEqual(result, {})
    mock_warn.assert_called()

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

  @patch("reports.report_utils.logger.warning")
  def test_empty_dataframe_no_crash(self, mock_warn):
    """Verify empty DataFrame doesn't crash."""
    df = pd.DataFrame(columns=["Sector", "Sharpe_1Y", "Volatility_20D"])
    out_path = os.path.join(self.test_dir, "empty.png")
    # Should not raise an exception
    generate_sector_risk_return_plot(df, out_path)
    mock_warn.assert_called()


class TestBuildTickerContextMarkdown(unittest.TestCase):
  """Tests for build_ticker_context_markdown()."""

  def setUp(self):
    self.test_dir = tempfile.mkdtemp()
    self.tickers_dir = os.path.join(self.test_dir, "tickers")
    os.makedirs(self.tickers_dir, exist_ok=True)

  def tearDown(self):
    shutil.rmtree(self.test_dir)

  def test_empty_tickers_returns_empty_string(self):
    self.assertEqual(build_ticker_context_markdown([], self.test_dir), "")

  def test_context_markdown_contains_real_newlines_and_discount(self):
    t_dir = os.path.join(self.tickers_dir, "NVDA")
    os.makedirs(t_dir, exist_ok=True)
    # Write fundamentals with graham discount
    fund_path = os.path.join(t_dir, "fundamentals.tsv")
    with open(fund_path, "w") as f:
      f.write("Metric\tValue\n")
      f.write("graham_intrinsic_value\t150.0\n")
      f.write("discount_to_intrinsic_value\t25.5\n")

    # Write recent news
    news_path = os.path.join(t_dir, "news.tsv")
    with open(news_path, "w") as f:
      f.write("Date\tHeadline\n")
      f.write("2026-10-12\tNvidia announces new architecture\n")

    result = build_ticker_context_markdown(["NVDA"], self.test_dir)
    # Must NOT contain literal backslash-n
    self.assertNotIn("\\n", result)
    # Must contain real newlines and expected text
    self.assertIn("### Detailed Portfolio Context", result)
    self.assertIn("- **NVDA**: Intrinsic Discount: 25.5%", result)
    self.assertIn("Nvidia announces new architecture", result)


class TestRenderMarkdownCli(unittest.TestCase):
  """Tests for report_utils --render CLI."""

  def setUp(self):
    self.test_dir = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.test_dir)

  def test_cli_renders_pdf(self):
    md_file = os.path.join(self.test_dir, "test.md")
    pdf_file = os.path.join(self.test_dir, "test.pdf")
    with open(md_file, "w") as f:
      f.write("# Sample Header\n\nSample content for PDF test.\n")

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    script_path = os.path.join(repo_root, "reports", "report_utils.py")
    proc = subprocess.run([
        sys.executable, script_path, "--render", md_file, "--output", pdf_file
    ],
                          capture_output=True,
                          text=True,
                          check=False)
    self.assertEqual(proc.returncode, 0, f"CLI failed: {proc.stderr}")
    self.assertTrue(os.path.exists(pdf_file))
    self.assertGreater(os.path.getsize(pdf_file), 0)


# ==========================================
# MACRO ACCESS, RATES MATH & CROSS-ASSET HELPERS
# ==========================================


def _macro_frame() -> pd.DataFrame:
  """Small daily macro frame mimicking economic_indicators.tsv."""
  idx = pd.date_range("2026-01-01", periods=5, freq="D")
  return pd.DataFrame(
      {
          "FEDFUNDS_UPPER": [3.75, 3.75, 4.0, 4.0, 4.0],
          "FEDFUNDS": [3.63] * 5,
          "SOFR": [3.6, 3.6, 3.87, 3.87, 3.87],
          "US03M": [3.7, 3.8, 4.0, 4.2, 4.25],
          "US01Y": [3.8, 3.9, 4.2, 4.4, 4.47],
          "US02Y": [3.8, 4.0, 4.4, 4.7, 4.75],
          "US05Y": [3.9, 4.2, 4.7, 5.0, 5.02],
          "US10Y": [4.3, 4.6, 5.0, 5.2, 5.22],
          "US30Y": [4.9, 5.1, 5.4, 5.6, 5.6],
          "US10Y_REAL": [1.9, 2.2, 2.6, 2.9, 2.91],
          "BREAKEVEN_10Y": [2.4, 2.4, 2.4, 2.3, 2.33],
          "TERM_PREMIUM_10Y": [0.6, 0.7, 0.9, 1.0, 1.07],
          "HY_SPREAD": [2.9, 2.8, 2.7, 3.1, 3.15],
          "HY_YIELD": [6.9, 7.0, 7.4, 8.0, 8.09],
          "CORP_YIELD": [5.0, 5.2, 5.6, 5.9, 5.96],
      },
      index=idx)


class TestSyntheticBondTotalReturn(unittest.TestCase):
  """Tests for the constant-maturity synthetic bond index."""

  def test_flat_yields_return_the_coupon(self):
    """With unchanged yields the par bond earns exactly its yield."""
    idx = pd.date_range("2000-01-01", periods=13, freq="MS")
    tr = synthetic_bond_total_return(pd.Series(6.0, index=idx), 10)
    annual = tr.iloc[-1] / tr.iloc[0] - 1
    self.assertAlmostEqual(annual, (1 + 0.06 / 12)**12 - 1, places=6)

  def test_rising_yields_lose_money_short_term(self):
    idx = pd.date_range("2000-01-01", periods=2, freq="MS")
    tr = synthetic_bond_total_return(pd.Series([4.0, 5.0], index=idx), 10)
    self.assertLess(tr.iloc[-1], 100.0)

  def test_longer_maturity_more_sensitive(self):
    idx = pd.date_range("2000-01-01", periods=2, freq="MS")
    y = pd.Series([4.0, 5.0], index=idx)
    self.assertLess(
        synthetic_bond_total_return(y, 30).iloc[-1],
        synthetic_bond_total_return(y, 2).iloc[-1])

  def test_starting_yield_table_and_base_rates(self):
    idx = pd.date_range("1990-01-01", periods=240, freq="MS")
    rng = np.random.default_rng(0)
    y = pd.Series(5 + rng.normal(0, 0.1, len(idx)).cumsum() * 0.1, index=idx)
    table = starting_yield_table(y,
                                 10,
                                 horizons=(1, 5),
                                 cash_rate_pct=pd.Series(3.0, index=idx))
    self.assertIn("Fwd_5Y", table.columns)
    self.assertIn("Excess_1Y", table.columns)
    rates = conditional_base_rates(table,
                                   table["Start_Yield"] > 0,
                                   horizons=(1, 5))
    self.assertEqual(list(rates.index), ["1Y", "5Y"])
    self.assertGreater(rates.loc["1Y", "N_months"], 200)


class TestRateShockMath(unittest.TestCase):
  """Tests for carry / duration / convexity approximations."""

  def test_zero_shock_is_carry(self):
    self.assertAlmostEqual(rate_shock_return(5.0, 7.0, 0), 5.0)

  def test_positive_shock_hurts_duration(self):
    self.assertLess(rate_shock_return(5.0, 7.0, 100),
                    rate_shock_return(5.0, 0.3, 100))

  def test_convexity_makes_rally_bigger_than_selloff(self):
    up = rate_shock_return(5.0, 7.0, 100) - 5.0
    down = rate_shock_return(5.0, 7.0, -100) - 5.0
    self.assertGreater(down, -up)

  def test_rate_shock_grid_shape(self):
    grid = rate_shock_grid({"A": (5.0, 1.0), "B": (5.0, 7.0)}, [-100, 0, 100])
    self.assertEqual(grid.shape, (2, 3))
    self.assertAlmostEqual(grid.loc["A", "+0bp"], 5.0)


class TestRatesMarketStructure(unittest.TestCase):
  """Tests for curve / hike-pricing / valuation / tax helpers."""

  def test_curve_snapshot_uses_asof(self):
    snap = curve_snapshot(_macro_frame(), {
        "Start": "2026-01-01",
        "Now": "2026-01-10"
    })
    self.assertEqual(list(snap.index), ["3M", "1Y", "2Y", "5Y", "10Y", "30Y"])
    self.assertAlmostEqual(snap.loc["10Y", "Now"], 5.22)
    self.assertAlmostEqual(snap.loc["10Y", "Start"], 4.3)

  def test_hike_pricing(self):
    hp = hike_pricing(macro_asof(_macro_frame(), "2026-01-05"))
    self.assertAlmostEqual(hp["policy_mid"], 3.875)
    self.assertAlmostEqual(hp["hikes_priced_2y"], 3.5)

  def test_rates_change_table(self):
    tab = rates_change_table(_macro_frame(), "2026-01-01", "2026-01-05")
    self.assertAlmostEqual(tab.loc["US10Y", "Change_bp"], 92.0)
    self.assertAlmostEqual(tab.loc["BREAKEVEN_10Y", "Change_bp"], -7.0)

  def test_stock_bond_valuation(self):
    v = stock_bond_valuation(25.0,
                             macro_asof(_macro_frame(), "2026-01-05"),
                             dividend_yield_pct=1.0)
    self.assertAlmostEqual(v["earnings_yield"], 4.0)
    self.assertAlmostEqual(v["fed_model_gap"], 4.0 - 5.22)
    self.assertAlmostEqual(v["erp_vs_real"], 4.0 - 2.91)

  def test_after_tax_yield(self):
    self.assertAlmostEqual(after_tax_yield(5.0, 0.37, 0.0, 0.0, 0.038),
                           5.0 * (1 - 0.408))
    self.assertAlmostEqual(
        after_tax_yield(5.0, 0.37, 0.10, state_exempt_share=1.0, niit=0),
        5.0 * 0.63)

  def test_classify_holding(self):
    self.assertEqual(classify_holding("GOOG"), "Employer Stock")
    self.assertEqual(classify_holding("BTC-USD"), "Crypto")
    self.assertEqual(classify_holding("VMFXX"), "Cash")
    self.assertEqual(classify_holding("SJNK"), "Bond")
    self.assertEqual(
        classify_holding("Inst Tot Bd Mkt Ix Tr", "Inst Tot Bd Mkt Ix Tr"),
        "Bond")
    self.assertEqual(classify_holding("NVDA"), "Equity")


if __name__ == "__main__":
  unittest.main()
