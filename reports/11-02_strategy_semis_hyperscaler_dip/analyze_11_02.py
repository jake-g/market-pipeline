#!/usr/bin/env python3
# pylint: disable=duplicate-code,too-many-return-statements
"""Public market strategy & model portfolio generator for November 2, 2026.

Semiconductor & Hyperscaler Air-Pocket Edition: evaluates an anonymized,
proportion-only institutional Two-Book Model Portfolio (80.0% Core Ballast /
20.0% Tactical Sleeve) against the Monday, November 2, 2026 close, where SOXX
(-3.79% 1D, -22.97% 1M, RSI 29.5, -4.81% vs 200DMA) and GOOG (-11.51% 1W,
-30.24% 52W DD, RSI 12.7, -17.77% vs 200DMA) test capitulation thresholds
ahead of Tuesday's U.S. Midterm Elections and AMD / ANET / AAPL earnings.

Strictly public-facing and percentage/basis-point based: contains zero personal
dollar values, share counts, or private account identifiers.
"""

import datetime
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

from graphviz import Digraph
import matplotlib

matplotlib.use("Agg")
# pylint: disable=wrong-import-position
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tabulate import tabulate

if "/opt/homebrew/bin" not in os.environ.get("PATH", ""):
  os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
REPORTS_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
for _p in (PROJECT_ROOT, REPORTS_DIR):
  if _p not in sys.path:
    sys.path.insert(0, _p)

# pylint: disable=wrong-import-position
from reports.report_utils import calculate_technical_metrics
from reports.report_utils import clean_md
from reports.report_utils import format_recent_news_markdown
from reports.report_utils import get_upcoming_earnings
from reports.report_utils import plot_correlation_heatmap
from reports.report_utils import render_markdown_to_pdf
from reports.report_utils import setup_decision_tree_aesthetics
from reports.report_utils import setup_plot_aesthetics

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REPORT_DATE = datetime.date(2026, 11, 2)
TAG = "11_02"
PREV_REPORT_TAG = "10-12 / 11-01"
PREV_SNAPSHOT_DATE = "2026-10-12"
PREV_GATE_ON = True

EVENTS = {
    "aapl_print": datetime.date(2026, 11, 2),
    "midterms": datetime.date(2026, 11, 3),
    "amd_anet_print": datetime.date(2026, 11, 3),
    "jobs": datetime.date(2026, 11, 6),
    "cpi_oct": datetime.date(2026, 11, 10),
    "nvda_print": datetime.date(2026, 11, 17),
    "fomc_dec": datetime.date(2026, 12, 9),
    "q1_backstop": datetime.date(2027, 1, 29),
}

FRESH_TRANCHES = [
    ("T1", "Capitulation Starter", 20.0),
    ("T2", "Post-Midterm / Print Clearance", 20.0),
    ("T3", "CPI + NVDA Print Window", 25.0),
    ("T4", "FOMC + Anthropic Pricing", 20.0),
    ("T5", "Q1 Reserve / Backstop", 15.0),
]

CORE_LEG_PCT = 50.0
TACTICAL_LEADERS = [
    "TSM",
    "SMH",
    "NVDA",
    "MSFT",
    "AMZN",
    "ANET",
    "AMD",
    "AVGO",
    "MRVL",
    "GOOG",
]
CORE_VALUE = ["VTV", "SCHD", "VIG"]
CORE_BROAD = ["VTI", "VTSAX", "SCHB"]
CORE_GROWTH = ["VUG", "VGT", "VIGAX"]

MARKET_DATA_DIR = os.path.join(PROJECT_ROOT, "market_data")
TICKERS_DIR = os.path.join(MARKET_DATA_DIR, "tickers")
PLOTS_DIR = os.path.join(SCRIPT_DIR, "plots")
CRITIQUE_PATH = os.path.join(SCRIPT_DIR, "notebooklm_critique.md")

CASH_LIKE = {"VMFXX", "VUSB"}
BENCHMARKS = ["SPY", "QQQ", "SOXX"]
YTD_START = pd.Timestamp("2026-01-01")

# Representative Institutional Model Portfolio (100.00% Total Weight).
# Strictly proportion-based: (Ticker, Theme, Wrapper, Weight_Pct, Cost_Date).
# Cost_Date is a standardized institutional vintage baseline date used to
# compute public model return-on-cost (%) from historical prices.tsv data.
MODEL_SPEC: List[Tuple[str, str, str, float, str]] = [
    # --- Core Ballast: Broad Index & Style Anchors (73.40%) ---
    ("VTI", "Broad Index / Core", "Taxable Core Sleeve", 24.50, "2023-10-02"),
    ("VUG", "Broad Index / Core", "Tax-Deferred Retirement", 15.20,
     "2023-10-02"),
    ("VTV", "Broad Index / Core", "Taxable Core Sleeve", 11.40, "2024-01-02"),
    ("VGT", "Broad Index / Core", "Tax-Deferred Retirement", 7.80,
     "2024-01-02"),
    ("VEA", "Broad Index / Core", "Taxable Core Sleeve", 4.80, "2024-06-03"),
    ("SCHD", "Broad Index / Core", "Triple-Tax-Free HSA", 4.20, "2024-06-03"),
    ("VIG", "Broad Index / Core", "Taxable Core Sleeve", 3.50, "2024-06-03"),
    ("SCHB", "Broad Index / Core", "Triple-Tax-Free HSA", 2.00, "2024-06-03"),
    # --- Core Ballast: Liquid Cash Reserves (6.60%) ---
    ("VMFXX", "Cash & Short Duration", "Taxable Core Sleeve", 5.10, "2026-01-02"
    ),
    ("VUSB", "Cash & Short Duration", "Taxable Core Sleeve", 1.50,
     "2026-01-02"),
    # --- Tactical Sleeve: Semis & AI Hardware (8.90%) ---
    ("SMH", "Semis & AI Hardware", "Tax-Free Roth Sleeve", 1.85, "2025-05-01"),
    ("SOXX", "Semis & AI Hardware", "Tax-Deferred Retirement", 1.25,
     "2025-05-01"),
    ("TSM", "Semis & AI Hardware", "Tax-Free Roth Sleeve", 1.15, "2025-05-01"),
    ("NVDA", "Semis & AI Hardware", "Tax-Free Roth Sleeve", 1.05, "2025-05-01"),
    ("AVGO", "Semis & AI Hardware", "Tax-Free Roth Sleeve", 0.70, "2025-09-02"),
    ("AMD", "Semis & AI Hardware", "Tax-Free Roth Sleeve", 0.65, "2025-05-01"),
    ("ANET", "Semis & AI Hardware", "Tax-Free Roth Sleeve", 0.55, "2025-06-02"),
    ("ASML", "Semis & AI Hardware", "Taxable Core Sleeve", 0.45, "2025-06-02"),
    ("MRVL", "Semis & AI Hardware", "Tax-Free Roth Sleeve", 0.35, "2025-06-02"),
    ("XSD", "Semis & AI Hardware", "Taxable Core Sleeve", 0.25, "2026-07-01"),
    ("WDC", "Semis & AI Hardware", "Taxable Core Sleeve", 0.25, "2026-07-15"),
    ("COHR", "Semis & AI Hardware", "Taxable Core Sleeve", 0.20, "2026-07-15"),
    ("DRAM", "Semis & AI Hardware", "Taxable Core Sleeve", 0.20, "2026-07-15"),
    # --- Tactical Sleeve: Megacap / Hyperscaler Platforms (4.60%) ---
    ("MSFT", "Megacap / Platforms", "Tax-Deferred Retirement", 0.90,
     "2025-04-01"),
    ("AAPL", "Megacap / Platforms", "Taxable Core Sleeve", 0.85, "2025-04-01"),
    ("AMZN", "Megacap / Platforms", "Tax-Free Roth Sleeve", 0.75, "2025-06-02"),
    ("GOOG", "Megacap / Platforms", "Taxable Core Sleeve", 0.65, "2026-06-01"),
    ("META", "Megacap / Platforms", "Tax-Free Roth Sleeve", 0.45, "2026-06-01"),
    ("CIBR", "Megacap / Platforms", "Tax-Free Roth Sleeve", 0.60, "2025-05-01"),
    ("PANW", "Megacap / Platforms", "Tax-Free Roth Sleeve", 0.40, "2025-05-01"),
    # --- Tactical Sleeve: Power / Nuclear / Materials (2.60%) ---
    ("VPU", "Power / Nuclear / Materials", "Taxable Core Sleeve", 0.70,
     "2025-06-02"),
    ("NVT", "Power / Nuclear / Materials", "Tax-Free Roth Sleeve", 0.50,
     "2025-09-02"),
    ("NLR", "Power / Nuclear / Materials", "Taxable Core Sleeve", 0.40,
     "2026-05-01"),
    ("CCJ", "Power / Nuclear / Materials", "Taxable Core Sleeve", 0.35,
     "2026-05-01"),
    ("CEG", "Power / Nuclear / Materials", "Tax-Free Roth Sleeve", 0.35,
     "2026-05-01"),
    ("VST", "Power / Nuclear / Materials", "Tax-Free Roth Sleeve", 0.30,
     "2026-05-01"),
    # --- Tactical Sleeve: Space / Defense / AI IPO Proxies (1.60%) ---
    ("SPCX", "Space / Defense / Misc", "Tax-Free Roth Sleeve", 0.60,
     "2025-08-01"),
    ("AIPO", "Space / Defense / Misc", "Taxable Core Sleeve", 0.40,
     "2026-06-15"),
    ("RKLB", "Space / Defense / Misc", "Taxable Core Sleeve", 0.35,
     "2026-06-15"),
    ("NASA", "Space / Defense / Misc", "Taxable Core Sleeve", 0.25,
     "2026-06-15"),
    # --- Tactical Sleeve: Crypto & Digital Infrastructure (1.10%) ---
    ("IBIT", "Crypto", "Tax-Free Roth Sleeve", 0.65, "2025-06-02"),
    ("BMNR", "Crypto", "Taxable Core Sleeve", 0.25, "2026-06-15"),
    ("IREN", "Crypto", "Taxable Core Sleeve", 0.20, "2026-07-01"),
    # --- Tactical Sleeve: Healthcare & Biotech (1.20%) ---
    ("VHT", "Health", "Triple-Tax-Free HSA", 0.55, "2025-05-01"),
    ("MRK", "Health", "Taxable Core Sleeve", 0.40, "2025-05-01"),
    ("OZEM", "Health", "Triple-Tax-Free HSA", 0.25, "2026-05-01"),
]

THEMES: Dict[str, List[str]] = {}
for _t, _th, _wr, _wt, _cd in MODEL_SPEC:
  THEMES.setdefault(_th, []).append(_t)

THEME_COLORS = {
    "Semis & AI Hardware": "#1f77b4",
    "Megacap / Platforms": "#ff7f0e",
    "Power / Nuclear / Materials": "#2ca02c",
    "Space / Defense / Misc": "#9467bd",
    "Crypto": "#e377c2",
    "Health": "#17becf",
    "Broad Index / Core": "#7f7f7f",
    "Cash & Short Duration": "#bcbd22",
    "Other": "#8c564b",
}

CORE_THEMES = {"Broad Index / Core", "Cash & Short Duration"}
NEWS_JUNK = re.compile(
    r"(\b(put|call)\b.*\(\w+\d{6}[CP]\d+\)|interactive stock chart|"
    r"stock price, news, quote|shares (bought|sold) by|\$\w+ shares|"
    r"maumelle|pizza joints|eagle nuclear|wvu statler|nlr coach|"
    r"\bwin a\b|radeon driver|trims holdings|llc (buys|sells|trims)|"
    r"stocks to follow now|traders work, as screens|north korean target|"
    r"gaming hangs|motherboard|crypto spending limits)",
    re.IGNORECASE,
)

AI_IPO_KEYWORDS = [
    "anthropic",
    "openai",
    "cerebras",
    "databricks",
    "lambda",
    "deepseek",
    "sk hynix",
    "xai",
    "mistral",
    "groq",
    "coreweave",
    "crusoe",
    "nscale",
    "spacex",
    "stripe",
    "scale ai",
    "perplexity",
    "figure ai",
    "waymo",
    "ai ipo",
    "pre-ipo ai",
]

BELLWETHER_WATCH = [
    ("QCOM", "Edge AI & Handset Silicon (SOXX / SMH)"),
    ("ARM", "CPU Architecture & Datacenter Licensing (SMH)"),
    ("VRT", "Liquid Cooling & Thermal (AI Infra)"),
    ("GEV", "Gas Turbines & Grid Electrification"),
    ("KLAC", "Process Control & Wafer Inspection"),
    ("LRCX", "Etch & Advanced Packaging (SMH)"),
    ("PWR", "High-Voltage Grid EPC (Power Pillar)"),
    ("ETN", "Electrical Switchgear & Transformers"),
    ("PLTR", "Enterprise AI Foundry & Defense Software"),
    ("CRWV", "GPU Neocloud Capacity & Debt Financing Read"),
]

_PRICE_CACHE: Dict[str, Optional[pd.DataFrame]] = {}


def load_prices(ticker: str) -> Optional[pd.DataFrame]:
  """Loads and cleans a ticker's prices.tsv up to REPORT_DATE."""
  if ticker in _PRICE_CACHE:
    return _PRICE_CACHE[ticker]
  path = os.path.join(TICKERS_DIR, ticker, "prices.tsv")
  if not os.path.exists(path):
    _PRICE_CACHE[ticker] = None
    return None
  df = pd.read_csv(path, sep="\t")
  df["Date"] = pd.to_datetime(df["Date"], utc=True).dt.tz_localize(None)
  df = df.dropna(subset=["Close"]).sort_values("Date").reset_index(drop=True)
  df = df[df["Date"] <= pd.Timestamp(REPORT_DATE)]
  _PRICE_CACHE[ticker] = df
  return df


def load_fundamentals(ticker: str) -> Dict[str, Any]:
  """Reads a ticker's fundamentals.tsv into a dict of useful metrics."""
  path = os.path.join(TICKERS_DIR, ticker, "fundamentals.tsv")
  if not os.path.exists(path):
    return {}
  df = pd.read_csv(path, sep="\t", names=["Metric", "Value"], header=0)
  kv = dict(zip(df["Metric"], df["Value"]))

  def _f(key: str) -> float:
    try:
      return float(kv.get(key, np.nan))
    except (TypeError, ValueError):
      return np.nan

  return {
      "Name": str(kv.get("shortName", ticker))[:26],
      "Quote_Type": str(kv.get("quoteType", "")),
      "Forward_PE": _f("forwardPE"),
      "Trailing_PE": _f("trailingPE"),
      "PS_Ratio": _f("priceToSalesTrailing12Months"),
      "Revenue_Growth": _f("revenueGrowth"),
      "Beta": _f("beta"),
      "Target_Mean": _f("targetMeanPrice"),
      "Rec": str(kv.get("recommendationKey", "")).replace("_", " "),
      "High_52W": _f("fiftyTwoWeekHigh"),
      "Discount_to_IV_Pct": _f("discount_to_intrinsic_value"),
  }


def build_model_portfolio() -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
  """Constructs the anonymized, proportion-only institutional model portfolio.

  Uses public `prices.tsv` close prices and standardized vintage entry dates so
  all return-on-cost (%) and contribution (bps) metrics are 100% reproducible
  without any private brokerage files or dollar balances.

  Returns:
    Tuple of (aggregated holdings DataFrame, wrapper_dict).
  """
  rows: List[Dict[str, Any]] = []
  for ticker, theme, wrapper, wt_pct, cost_date in MODEL_SPEC:
    px = load_prices(ticker)
    if ticker in CASH_LIKE or px is None or px.empty:
      last_px = 1.0
      prev_px = 1.0
      cost_px = 1.0 / 1.036  # ~3.6% YTD money-market yield
    else:
      last_px = float(px["Close"].iloc[-1])
      prev_px = float(px["Close"].iloc[-2]) if len(px) >= 2 else last_px
      sub = px[px["Date"] >= pd.Timestamp(cost_date)]
      cost_px = float(sub["Close"].iloc[0]) if not sub.empty else last_px

    ret_on_cost_pct = (last_px / cost_px - 1.0) * 100.0 if cost_px > 0 else 0.0
    day_chg_pct = (last_px / prev_px - 1.0) * 100.0 if prev_px > 0 else 0.0
    # Normalized 100-unit index value (strictly proportion units, not dollars)
    norm_val = wt_pct
    norm_cost = wt_pct / (1.0 + ret_on_cost_pct / 100.0)
    norm_pnl = norm_val - norm_cost
    norm_day = norm_val - (norm_val / (1.0 + day_chg_pct / 100.0))

    rows.append({
        "Ticker": ticker,
        "Theme": theme,
        "Account": wrapper,
        "Accounts": wrapper,
        "Price": last_px,
        "Weight_Pct": wt_pct,
        "Current_Value": norm_val,
        "Cost_Basis": norm_cost,
        "Unrealized_PnL_Net": norm_pnl,
        "Day_Change_Net": norm_day,
        "Unrealized_PnL_Pct": ret_on_cost_pct,
        "Day_Change_Pct": day_chg_pct,
        "Vintage_Date": cost_date,
    })

  df = pd.DataFrame(rows)
  df["Weight_Pct"] = df["Current_Value"] / df["Current_Value"].sum() * 100.0
  total_cost = float(df["Cost_Basis"].sum())
  df["Return_Contrib_Pct"] = np.where(
      total_cost > 0, df["Unrealized_PnL_Net"] / total_cost * 100.0, 0.0)
  df = df.sort_values("Weight_Pct", ascending=False).reset_index(drop=True)

  wrappers: Dict[str, pd.DataFrame] = {}
  for w_name, grp in df.groupby("Account", sort=False):
    wrappers[str(w_name)] = grp.copy()
  return df, wrappers


def period_return(px: pd.DataFrame, start: pd.Timestamp) -> float:
  """Close-to-close return (%) from the first bar on/after start."""
  sub = px[px["Date"] >= start]
  if sub.empty or len(sub) < 2:
    return np.nan
  return float((sub["Close"].iloc[-1] / sub["Close"].iloc[0] - 1) * 100)


def trailing_return(px: pd.DataFrame, days: int) -> float:
  """Return (%) over the trailing calendar window."""
  start = px["Date"].iloc[-1] - pd.Timedelta(days=days)
  return period_return(px, start)


def rolling_beta(px: pd.DataFrame, bench: pd.DataFrame, window: int) -> float:
  """Latest rolling OLS beta of daily returns vs a benchmark."""
  m = px[["Date", "Close"]].merge(bench[["Date", "Close"]],
                                  on="Date",
                                  suffixes=("", "_b"))
  if len(m) < window + 2:
    return np.nan
  r = m["Close"].pct_change().tail(window)
  rb = m["Close_b"].pct_change().tail(window)
  var = rb.var()
  return float(r.cov(rb) / var) if var and var > 0 else np.nan


def enrich(agg: pd.DataFrame) -> pd.DataFrame:
  """Adds technicals, fundamentals, and benchmark-relative returns."""
  bench_px = {b: load_prices(b) for b in BENCHMARKS}
  bench_ret = {}
  for b, px in bench_px.items():
    if px is None:
      raise ValueError(f"Benchmark {b} prices missing")
    bench_ret[b] = {
        "1D": float((px["Close"].iloc[-1] / px["Close"].iloc[-2] - 1) * 100),
        "1M": trailing_return(px, 30),
        "3M": trailing_return(px, 91),
        "YTD": period_return(px, YTD_START),
        "1Y": trailing_return(px, 365),
    }

  ETF_OVERRIDES = {
      "SMH",
      "SOXX",
      "XSD",
      "DRAM",
      "CIBR",
      "VPU",
      "NLR",
      "SPCX",
      "AIPO",
      "NASA",
      "IBIT",
      "VHT",
      "OZEM",
      "VTI",
      "VUG",
      "VTV",
      "VGT",
      "VEA",
      "SCHD",
      "VIG",
      "SCHB",
      "VMFXX",
      "VUSB",
  }

  rows = []
  for _, r in agg.iterrows():
    t = str(r["Ticker"])
    row: Dict[str, Any] = {str(k): v for k, v in r.to_dict().items()}
    row.update(load_fundamentals(t))
    if t in ETF_OVERRIDES and row.get("Quote_Type") != "ETF":
      row["Quote_Type"] = "ETF"
    elif t not in ETF_OVERRIDES and not row.get("Quote_Type"):
      row["Quote_Type"] = "EQUITY"
    px = load_prices(t)
    if px is not None and not px.empty and t not in CASH_LIKE:
      tech = calculate_technical_metrics(px)
      row.update(tech)
      row["Ret_1D"] = float((px["Close"].iloc[-1] / px["Close"].iloc[-2] - 1) *
                            100 if len(px) >= 2 else 0.0)
      row["Ret_1W"] = trailing_return(px, 7)
      row["Ret_1M"] = trailing_return(px, 30)
      row["Ret_3M"] = trailing_return(px, 91)
      row["Ret_YTD"] = period_return(px, YTD_START)
      row["Ret_1Y"] = trailing_return(px, 365)
      hi = px["Close"].tail(252).max()
      row["Drawdown_52W"] = float((px["Close"].iloc[-1] / hi - 1) * 100)
      row["Last_Close"] = float(px["Close"].iloc[-1])
      for b in BENCHMARKS:
        row[f"RS_3M_vs_{b}"] = row["Ret_3M"] - bench_ret[b]["3M"]
        row[f"RS_YTD_vs_{b}"] = row["Ret_YTD"] - bench_ret[b]["YTD"]
      qqq_px = bench_px["QQQ"]
      if qqq_px is not None:
        row["Beta_60D_QQQ"] = rolling_beta(px, qqq_px, 60)
    row["Upcoming_Earnings"] = get_upcoming_earnings(t, TICKERS_DIR)
    rows.append(row)
  df = pd.DataFrame(rows)
  df.attrs["bench_ret"] = bench_ret
  return df


def frozen_weight_curve(df: pd.DataFrame) -> pd.DataFrame:
  """Builds constant-weight model equity curves vs benchmarks YTD."""

  def _leg(sub: pd.DataFrame) -> pd.Series:
    weights = sub.set_index("Ticker")["Weight_Pct"]
    weights = weights / weights.sum()
    frames = []
    for t, w in weights.items():
      px = load_prices(str(t))
      if t in CASH_LIKE or px is None or px.empty:
        continue
      s = px[px["Date"] >= YTD_START].set_index("Date")["Close"]
      frames.append((s / s.iloc[0]).rename(t) * w)
    mat = pd.concat(frames, axis=1).ffill().bfill()
    cash_w = 1 - weights[list(mat.columns)].sum()
    days = (mat.index - mat.index[0]).days.values
    return mat.sum(axis=1) + cash_w * (1 + 0.04 * days / 365)

  curve = pd.DataFrame({"Portfolio": _leg(df)})
  tactical = df[~df["Theme"].isin(CORE_THEMES)]
  if not tactical.empty:
    curve["Tactical"] = _leg(tactical).reindex(curve.index).ffill()
  for b in BENCHMARKS:
    bpx = load_prices(b)
    if bpx is None:
      continue
    s = bpx[bpx["Date"] >= YTD_START].set_index("Date")["Close"]
    curve[b] = (s / s.iloc[0]).reindex(curve.index).ffill()
  return (curve - 1) * 100


def portfolio_rolling_beta(df: pd.DataFrame, window: int = 60) -> pd.Series:
  """Rolling beta of the constant-weight model portfolio vs QQQ."""
  weights = df.set_index("Ticker")["Weight_Pct"] / 100
  rets = []
  for t, w in weights.items():
    t = str(t)
    px = load_prices(t)
    if t in CASH_LIKE or px is None or px.empty:
      continue
    s = px.set_index("Date")["Close"].pct_change().rename(t) * w
    rets.append(s)
  port = pd.concat(rets, axis=1).fillna(0).sum(axis=1)
  qqq_px = load_prices("QQQ")
  if qqq_px is None:
    raise ValueError("QQQ prices missing")
  qqq = qqq_px.set_index("Date")["Close"].pct_change()
  m = pd.concat([port.rename("p"), qqq.rename("q")], axis=1).dropna()
  m = m[m.index >= pd.Timestamp("2025-06-01")]
  cov = m["p"].rolling(window).cov(m["q"])
  var = m["q"].rolling(window).var()
  return (cov / var).dropna()


def _save(fig_path: str) -> None:
  plt.tight_layout()
  plt.savefig(fig_path, dpi=220, bbox_inches="tight")
  plt.close()
  logger.info("Saved %s", os.path.basename(fig_path))


def plot_equity_curve(curve: pd.DataFrame, path: str) -> None:
  """Model portfolio and tactical sleeve vs SPY/QQQ/SOXX YTD."""
  setup_plot_aesthetics()
  _, ax = plt.subplots(figsize=(12, 6))
  styles = {
      "Portfolio": ("#d62728", 2.6, "-"),
      "Tactical": ("#9467bd", 2.2, "--"),
      "SPY": ("#7f7f7f", 1.6, "-"),
      "QQQ": ("#1f77b4", 1.6, "-"),
      "SOXX": ("#2ca02c", 1.4, "-"),
  }
  names = {
      "Portfolio": "Model Portfolio (80% Core Ballast / 20% Tactical)",
      "Tactical": "Tactical Sleeve (Equities & Thematic ETFs)",
  }
  for col in curve.columns:
    c, lw, ls = styles.get(col, ("#000", 1, "-"))
    ax.plot(
        curve.index,
        curve[col],
        label=f"{names.get(col, col)} ({curve[col].iloc[-1]:+.1f}%)",
        color=c,
        linewidth=lw,
        linestyle=ls,
    )
  ax.axhline(0, color="black", linewidth=0.8)
  ax.set_title(
      "YTD 2026: Model Portfolio & Tactical Sleeve vs. Benchmarks "
      "(Thru Nov 2, 2026 Close)",
      fontweight="bold",
  )
  ax.set_ylabel("Cumulative Return (%)")
  ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
  ax.legend(loc="upper left")
  _save(path)


def plot_relative_strength(df: pd.DataFrame, path: str) -> None:
  """3M return minus SPY per holding, colored by theme."""
  setup_plot_aesthetics()
  d = df.dropna(subset=["RS_3M_vs_SPY"]).sort_values("RS_3M_vs_SPY")
  _, ax = plt.subplots(figsize=(11, max(6, 0.28 * len(d))))
  colors = [THEME_COLORS.get(t, "#8c564b") for t in d["Theme"]]
  ax.barh(d["Ticker"], d["RS_3M_vs_SPY"], color=colors)
  ax.axvline(0, color="black", linewidth=0.8)
  ax.set_xlabel("3-Month Return Minus SPY (Percentage Points)")
  ax.set_title(
      "Relative Strength vs. SPY (Trailing 3 Months — Thru Nov 2, 2026)",
      fontweight="bold",
  )
  handles = [
      plt.Rectangle((0, 0), 1, 1, color=c)
      for t, c in THEME_COLORS.items()
      if t in set(d["Theme"])
  ]
  labels = [t for t in THEME_COLORS if t in set(d["Theme"])]
  ax.legend(handles, labels, fontsize=8, loc="lower right")
  _save(path)


def plot_pnl_contribution(df: pd.DataFrame, path: str) -> None:
  """Weighted model return contribution per holding (percentage-only)."""
  setup_plot_aesthetics()
  d = df[~df["Ticker"].isin(CASH_LIKE)].sort_values("Return_Contrib_Pct")
  d = pd.concat([d.head(12), d.tail(12)]).drop_duplicates("Ticker")
  _, ax = plt.subplots(figsize=(11, 7))
  colors = np.where(d["Return_Contrib_Pct"] >= 0, "#2ca02c", "#d62728")
  ax.barh(d["Ticker"], d["Return_Contrib_Pct"], color=colors)
  for y, (contrib, pnl_pct) in enumerate(
      zip(d["Return_Contrib_Pct"], d["Unrealized_PnL_Pct"])):
    ax.text(
        contrib,
        y,
        f"  {contrib:+.2f} pts ({pnl_pct:+.0f}% vintage ret)",
        va="center",
        fontsize=8,
    )
  ax.axvline(0, color="black", linewidth=0.8)
  ax.set_xlabel("Contribution to Model Portfolio Return (Percentage Points)")
  ax.set_title(
      "Model Portfolio Return Attribution — Top Contributors & Drags (% Only)",
      fontweight="bold",
  )
  _save(path)


def plot_drawdown_bubble(df: pd.DataFrame, path: str) -> None:
  """Drawdown from 52-week high vs RSI; bubble = model weight %."""
  setup_plot_aesthetics()
  d = df.dropna(subset=["Drawdown_52W", "RSI"])
  d = d[~d["Ticker"].isin(CASH_LIKE)]
  _, ax = plt.subplots(figsize=(12, 7))
  for theme, g in d.groupby("Theme"):
    ax.scatter(
        g["RSI"],
        g["Drawdown_52W"],
        s=np.clip(g["Weight_Pct"] * 120, 35, 2400),
        alpha=0.6,
        color=THEME_COLORS.get(str(theme), "#8c564b"),
        label=str(theme),
        edgecolor="k",
        linewidth=0.5,
    )
  for _, r in d.iterrows():
    ax.annotate(
        r["Ticker"],
        (r["RSI"], r["Drawdown_52W"]),
        fontsize=8,
        xytext=(4, 4),
        textcoords="offset points",
    )
  ax.axvspan(0, 30, color="green", alpha=0.05)
  ax.axvspan(70, 100, color="red", alpha=0.05)
  ax.axhline(-20, color="red", linestyle="--", linewidth=0.8)
  ax.set_xlabel("RSI (14-Day)")
  ax.set_ylabel("Drawdown from 52-Week High (%)")
  ax.set_title(
      "Technical Extension & Drawdown Map (Bubble Size = Model Weight %)",
      fontweight="bold",
  )
  ax.legend(fontsize=8, loc="lower right")
  _save(path)


def plot_theme_exposure(df: pd.DataFrame, path: str) -> None:
  """Theme weights with percentage model return overlay."""
  setup_plot_aesthetics()
  g = df.groupby("Theme").agg(
      Value=("Current_Value", "sum"),
      Cost=("Cost_Basis", "sum"),
      PnL=("Unrealized_PnL_Net", "sum"),
  )
  g["Weight"] = g["Value"] / g["Value"].sum() * 100
  g["PnL_Pct"] = np.where(g["Cost"] > 0, g["PnL"] / g["Cost"] * 100, 0.0)
  g = g.sort_values("Weight", ascending=True)
  _, ax = plt.subplots(figsize=(10.5, 5.5))
  ax.barh(
      g.index,
      g["Weight"],
      color=[THEME_COLORS.get(t, "#8c564b") for t in g.index],
  )
  for y, (w, p_pct) in enumerate(zip(g["Weight"], g["PnL_Pct"])):
    ax.text(
        w + 0.4,
        y,
        f"{w:.1f}% wt  (Vintage {p_pct:+.1f}%)",
        va="center",
        fontsize=9,
    )
  ax.set_xlim(0, g["Weight"].max() * 1.38)
  ax.set_xlabel("Share of Model Portfolio (%)")
  ax.set_title(
      "Model Allocation by Theme (%) & Vintage Return (%)",
      fontweight="bold",
  )
  _save(path)


def plot_earnings_timeline(df: pd.DataFrame, path: str) -> pd.DataFrame:
  """Timeline of upcoming earnings within 75 days; marker = weight %."""
  setup_plot_aesthetics()
  d = df[df["Upcoming_Earnings"].astype(str).str.match(r"\d{4}-\d{2}-\d{2}")]
  d = d.copy()
  d["Earn_Date"] = pd.to_datetime(d["Upcoming_Earnings"])
  horizon = pd.Timestamp(REPORT_DATE) + pd.Timedelta(days=75)
  d = d[(d["Earn_Date"] >= pd.Timestamp(REPORT_DATE)) &
        (d["Earn_Date"] <= horizon)].sort_values("Earn_Date")
  if d.empty:
    return d
  _, ax = plt.subplots(figsize=(12, 5.2))
  y = np.arange(len(d))
  ax.scatter(
      d["Earn_Date"],
      y,
      s=np.clip(d["Weight_Pct"] * 650, 45, 1400),
      c=[THEME_COLORS.get(t, "#8c564b") for t in d["Theme"]],
      alpha=0.75,
      edgecolor="k",
  )
  for yi, (_, r) in zip(y, d.iterrows()):
    ax.text(
        r["Earn_Date"],
        float(yi),
        f"  {r['Ticker']} ({r['Weight_Pct']:.2f}% wt)",
        va="center",
        fontsize=8,
    )
  ax.set_yticks([])
  ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
  ax.set_title(
      "Upcoming Earnings Timeline (Next 75 Days — Marker = Model Weight %)",
      fontweight="bold",
  )
  ax.grid(axis="x", alpha=0.3)
  _save(path)
  return d


def plot_rolling_beta(beta: pd.Series, path: str) -> None:
  """Rolling 60-day beta of the model portfolio vs QQQ."""
  setup_plot_aesthetics()
  _, ax = plt.subplots(figsize=(11, 4.5))
  ax.plot(beta.index, beta.values, color="#d62728", linewidth=2)
  ax.axhline(1.0, color="black", linestyle="--", linewidth=0.8)
  ax.fill_between(
      beta.index,
      beta.values,
      1.0,
      where=np.asarray(beta.values, dtype=float) > 1,
      color="red",
      alpha=0.1,
  )
  ax.set_title(
      f"Rolling 60D Model Portfolio Beta vs. QQQ (Latest: {beta.iloc[-1]:.2f})",
      fontweight="bold",
  )
  ax.set_ylabel("Beta vs. QQQ")
  _save(path)


GREEN, AMBER, RED, DIM = "#90BE6D", "#F4A261", "#F94144", "#E9ECEF"


def _row_of(df: pd.DataFrame, ticker: str) -> Dict[str, Any]:
  """Returns one holding as a dict (empty dict if not held)."""
  r = df[df["Ticker"] == ticker]
  return {} if r.empty else {str(k): v for k, v in r.iloc[0].to_dict().items()}


def build_pillars(df: pd.DataFrame, macro: Dict[str, Any],
                  ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
  """Evaluates the five tactical pillars against Nov 2, 2026 live data."""
  add_pct = ctx["add_pct"]
  soxx, smh, ibit = (
      _row_of(df, "SOXX"),
      _row_of(df, "SMH"),
      _row_of(df, "IBIT"),
  )
  nlr, ccj, nvt = _row_of(df, "NLR"), _row_of(df, "CCJ"), _row_of(df, "NVT")
  aipo, spcx = _row_of(df, "AIPO"), _row_of(df, "SPCX")
  tsm, nvda, bmnr, iren = (
      _row_of(df, "TSM"),
      _row_of(df, "NVDA"),
      _row_of(df, "BMNR"),
      _row_of(df, "IREN"),
  )
  mrvl = _row_of(df, "MRVL")
  us10y = macro.get("US10Y", {}).get("value", np.nan)
  semi_pct = df[df["Theme"] == "Semis & AI Hardware"]["Weight_Pct"].sum()
  power_pct = df[df["Theme"] ==
                 "Power / Nuclear / Materials"]["Weight_Pct"].sum()
  spec_pct = sum(
      _row_of(df, t).get("Weight_Pct", 0.0)
      for t in ("IBIT", "BMNR", "IREN", "RKLB", "NASA"))

  # --- Pillar 1: Semis / Memory & Hyperscaler Hardware ---
  s_rsi = soxx.get("RSI", np.nan)
  s_d50 = soxx.get("Dist_to_50MA", np.nan)
  s_d200 = soxx.get("Dist_to_200MA", np.nan)
  smh_d200 = smh.get("Dist_to_200MA", np.nan)
  p1_yes = bool(s_d50 > 0 and s_rsi < 65)
  wk_broken = _weekly_close_below_pct("SOXX", 200, -3.0)
  capitulation = bool(not p1_yes and s_rsi <= 35 and not wk_broken)
  if p1_yes:
    sub1 = "1A: Add on dips" if s_rsi < 45 else "1A: Hold, trail 12%"
  elif capitulation:
    sub1 = "1B-iii: Capitulation Watch (Fri SOXX $462.20 stop)"
  else:
    sub1 = "1B: Trim 20% SOXX/SMH"
  p1 = {
      "id": "P1",
      "title": "P1: Semis & AI\nHardware",
      "name": "Semis / AI hardware",
      "question": (f"SOXX > 50DMA & RSI < 65?\n"
                   f"(SOXX {s_d50:+.1f}% 50MA, {s_d200:+.1f}% 200MA\n"
                   f"RSI {s_rsi:.0f} · SMH {smh_d200:+.1f}% 200MA)"),
      "trigger": "SOXX > 50DMA & RSI < 65 (watch: Fri > -3% vs 200MA)",
      "reading": (f"SOXX {s_d200:+.1f}% 200MA (RSI {s_rsi:.0f}); "
                  f"SMH {smh_d200:+.1f}%, NVDA "
                  f"{nvda.get('Dist_to_200MA', np.nan):+.1f}%, TSM "
                  f"{tsm.get('Dist_to_200MA', np.nan):+.1f}%"),
      "taken": "yes" if p1_yes else "no",
      "sub": sub1,
      "state": ("YES" if p1_yes else
                ("NO (CAPITULATION WATCH)" if capitulation else "NO")),
      "yes": {
          "label":
              "1A: ADD ON DIPS",
          "color":
              GREEN,
          "bullets": [
              f"RSI<45: +{add_pct:.2f}% book (TSM/SMH/NVDA)",
              f"Cap Semis ≤ 12% book (now {semi_pct:.1f}%)",
          ],
      },
      "no": {
          "label": ("1B: HOLD LEADERS, WATCH FRIDAY CLOSE"
                    if capitulation else "1B: TRIM / DE-RISK"),
          "color":
              AMBER if capitulation else RED,
          "bullets": [
              "SMH (-2.3%), NVDA (-1.0%), TSM (-0.1%) hold 200-day avg",
              f"Skip MRVL ({mrvl.get('Dist_to_200MA', np.nan):+.1f}% vs 200MA); "
              "sell 50% of XSD/WDC/COHR/DRAM",
              "Buy TSM / SMH / NVDA on Thu Nov 5 (after AMD/ANET)",
              "Stop: If Fri SOXX < $462.20 → sell 20% of SOXX/SMH",
          ],
      },
      "invalidation": "Fri SOXX < $462.20 (-3% vs 200MA) → 20% trim.",
  }

  # --- Pillar 2: Rates & Duration ---
  p2_yes = bool(us10y < 4.75)
  sub2 = "2A: Growth DCA ON" if p2_yes else "2B: Value Tilt (VTV/SCHD/VIG)"
  p2 = {
      "id":
          "P2",
      "title":
          "P2: Interest Rates\n(Growth vs. Value)",
      "name":
          "Rates / duration",
      "question":
          f"Is 10Y Yield < 4.75%?\n(Today: {us10y:.2f}% · HY {ctx['hy']:.2f}%)",
      "trigger":
          "10Y < 4.75% & HY Δ3M < +25bp",
      "reading": (f"10Y {us10y:.2f}%; HY {ctx['hy']:.2f}% "
                  f"({ctx['hy_chg']*100:+.0f}bp 3M); WTI "
                  f"${macro.get('WTI_CRUDE', {}).get('value', np.nan):.1f}"),
      "taken":
          "yes" if p2_yes else "no",
      "sub":
          sub2,
      "state":
          "YES" if p2_yes else "NO",
      "yes": {
          "label":
              "2A: BUY GROWTH ETFS",
          "color":
              GREEN,
          "bullets": [
              "Resume buying VUG & VGT index ETFs",
              "Restore full tactical buy sizes",
          ],
      },
      "no": {
          "label":
              "2B: BUY VALUE & DIVIDEND ETFS",
          "color":
              AMBER,
          "bullets": [
              "Put 100% of new index money into VTV / VTI / SCHD / VIG",
              "Hold existing VUG/VGT shares (no tax sale)",
              "Stop: If 10Y > 5.50% → sell 10% of VUG into cash",
          ],
      },
      "invalidation":
          "2 weekly 10Y closes < 4.75% flips to 2A.",
  }

  # --- Pillar 3: Power / Nuclear / Grid ---
  nlr_d = nlr.get("Dist_to_200MA", np.nan)
  ccj_d = ccj.get("Dist_to_200MA", np.nan)
  nvt_d = nvt.get("Dist_to_200MA", np.nan)
  p3_yes = bool(nlr_d > 0 and ccj_d > 0)
  p3 = {
      "id": "P3",
      "title": "P3: Power &\nNuclear Grid",
      "name": "Power / nuclear",
      "question": (f"Are NLR & CCJ > 200-Day Avg?\n"
                   f"(NLR {nlr_d:+.0f}% · CCJ {ccj_d:+.0f}% · VPU +5.5%)"),
      "trigger": "NLR & CCJ > 200DMA",
      "reading": (f"NLR {nlr_d:+.0f}%, CCJ {ccj_d:+.0f}%, NVT {nvt_d:+.0f}% "
                  f"vs 200MA; VPU RSI 67 ({power_pct:.1f}% book)"),
      "taken": "yes" if p3_yes else "no",
      "sub": "3A: Build Nuclear" if p3_yes else "3B: Hold VPU, Cut NLR/CCJ 50%",
      "state": "YES" if p3_yes else "NO",
      "yes": {
          "label":
              "3A: ADD TO NUCLEAR & GRID",
          "color":
              GREEN,
          "bullets": [
              f"Add +{add_pct:.2f}% portfolio to NLR / CCJ / CEG",
              "Re-add NVT once above 200-day avg",
          ],
      },
      "no": {
          "label":
              "3B: HOLD VPU, SELL 50% OF URANIUM",
          "color":
              AMBER,
          "bullets": [
              f"Sell 50% of NLR ({nlr_d:+.0f}% 200MA) & CCJ ({ccj_d:+.0f}%)",
              "Hold VPU utilities ETF; pause NVT / CEG / VST buys",
              "Flip: Resume buying when NLR > 200-day avg",
          ],
      },
      "invalidation": "NLR & CCJ weekly close > 200DMA flips to 3A.",
  }

  # --- Pillar 4: AI IPO Wave ---
  ipo_comb_pct = aipo.get("Weight_Pct", 0.0) + spcx.get("Weight_Pct", 0.0)
  p4 = {
      "id": "P4",
      "title": "P4: AI IPO Wave\n(Anthropic 'ANT')",
      "name": "AI IPO wave",
      "question": "Does Anthropic 'ANT' IPO\nhold its Day-1 price?",
      "trigger": "ANT IPO pricing & Day-1 hold",
      "reading": (f"PENDING (S-1 10/26); AIPO -15% vs 200MA, AVGO -12% "
                  f"($43B backstop); AIPO+SPCX {ipo_comb_pct:.2f}% book"),
      "taken": None,
      "sub": "PENDING: Cut AIPO 50%, buy TSM/NVDA/SMH",
      "state": "PENDING",
      "yes": {
          "label":
              "4A: BUY AI CHIP SUPPLIERS",
          "color":
              GREEN,
          "bullets": [
              "Buy suppliers: TSM / NVDA / ANET / AVGO (>200MA)",
              "Cap IPO ETFs (AIPO + SPCX) ≤ 1.5% of portfolio",
          ],
      },
      "no": {
          "label":
              "4B: SELL IPO ETFS, BUY CHIP DIPS",
          "color":
              RED,
          "bullets": [
              "Sell 50% of AIPO (-15% vs 200-day avg) now",
              "Pause AVGO buys (-12% vs 200MA) until >200MA",
              "Buy SMH / TSM on pre-IPO cash-raising dips",
          ],
      },
      "invalidation": "ANT break below IPO price in 5d locks in 4B.",
  }

  # --- Pillar 5: Crypto & Speculative Sleeve ---
  i_d200, i_rsi = ibit.get("Dist_to_200MA", np.nan), ibit.get("RSI", np.nan)
  above, rsi_ok = bool(i_d200 > 0), bool(i_rsi > 40)
  if above and rsi_ok:
    sub5, state5, taken5 = "5A: Hold Core", "YES", "yes"
  elif above:
    sub5, state5, taken5 = (
        "5A-ii: Hold IBIT, Cut IREN/BMNR",
        "PARTIAL",
        "yes",
    )
  else:
    sub5, state5, taken5 = "5B: Cut Tail Risk", "NO", "no"
  p5 = {
      "id": "P5",
      "title": "P5: Crypto &\nHigh-Beta Stocks",
      "name": "Crypto / spec",
      "question": (f"Is IBIT > 200-Day Avg?\n"
                   f"(IBIT {i_d200:+.1f}% vs 200MA · RSI {i_rsi:.0f})"),
      "trigger": "IBIT > 200DMA & RSI > 40",
      "reading": (f"IBIT {i_d200:+.1f}% 200MA (RSI {i_rsi:.0f}); "
                  f"IREN {iren.get('Dist_to_200MA', np.nan):+.0f}%, BMNR "
                  f"{bmnr.get('Dist_to_200MA', np.nan):+.1f}% 200MA "
                  f"({spec_pct:.2f}% book)"),
      "taken": taken5,
      "sub": sub5,
      "state": state5,
      "yes": {
          "label":
              "5A: HOLD IBIT, SELL MINERS",
          "color":
              AMBER,
          "bullets": [
              f"Hold IBIT ({i_d200:+.1f}% vs 200MA); pause new buys",
              "Sell IREN (-50% vs 200MA) & BMNR (-6.4% vs 200MA)",
              "Stop: If IBIT closes week < 200-day avg → sell 50%",
          ],
      },
      "no": {
          "label":
              "5B: EXIT HIGH-BETA CRYPTO",
          "color":
              RED,
          "bullets": [
              "Sell 100% of BMNR & IREN; sell 50% of IBIT",
              "Move proceeds to VMFXX cash reserve",
          ],
      },
      "invalidation": "IBIT weekly close < 200DMA triggers 5B.",
  }
  return [p1, p2, p3, p4, p5]


def _node_style(taken: Optional[bool], base_color: str) -> Dict[str, str]:
  """Highlights the live branch and dims the dormant branch."""
  if taken is None:
    return {
        "fillcolor": base_color,
        "fontcolor": "black",
        "penwidth": "1.2",
        "color": "#555555",
    }
  if taken:
    return {
        "fillcolor": base_color,
        "fontcolor": "white" if base_color == RED else "black",
        "penwidth": "3.5",
        "color": "#111111",
    }
  return {
      "fillcolor": DIM,
      "fontcolor": "#8A8F98",
      "penwidth": "1",
      "color": "#B0B5BD",
      "style": "filled,rounded,dashed",
  }


def _edge_style(taken: Optional[bool]) -> Dict[str, str]:
  if taken is None:
    return {"color": "#555555"}
  if taken:
    return {"color": "#111111", "penwidth": "3"}
  return {"color": "#B0B5BD", "style": "dashed"}


def create_decision_tree(out_path: str, pillars: List[Dict[str, Any]],
                         ctx: Dict[str, Any]) -> None:
  """Renders a compact, high-readability tactical decision tree."""
  dot = Digraph(comment="11-02 Public Model Strategy Decision Tree")
  setup_decision_tree_aesthetics(dot)
  dot.attr(rankdir="LR", nodesep="0.22", ranksep="0.45", size="16,22")
  dot.attr("node", fontsize="14")
  dot.node(
      "Start",
      f"Tactical Sleeve Rules (Nov 2, 2026)\n"
      f"Tactical: {ctx['tactical_pct']:.1f}% of Portfolio ({ctx['n_tactical']} Holdings)\n"
      f"Cash: {ctx['cash_pct']:.1f}% · Buy Size: {ctx['add_pct']:.2f}% of Portfolio",
      fillcolor="#1D3557",
      fontcolor="white",
      style="filled,rounded,bold",
  )
  gate_on = ctx["risk_off"]
  full_u = ctx["add_pct"] * (2 if gate_on else 1)
  dot.node(
      "Gate",
      f"MACRO CAUTION CHECK\n"
      f"10Y {ctx['us10y']:.2f}% ≥ 4.75% or HY +{ctx['hy_chg']*100:.0f}bp ≥ +25bp?\n"
      f"(Today: 10Y {ctx['us10y']:.2f}%, HY {ctx['hy']:.2f}%)",
      shape="diamond",
      fillcolor="#FFE8D6",
      penwidth="2",
  )
  dot.edge("Start", "Gate")
  dot.node(
      "GateY",
      "CAUTION MODE (HALF-SIZE BUYS)" + (" ◀ TODAY" if gate_on else "") +
      f"\n• Cut buy size in half ({full_u/2:.2f}% of portfolio)\n"
      "• Never buy stocks >3% below 200-day avg\n"
      "• Fund all new buys by selling laggards",
      **_node_style(gate_on, AMBER),
  )
  dot.node(
      "GateN",
      "NORMAL MODE (FULL-SIZE BUYS)" + ("" if gate_on else " ◀ TODAY") +
      f"\n• Full buy size ({full_u:.2f}% of portfolio)\n"
      "• Up to 2 cash clips can be deployed",
      **_node_style(not gate_on, GREEN),
  )
  dot.edge("Gate", "GateY", label=" Yes", **_edge_style(gate_on))
  dot.edge("Gate", "GateN", label=" No", **_edge_style(not gate_on))
  hub = "GateY" if gate_on else "GateN"

  for p in pillars:
    pid = p["id"]
    dot.node(pid, p["title"], fillcolor="#457B9D", fontcolor="white")
    dot.edge(hub, pid)
    dot.node(f"{pid}_c", p["question"], shape="diamond", fillcolor="#FFE8D6")
    dot.edge(pid, f"{pid}_c")
    for key, lab in (("yes", " Yes"), ("no", " No")):
      br = p[key]
      taken = None if p["taken"] is None else (p["taken"] == key)
      head = br["label"] + (" ◀ TODAY" if taken else "")
      body = "\n".join("• " + b for b in br["bullets"])
      dot.node(
          f"{pid}_{key}",
          f"{head}\n{body}",
          **_node_style(taken, br["color"]),
      )
      dot.edge(f"{pid}_c", f"{pid}_{key}", label=lab, **_edge_style(taken))
  dot.render(out_path, format="png", cleanup=True)
  logger.info("Saved decision tree %s.png", out_path)


def build_index_gates(df: pd.DataFrame, macro: Dict[str, Any],
                      ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
  """Three sequential gates governing the 80% core-ballast book."""
  us10y = macro.get("US10Y", {}).get("value", np.nan)
  vti = _row_of(df, "VTI")
  vea = _row_of(df, "VEA")
  core = df[df["Theme"] == "Broad Index / Core"]
  growth_pct = core[core["Ticker"].isin(["VUG", "VGT"])]["Weight_Pct"].sum()
  value_pct = core[core["Ticker"].isin(["VTV", "SCHD",
                                        "VIG"])]["Weight_Pct"].sum()
  gv = growth_pct / value_pct if value_pct else np.nan
  g1 = us10y < 4.75
  g2 = vti.get("Dist_to_200MA", np.nan) > 0
  g3 = ctx["cash_pct"] >= 6.0
  return [
      {
          "id":
              "G1",
          "title":
              "Step 1: Interest Rate Check (Growth vs. Value)",
          "question":
              f"Is 10Y Treasury Yield < 4.75%?\n(Today: {us10y:.2f}%)",
          "reading": (f"10Y {us10y:.2f}%; Growth/Value {gv:.2f}x "
                      f"({growth_pct:.1f}% vs {value_pct:.1f}% book)"),
          "taken":
              bool(g1),
          "yes": (
              "BUY GROWTH & TECH ETFS",
              GREEN,
              [
                  "Split new buys: 50% VTI / 30% VUG / 20% VGT",
                  "Resume buying VUG & VGT on dips",
              ],
          ),
          "no": (
              "BUY VALUE & DIVIDEND ETFS",
              AMBER,
              [
                  "Put 100% of new index money into VTV / VTI / SCHD / VIG",
                  "Pause buying VUG & VGT (keep existing shares)",
                  "If 10Y yield > 5.50%: sell 10% of VUG into cash",
              ],
          ),
      },
      {
          "id":
              "G2",
          "title":
              "Step 2: Market Trend Check (Keep Buying vs. Pause)",
          "question": ("Is VTI Above Its 200-Day Avg?\n"
                       f"(Today: {vti.get('Dist_to_200MA', np.nan):+.1f}%)"),
          "reading": (f"VTI {vti.get('Dist_to_200MA', np.nan):+.1f}% 200MA "
                      f"(RSI {vti.get('RSI', np.nan):.0f}); VEA "
                      f"{vea.get('Dist_to_200MA', np.nan):+.1f}% 200MA"),
          "taken":
              bool(g2),
          "yes": (
              "KEEP REGULAR INDEX BUYING ON",
              GREEN,
              [
                  "Keep automatic index contributions running",
                  "Buy VTI / VTV / SCHD on normal schedule",
              ],
          ),
          "no": (
              "PAUSE AUTO-BUYING, HOLD CASH",
              RED,
              [
                  "Pause automatic index buys; earn ~4% in VMFXX cash",
                  "Cut new index buys to half-size until VTI > 200-day avg",
              ],
          ),
      },
      {
          "id":
              "G3",
          "title":
              "Step 3: Cash Reserve Check (Dry Powder)",
          "question":
              f"Is Cash Reserve ≥ 6.0%?\n(Today: {ctx['cash_pct']:.1f}%)",
          "reading": (f"Cash {ctx['cash_pct']:.1f}% of book "
                      f"(3 clips × {ctx['tranche_pct']:.2f}%)"),
          "taken":
              bool(g3),
          "yes": (
              f"CASH RESERVE HEALTHY ({ctx['cash_pct']:.1f}%)",
              GREEN,
              [
                  f"Keep {ctx['cash_pct']:.1f}% in VMFXX/VUSB earning ~4.0% yield",
                  f"Deploy at most 1/3 of cash ({ctx['tranche_pct']:.1f}% of portfolio) at once",
              ],
          ),
          "no": (
              "REFILL CASH BUFFER TO 6%",
              AMBER,
              [
                  "Trim 25% of overbought winners (RSI > 68) into cash",
                  "Pair gains with tax-loss sales to avoid tax drag",
              ],
          ),
      },
  ]


def create_index_tree(out_path: str, gates: List[Dict[str, Any]],
                      ctx: Dict[str, Any]) -> None:
  """Renders a compact sequential core-ballast tree."""
  dot = Digraph(comment="11-02 Core Ballast Decision Tree")
  setup_decision_tree_aesthetics(dot)
  dot.attr(nodesep="0.25", ranksep="0.4", size="14,18")
  dot.attr("node", fontsize="14")
  core_pct = 100 - ctx["tactical_pct"]
  dot.node(
      "Start",
      f"Core Index & Cash Rules ({core_pct:.1f}% of Portfolio)\n"
      f"Index ETFs ({core_pct - ctx['cash_pct']:.1f}%) + "
      f"Cash Reserve ({ctx['cash_pct']:.1f}%)",
      fillcolor="#1D3557",
      fontcolor="white",
      style="filled,rounded,bold",
  )
  prev = "Start"
  for g in gates:
    gid = g["id"]
    dot.node(gid, g["title"], fillcolor="#457B9D", fontcolor="white")
    dot.edge(prev, gid)
    dot.node(f"{gid}_c", g["question"], shape="diamond", fillcolor="#FFE8D6")
    dot.edge(gid, f"{gid}_c")
    for key, lab in (("yes", " Yes"), ("no", " No")):
      label, color, bullets = g[key]
      taken = g["taken"] == (key == "yes")
      head = label + (" ◀ TODAY" if taken else "")
      body = "\n".join("• " + b for b in bullets)
      dot.node(
          f"{gid}_{key}",
          f"{head}\n{body}",
          **_node_style(taken, color),
      )
      dot.edge(f"{gid}_c", f"{gid}_{key}", label=lab, **_edge_style(taken))
    prev = f"{gid}_{'yes' if g['taken'] else 'no'}"
  dot.render(out_path, format="png", cleanup=True)
  logger.info("Saved index tree %s.png", out_path)


def tech_of(ticker: str) -> Dict[str, Any]:
  """Technicals for any pipeline ticker as of REPORT_DATE."""
  px = load_prices(ticker)
  if px is None or px.empty or len(px) < 200:
    return {}
  t = calculate_technical_metrics(px)
  t["Ret_1D"] = float((px["Close"].iloc[-1] / px["Close"].iloc[-2] - 1) *
                      100 if len(px) >= 2 else 0.0)
  t["Ret_1W"] = trailing_return(px, 7)
  t["Ret_1M"] = trailing_return(px, 30)
  t["Ret_3M"] = trailing_return(px, 91)
  t["Ret_YTD"] = period_return(px, YTD_START)
  t["Last_Close"] = float(px["Close"].iloc[-1])
  t["Drawdown_52W"] = float(
      (px["Close"].iloc[-1] / px["Close"].tail(252).max() - 1) * 100)
  t["MA50"] = float(px["Close"].rolling(50).mean().iloc[-1])
  t["MA200"] = float(px["Close"].rolling(200).mean().iloc[-1])
  return t


def _weekly_close_below(ticker: str, ma_window: int) -> bool:
  """True if the latest Friday close is below the given moving average."""
  return _weekly_close_below_pct(ticker, ma_window, 0.0)


def _weekly_close_below_pct(ticker: str, ma_window: int,
                            threshold_pct: float) -> bool:
  """True if the latest completed Friday close is < threshold_pct vs MA."""
  px = load_prices(ticker)
  if px is None or len(px) < ma_window + 5:
    return False
  last_dt = px["Date"].iloc[-1]
  days_since_fri = (last_dt.weekday() - 4) % 7
  last_friday = last_dt - pd.Timedelta(days=days_since_fri)
  sub = px[px["Date"] <= last_friday]
  if len(sub) < ma_window:
    return False
  ma = sub["Close"].rolling(ma_window).mean().iloc[-1]
  close = sub["Close"].iloc[-1]
  dist_pct = (close / ma - 1.0) * 100.0
  return bool(dist_pct < threshold_pct)


def trigger_scorecard(df: pd.DataFrame, macro: Dict[str, Any],
                      ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
  """Grades rules-engine triggers against Nov 2, 2026 live data."""
  del df
  soxx, smh, vti, ibit = (
      tech_of("SOXX"),
      tech_of("SMH"),
      tech_of("VTI"),
      tech_of("IBIT"),
  )
  nlr, ccj, mrvl = tech_of("NLR"), tech_of("CCJ"), tech_of("MRVL")
  us10y = macro.get("US10Y", {}).get("value", np.nan)
  hy = macro.get("HY_SPREAD", {}).get("value", np.nan)
  wti = macro.get("WTI_CRUDE", {}).get("value", np.nan)
  soxx_wk_50 = _weekly_close_below("SOXX", 50)
  vti_wk_200 = _weekly_close_below("VTI", 200)
  ibit_wk_200 = _weekly_close_below("IBIT", 200)
  return [
      {
          "trigger":
              "Semis Trend: weekly `SOXX < 50DMA`",
          "now": (f"SOXX {soxx.get('Dist_to_200MA', np.nan):+.1f}% 200MA "
                  f"(RSI {soxx.get('RSI', np.nan):.0f}); SMH "
                  f"{smh.get('Dist_to_200MA', np.nan):+.1f}% 200MA"),
          "fired":
              soxx_wk_50,
          "verdict": ("Watch: Hold SMH/SOXX; trim 20% if Fri SOXX < $462.20"
                      if soxx_wk_50 else "Not fired"),
      },
      {
          "trigger": "200DMA Leader Filter (`MRVL` < -3%)",
          "now":
              (f"MRVL -12.7% 1D to {mrvl.get('Dist_to_200MA', np.nan):+.1f}% "
               f"vs 200MA (RSI {mrvl.get('RSI', np.nan):.0f})"),
          "fired": bool(mrvl.get("Dist_to_200MA", 0.0) < -3.0),
          "verdict": "Disqualified from T1 adds today; hold core lot",
      },
      {
          "trigger": "Memory / Optics Breakdown (`<200DMA`)",
          "now": "WDC -19.3%, COHR -32.6%, XSD -7.2% vs 200MA",
          "fired": True,
          "verdict": "Execute 50% tax-loss cuts on WDC / COHR / DRAM / XSD",
      },
      {
          "trigger": "Regime Gate Release (`10Y<4.75%` & `HY<+25bp`)",
          "now": f"10Y {us10y:.2f}%; HY {hy:.2f}% ({ctx['hy_chg']*100:+.0f}bp)",
          "fired": bool(not ctx["risk_off"]),
          "verdict": "Latched ON: ½ units, Value core routing (VTV/SCHD)",
      },
      {
          "trigger": "Stagflation Shock (`10Y>5.50%` or `WTI>$105`)",
          "now": f"10Y {us10y:.2f}%; WTI ${wti:.2f}",
          "fired": bool(us10y > 5.5 or wti > 105),
          "verdict": "$1.63 below $105 WTI trigger; pre-stage VUG 10% trim",
      },
      {
          "trigger": "Credit / Trend Stop (`HY>4.0%` or `VTI<200MA`)",
          "now": (f"HY {hy:.2f}%; VTI {vti.get('Dist_to_200MA', np.nan):+.1f}% "
                  "vs 200MA"),
          "fired": bool(hy > 4.0 or vti_wk_200),
          "verdict": "Intact (+3.4% buffer on VTI 200MA)",
      },
      {
          "trigger":
              "Power Reclaim (`NLR` & `CCJ > 200DMA`)",
          "now": (f"NLR {nlr.get('Dist_to_200MA', np.nan):+.0f}% / CCJ "
                  f"{ccj.get('Dist_to_200MA', np.nan):+.0f}% vs 200MA"),
          "fired":
              bool(
                  nlr.get("Dist_to_200MA", -1) > 0 and
                  ccj.get("Dist_to_200MA", -1) > 0),
          "verdict":
              "Stay in 3B: hold VPU, cut NLR & CCJ 50%",
      },
      {
          "trigger": "Crypto Stop (weekly `IBIT < 200DMA`)",
          "now": (f"IBIT {ibit.get('Dist_to_200MA', np.nan):+.1f}% vs 200MA "
                  f"(RSI {ibit.get('RSI', np.nan):.0f})"),
          "fired": ibit_wk_200,
          "verdict": "Hold IBIT core; cut IREN (-50% 200MA) & BMNR",
      },
  ]


def scorecard_md(rows: List[Dict[str, Any]]) -> str:
  """Compact 4-column markdown table for the trigger scorecard."""
  tbl = [[
      r["trigger"],
      r["now"],
      "🔴 **FIRED**" if r["fired"] else "⚪ Watch",
      r["verdict"],
  ] for r in rows]
  return tabulate(
      tbl,
      headers=[
          "Rule Trigger",
          "Nov 2 Close Reading",
          "Status",
          "Immediate Action",
      ],
      tablefmt="pipe",
  )


def _eligible_leaders(df: pd.DataFrame) -> List[Tuple[str, str]]:
  """Tactical leaders evaluated for fresh capital as of Nov 2, 2026."""
  out = []
  for t in TACTICAL_LEADERS:
    r = _row_of(df, t) or tech_of(t)
    if not r:
      continue
    d200 = r.get("Dist_to_200MA", np.nan)
    rsi = r.get("RSI", np.nan)
    earn = str(r.get("Upcoming_Earnings", "")) or get_upcoming_earnings(
        t, TICKERS_DIR)
    days = np.nan
    if re.match(r"\d{4}-\d{2}-\d{2}", earn):
      days = (pd.Timestamp(earn) - pd.Timestamp(REPORT_DATE)).days
    if pd.notna(d200) and d200 < -3.0:
      out.append((t, f"❌ {d200:+.1f}% 200MA (RSI {rsi:.0f}) — BLOCKED"))
    elif pd.notna(days) and 0 <= days <= 10:
      out.append((t, f"⏸ Print {earn[5:]} ({int(days)}d) — WAIT"))
    else:
      out.append((t, f"✅ {d200:+.1f}% 200MA, RSI {rsi:.0f} — ELIGIBLE"))
  return out


def build_deployment_plan(df: pd.DataFrame, macro: Dict[str, Any],
                          ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
  """Five conditional tranches for fresh capital (percent of new money)."""
  del df
  soxx, smh, spy, vti = (
      tech_of("SOXX"),
      tech_of("SMH"),
      tech_of("SPY"),
      tech_of("VTI"),
  )
  nvda = tech_of("NVDA")
  us10y = macro.get("US10Y", {}).get("value", np.nan)
  hy = macro.get("HY_SPREAD", {}).get("value", np.nan)
  s_rsi = soxx.get("RSI", np.nan)
  s_d200 = soxx.get("Dist_to_200MA", np.nan)
  smh_d200 = smh.get("Dist_to_200MA", np.nan)
  spy_d50 = spy.get("Dist_to_50MA", np.nan)
  vti_d200 = vti.get("Dist_to_200MA", np.nan)
  core_route = ("VTV 50% / VTI 30% / SCHD-VIG 20%"
                if us10y >= 4.75 else "VTI 40% / VUG 40% / VGT 20%")

  t1_live = bool(s_rsi <= 35 and smh_d200 > -3.0 and vti_d200 > 0 and hy < 4.0)
  t1 = {
      "id": "T1",
      "title": "T1: Capitulation Starter",
      "share": 20.0,
      "window": "Nov 2–6 (Core Now / Tactical Thu Nov 5)",
      "question": (f"SOXX RSI≤35 & SMH/TSM/NVDA ≥-3% 200MA?\n"
                   f"(SOXX RSI {s_rsi:.0f}, SMH {smh_d200:+.1f}% 200MA, "
                   f"VTI {vti_d200:+.1f}%)"),
      "state": "DEPLOY (SPLIT)" if t1_live else "WAIT",
      "taken": t1_live,
      "deploy": [
          f"Core 10% NOW: {core_route}",
          "Tactical 10% THU: TSM 35% / SMH 35% / NVDA-MSFT 30%",
          "Gate: SMH/TSM hold 200MA post-Midterms + AMD/ANET",
      ],
      "wait": [
          "Fri SOXX & SMH < -3% 200MA → cancel Thu clip to T3",
          "MRVL (-6.6% 200MA) & GOOG/META excluded from T1",
      ],
      "invalidation": "Fri SOXX < $462.20 or HY ≥ 4.0% freezes tactical.",
  }

  t2 = {
      "id": "T2",
      "title": "T2: Post-Midterm & AMD/ANET",
      "share": 20.0,
      "window": "Nov 5–14 (after Midterms 11/3, AMD/ANET 11/3, NFP 11/6)",
      "question":
          (f"SPY > 50DMA ({spy_d50:+.1f}%) OR SOXX > 200MA "
           f"({s_d200:+.1f}%)\nOR AMD & ANET hold > 200DMA post-print?"),
      "state": "PENDING",
      "taken": None,
      "deploy": [
          f"Core 10%: {core_route}",
          "Tactical 10%: SMH 40% / TSM 30% / AMD 15% / ANET 15%",
      ],
      "wait": [
          "No trigger by Nov 14 → deploy Core 10%, roll Tactical to T3",
          "Exclude AMD/ANET if post-print close < -3% vs 200MA",
      ],
      "invalidation": "HY ≥ 4.0% or VTI < 200MA freezes T2.",
  }

  nvda_d200 = nvda.get("Dist_to_200MA", np.nan)
  nvda_rsi = nvda.get("RSI", np.nan)
  t3 = {
      "id": "T3",
      "title": "T3: Oct CPI & NVDA Print",
      "share": 25.0,
      "window": "Nov 10 (CPI) → Nov 20 (post-NVDA 11/17)",
      "question": (f"NVDA post-11/17 close ≥ -5% w/ guide intact\n"
                   f"AND SMH/SOXX > 200MA? (NVDA {nvda_d200:+.1f}% 200MA, "
                   f"RSI {nvda_rsi:.0f})"),
      "state": "PENDING",
      "taken": None,
      "deploy": [
          "Tactical 15%: SMH 40% / NVDA 25% / TSM 20% / ANET 15%",
          f"Core 10%: {core_route}",
      ],
      "wait": [
          "Hot CPI (>0.4% m/m) or NVDA guide cut → 100% Core (VTV/VTI)",
          "Roll un-deployed tactical share to T5",
      ],
      "invalidation": "10Y > 5.50% or HY ≥ 4.0% freezes T3.",
  }

  t4 = {
      "id": "T4",
      "title": "T4: Dec FOMC & ANT IPO",
      "share": 20.0,
      "window": "Dec 1–15 (FOMC 12/9 + Anthropic IPO)",
      "question": (f"10Y weekly close < 4.75% (now {us10y:.2f}%)\n"
                   "OR Anthropic 'ANT' holds Day-1 IPO price?"),
      "state": "PENDING",
      "taken": None,
      "deploy": [
          "If 10Y < 4.75%: Core 10% unlocks VUG/VGT (GOOG/META dip)",
          "Tactical 10%: TSM / NVDA / ANET / AVGO (if > 200MA)",
      ],
      "wait": [
          "Hawkish FOMC & 10Y > 5.0% → Core 10% to VTV/SCHD, Tactical to T5",
      ],
      "invalidation": "10Y > 5.50% holds T4 in VMFXX.",
  }

  t5 = {
      "id": "T5",
      "title": "T5: Q1 2027 Capitulation Reserve",
      "share": 15.0,
      "window": "VMFXX (~4.0% yield) · Backstop Jan 29, 2027",
      "question": ("VTI within 2% of 200DMA w/ RSI < 35\n"
                   "OR HY spread peaks & turns down from > 4.0%?"),
      "state": "RESERVE",
      "taken": None,
      "deploy": [
          "Washout trigger: 9% Core (VTI/VTV) + 6% Tactical (SMH/TSM)",
          "Jan 29 backstop: 7.5% Core index + 7.5% permanent cash",
      ],
      "wait": ["Earns ~4.0% yield in VMFXX while waiting",],
      "invalidation": "Permanent tail-risk backstop.",
  }
  return [t1, t2, t3, t4, t5]


def create_deployment_tree(
    out_path: str,
    plan: List[Dict[str, Any]],
    ctx: Dict[str, Any],
    leaders: List[Tuple[str, str]],
) -> None:
  """Renders a compact, scannable fresh-capital deployment tree."""
  dot = Digraph(comment="11-02 Fresh Capital Deployment Tree")
  setup_decision_tree_aesthetics(dot)
  dot.attr(rankdir="TB", nodesep="0.28", ranksep="0.38", size="15,28")
  dot.attr("node", fontsize="13")
  dot.node(
      "Start",
      "FRESH CAPITAL — 100% (Nov 2, 2026 → Jan 29, 2027)\n"
      "Gate: " +
      ("RISK-OFF (½ units · only >200DMA)" if ctx["risk_off"] else "NORMAL") +
      " · Split: Core Index + Tactical Leaders",
      fillcolor="#1D3557",
      fontcolor="white",
      style="filled,rounded,bold",
  )
  dot.node(
      "Stop",
      "GLOBAL PAUSE RULES\n"
      "• HY ≥ 3.50%: tactical ½ pace\n"
      "• HY ≥ 4.00%: tactical frozen\n"
      "• VTI < 200DMA: tactical frozen\n"
      "• 10Y > 5.50%: VTV/SCHD/VMFXX only\n"
      "• Freeze ≤ 10d before earnings",
      shape="note",
      fillcolor="#FFF3CD",
      penwidth="1.5",
      fontsize="12",
  )
  elig = "\n".join(f"• {t}: {why}" for t, why in leaders)
  dot.node(
      "Elig",
      "LEADER AUDIT (NOV 2)\n" + elig,
      shape="note",
      fillcolor="#FFFFFF",
      fontsize="12",
  )
  with dot.subgraph() as s:
    s.attr(rank="same")
    s.node("Stop")
    s.node("Start")
    s.node("Elig")
  dot.edge("Start", "Stop", style="dotted", constraint="false")
  dot.edge("Start", "Elig", style="dotted", constraint="false")
  prev = "Start"
  for t in plan:
    tid = t["id"]
    dot.node(
        tid,
        f"{t['title']} ({t['share']:.0f}% Fresh Capital) · {t['window']}",
        fillcolor="#457B9D",
        fontcolor="white",
    )
    dot.edge(prev, tid, penwidth="2")
    dot.node(f"{tid}_c", t["question"], shape="diamond", fillcolor="#FFE8D6")
    dot.edge(tid, f"{tid}_c")
    taken = t["taken"]
    head_y = "DEPLOY" + (" ◀ TODAY" if taken else "")
    body_y = "\n".join("• " + b for b in t["deploy"])
    dot.node(
        f"{tid}_y",
        f"{head_y}\n{body_y}",
        **_node_style(True if taken else None, GREEN),
    )
    body_n = "\n".join("• " + b for b in t["wait"])
    dot.node(
        f"{tid}_n",
        f"WAIT / RE-ROUTE\n{body_n}\n• Pause if: {t['invalidation']}",
        **_node_style(False if taken else None, AMBER),
    )
    dot.edge(
        f"{tid}_c",
        f"{tid}_y",
        label=" Yes",
        **_edge_style(True if taken else None),
    )
    dot.edge(
        f"{tid}_c",
        f"{tid}_n",
        label=" No",
        **_edge_style(False if taken else None),
    )
    with dot.subgraph() as s:
      s.attr(rank="same")
      s.node(f"{tid}_y")
      s.node(f"{tid}_n")
    if prev != "Start":
      dot.edge(f"{prev}_y", tid, style="invis")
      dot.edge(f"{prev}_n", tid, style="invis")
    prev = tid
  dot.render(out_path, format="png", cleanup=True)
  logger.info("Saved deployment tree %s.png", out_path)


def deployment_table_md(plan: List[Dict[str, Any]]) -> str:
  """Unified 6-column fresh-capital tranche execution table."""
  rows = []
  cum = 0.0
  for t in plan:
    cum += t["share"]
    rows.append([
        f"**{t['title']}**",
        f"`{t['share']:.0f}%` (`{cum:.0f}%`)",
        t["window"],
        t["question"].replace("\n", " "),
        "; ".join(t["deploy"]),
        f"**{t['state']}** · {t['wait'][0]}",
    ])
  return tabulate(
      rows,
      headers=[
          "Tranche",
          "Share (Cum)",
          "Window",
          "Trigger",
          "Deploy Split (Core + Tactical)",
          "State & Fallback Rule",
      ],
      tablefmt="pipe",
  )


def wrapper_routing_md() -> str:
  """Compact tax-wrapper routing table."""
  rows = [
      [
          "`Roth IRA (Tax-Free)`",
          "Tactical Leaders (`SMH`, `TSM`, `NVDA`, `ANET`, `AMD`)",
          "Shields high-compounding AI beta & active trim turnover",
      ],
      [
          "`Taxable Core`",
          "Core Value (`VTV`, `VTI`, `VIG`) + Tax-Loss Harvests",
          "Pair index inflows with `CUT` harvests (`WDC`, `COHR`, `NLR`, `CCJ`)",
      ],
      [
          "`401k / Trad IRA`",
          "Scheduled Core DCA (`VTI`, `VTV`, `VUG`, `VGT`)",
          "Route new inflows to `VTV`/`VTI` while `10Y ≥ 4.75%`",
      ],
      [
          "`HSA Wrapper`",
          "Defensive Yield (`SCHD`, `SCHB`, `VHT`)",
          "Low-vol compounders (`SCHD` RSI 86, `VHT` RSI 78)",
      ],
  ]
  return tabulate(
      rows,
      headers=["Tax Wrapper", "Primary Vehicles", "Rule"],
      tablefmt="pipe",
  )


def load_macro() -> Dict[str, Any]:
  """Latest macro snapshot plus 3-month deltas for key series."""
  path = os.path.join(MARKET_DATA_DIR, "macro", "economic_indicators.tsv")
  df = pd.read_csv(path, sep="\t")
  df["DATE"] = pd.to_datetime(df["DATE"])
  df = df[df["DATE"] <= pd.Timestamp(REPORT_DATE)].sort_values("DATE")
  keys = [
      "FEDFUNDS",
      "US02Y",
      "US10Y",
      "US30Y",
      "CPI",
      "UNRATE",
      "HY_SPREAD",
      "RECESSION_PROB",
      "UMICH_SENTIMENT",
      "WTI_CRUDE",
      "COPPER_PRICE",
      "USD_INDEX",
      "ST_LOUIS_FIN_STRESS",
      "US_POLICY_UNCERTAINTY",
      "ELECTRIC_POWER_INDEX",
  ]
  out: Dict[str, Any] = {}
  for k in keys:
    if k not in df.columns:
      continue
    s = df[["DATE", k]].dropna()
    if s.empty:
      continue
    last = s.iloc[-1]
    prior = s[s["DATE"] <= last["DATE"] - pd.Timedelta(days=91)]
    out[k] = {
        "value":
            float(last[k]),
        "date":
            last["DATE"].date().isoformat(),
        "chg_3m":
            (float(last[k] - prior.iloc[-1][k]) if not prior.empty else np.nan),
    }
  return out


def macro_table(macro: Dict[str, Any]) -> str:
  """Compact 9-row macro table focused on actionable regime triggers."""
  labels = {
      "FEDFUNDS": ("Fed Funds (%)", "On hold (3.75%); 2 hawkish dissenters"),
      "US02Y": ("2Y Treasury (%)", "4.61% — higher-for-longer front end"),
      "US10Y": ("10Y Treasury (%)", "4.98% — Core Gate 1 NO (≥4.75%)"),
      "HY_SPREAD": ("HY Spread (%)", "3.26% (+49bp 3M) — Risk-Off Gate ON"),
      "WTI_CRUDE": ("WTI Crude ($/bbl)", "$103.37 — $1.63 below $105 trigger"),
      "UNRATE": ("Unemployment (%)", "4.2% — Nov 6 NFP is key labor test"),
      "UMICH_SENTIMENT": ("UMich Sentiment", "48.1 — recessionary consumer"),
      "ST_LOUIS_FIN_STRESS":
          ("Fin Stress Idx", "-0.58 — no systemic credit panic"),
      "US_POLICY_UNCERTAINTY": ("Policy Uncertainty", "251.1 — Nov 3 Midterms"),
  }
  rows = []
  for k, (lab, interp) in labels.items():
    if k in macro:
      m = macro[k]
      rows.append([
          lab,
          f"{m['value']:.2f}",
          f"{m['chg_3m']:+.2f}" if pd.notna(m["chg_3m"]) else "—",
          interp,
      ])
  return tabulate(
      rows,
      headers=["Indicator", "Latest", "Δ 3M", "Portfolio Signal"],
      tablefmt="pipe",
  )


def ai_ipo_digest(max_items: int = 5) -> str:
  """Scans all news TSVs for AI-related IPO headlines in the last 45 days."""
  since = pd.Timestamp(REPORT_DATE) - pd.Timedelta(days=45)
  found: List[Tuple[pd.Timestamp, str, str]] = []
  seen: set = set()
  for root in ("topics", "tickers"):
    base = os.path.join(MARKET_DATA_DIR, root)
    if not os.path.exists(base):
      continue
    for name in sorted(os.listdir(base)):
      path = os.path.join(base, name, "news.tsv")
      if not os.path.exists(path):
        continue
      try:
        df = pd.read_csv(path, sep="\t", usecols=["Date", "Headline", "URL"])
      except (ValueError, pd.errors.ParserError):
        continue
      df = df.dropna(subset=["Headline"])
      mask = df["Headline"].str.contains(r"\bIPO\b", case=False, regex=True)
      df = df[mask]
      if df.empty:
        continue
      df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
      df = df[df["Date"] >= since]
      for _, r in df.iterrows():
        h = str(r["Headline"]).strip()
        hl = h.lower()
        if not any(k in hl for k in AI_IPO_KEYWORDS):
          continue
        key = re.sub(r"[^a-z0-9]", "", hl)[:45]
        if key in seen:
          continue
        seen.add(key)
        found.append((r["Date"], h, str(r.get("URL", ""))))
  found.sort(key=lambda x: x[0], reverse=True)
  lines = []
  for d, h, u in found[:max_items]:
    link = f"[{h}]({u})" if u.startswith("http") else h
    lines.append(f"- **{d.strftime('%m/%d')}** — {link}")
  return "\n".join(lines) if lines else "*No AI IPO headlines found.*"


def _fmt(x: Any,
         spec: str = ".1f",
         suffix: str = "",
         signed: bool = False) -> str:
  if x is None or (isinstance(x, float) and np.isnan(x)):
    return "—"
  try:
    v = float(x)
  except (TypeError, ValueError):
    return str(x)
  s = f"{v:+{spec}}" if signed else f"{v:{spec}}"
  return s + suffix


_ACTION_RANK = {
    "CUT": 0,
    "TRIM": 1,
    "TRIM PRE-PRINT": 2,
    "ADD": 3,
    "HOLD-THRU-PRINT": 4,
    "HOLD": 5,
}


def _classify(r: pd.Series, ctx: Dict[str, Any],
              sleeve_val: float) -> Tuple[str, str, str]:
  """Rule-based action, concise size, and trigger for a tactical holding."""
  t = str(r.get("Ticker", ""))
  pnl = r.get("Unrealized_PnL_Pct", np.nan)
  rsi = r.get("RSI", np.nan)
  d200 = r.get("Dist_to_200MA", np.nan)
  rs3 = r.get("RS_3M_vs_SPY", np.nan)
  rs_ytd = r.get("RS_YTD_vs_SPY", np.nan)
  dd = r.get("Drawdown_52W", np.nan)
  val = float(r.get("Current_Value", 0.0))
  wt_slv = val / sleeve_val * 100.0 if sleeve_val > 0 else 0.0
  earn = str(r.get("Upcoming_Earnings", ""))
  days_to_print = np.nan
  if re.match(r"\d{4}-\d{2}-\d{2}", earn):
    days_to_print = (pd.Timestamp(earn) - pd.Timestamp(REPORT_DATE)).days
  near_print = 0 <= days_to_print <= 14

  add_act_pct = ctx["add_pct"]
  add_slv_pct = ctx["add_sleeve_pct"]

  if t in {"GOOG", "META"}:
    return (
        "HOLD",
        "Hold (RSI < 15); route dip to VGT/MSFT",
        f"RSI {rsi:.0f}, {d200:+.1f}% vs 200MA (capitulation hold)",
    )
  if t in {"AVGO", "ASML", "CEG", "VST"}:
    return (
        "HOLD",
        "Hold core; add only > 200DMA",
        f"{d200:+.1f}% vs 200MA, RSI {rsi:.0f}",
    )
  if t == "MRVL":
    return (
        "HOLD",
        "Blocked from T1 (-6.6% 200MA); hold",
        f"-12.7% 1D, broke 200DMA ({d200:+.1f}%)",
    )

  cut = (pd.notna(pnl) and pnl <= -15 and (pd.isna(d200) or d200 < -3.0) and
         pd.notna(rs3) and rs3 < -10)
  if t in {
      "XSD", "WDC", "COHR", "DRAM", "NLR", "CCJ", "AIPO", "RKLB", "NASA",
      "BMNR", "IREN"
  }:
    cut = True

  if cut:
    if near_print:
      size = f"Sell 50% ({wt_slv*0.5:.1f}% slv) post-{earn[5:]}"
    elif pd.notna(dd) and dd <= -50:
      size = f"Exit 100% ({wt_slv:.1f}% slv) tax-loss"
    else:
      size = f"Sell 50% ({wt_slv*0.5:.1f}% slv) now"
    d200_tag = f"{d200:+.1f}% 200MA, " if pd.notna(d200) else "<200MA, "
    return "CUT", size, f"{d200_tag}{dd:.0f}% 52W DD"

  trim = pd.notna(rsi) and rsi >= 68 and pnl > 15
  if trim:
    size = f"Trim 25% ({wt_slv*0.25:.1f}% slv → VMFXX)"
    act = "TRIM PRE-PRINT" if near_print else "TRIM"
    return act, size, f"RSI {rsi:.0f}, Vint {pnl:+.0f}%"

  if near_print:
    return (
        "HOLD-THRU-PRINT",
        f"Freeze pre-print ({earn[5:]})",
        f"Print {earn[5:]}, {d200:+.1f}% 200MA",
    )

  add = (pd.notna(rsi) and rsi <= 45 and pd.notna(d200) and d200 >= -2.5 and
         (pd.notna(rs_ytd) and rs_ytd > -5) and dd > -26)
  if add:
    if t == "SOXX":
      return (
          "HOLD",
          "Watch (Fri $462.20 stop); add via SMH",
          f"{d200:+.1f}% 200MA, RSI {rsi:.0f}",
      )
    if t == "SMH":
      return (
          "ADD",
          f"+{add_act_pct*0.35:.2f}% book (+{add_slv_pct*0.35:.1f}% slv) Thu",
          f"Holds 200MA ({d200:+.1f}%), RSI {rsi:.0f}",
      )
    if 14 < days_to_print <= 22:
      return (
          "ADD",
          f"+{add_act_pct/3:.2f}% book (⅓ unit pre-{earn[5:]})",
          f"Holds 200MA ({d200:+.1f}%), RSI {rsi:.0f}",
      )
    return (
        "ADD",
        f"+{add_act_pct:.2f}% book (+{add_slv_pct:.1f}% slv) ½ unit",
        f"Holds 200MA ({d200:+.1f}%), RSI {rsi:.0f}",
    )
  return "HOLD", "Hold core; trail 12–15%", f"{d200:+.1f}% 200MA, RSI {rsi:.0f}"


def priority_actions_table(df: pd.DataFrame, ctx: Dict[str, Any]) -> str:
  """Compact 6-column table of tactical positions where Action != HOLD."""
  sleeve = df[~df["Theme"].isin(CORE_THEMES) & ~df["Ticker"].isin(CASH_LIKE)]
  sleeve_val = float(sleeve["Current_Value"].sum())
  rows = []
  for _, r in sleeve.iterrows():
    action, size, why = _classify(r, ctx, sleeve_val)
    if action == "HOLD":
      continue
    wt_slv = float(r["Current_Value"]) / sleeve_val * 100.0
    rows.append((
        _ACTION_RANK[action],
        -wt_slv,
        [
            f"**{r['Ticker']}**",
            f"**{action}**",
            f"{r['Weight_Pct']:.2f}%",
            f"{wt_slv:.1f}%",
            size,
            why,
        ],
    ))
  rows.sort(key=lambda x: (x[0], x[1]))
  return tabulate(
      [x[2] for x in rows],
      headers=[
          "Ticker",
          "Action",
          "Book Wt%",
          "Sleeve Wt%",
          "Execution Size (% Only)",
          "Trigger",
      ],
      tablefmt="pipe",
  )


def unified_stocks_table(stocks: pd.DataFrame, ctx: Dict[str, Any],
                         sleeve_val: float) -> str:
  """Compact 9-column table for all 25 individual tactical equities."""
  rows = []
  for _, r in stocks.iterrows():
    action, size, _ = _classify(r, ctx, sleeve_val)
    act_str = f"**{action}**" if action != "HOLD" else "HOLD"
    earn = str(r.get("Upcoming_Earnings") or "—")
    earn_short = earn[5:10] if len(earn) >= 10 else "—"
    rows.append([
        f"**{r['Ticker']}**",
        act_str,
        f"{r['Weight_Pct']:.2f}%",
        "$" + _fmt(r.get("Price"), ".2f"),
        _fmt(r.get("Ret_1D"), signed=True, suffix="%"),
        _fmt(r["Unrealized_PnL_Pct"], signed=True, suffix="%"),
        _fmt(r.get("RSI"), ".0f"),
        _fmt(r.get("Dist_to_200MA"), signed=True, suffix="%"),
        f"{earn_short} · {size}",
    ])
  headers = [
      "Ticker",
      "Action",
      "Book Wt%",
      "Close",
      "1D%",
      "Vint%",
      "RSI",
      "vs 200MA",
      "Print & Execution Rule",
  ]
  return tabulate(rows, headers=headers, tablefmt="pipe")


def unified_etfs_table(etfs: pd.DataFrame, ctx: Dict[str, Any],
                       sleeve_val: float) -> str:
  """Compact 9-column table for all 9 thematic & sector ETFs."""
  rows = []
  for _, r in etfs.iterrows():
    action, size, _ = _classify(r, ctx, sleeve_val)
    act_str = f"**{action}**" if action != "HOLD" else "HOLD"
    rows.append([
        f"**{r['Ticker']}**",
        r["Theme"].split(" /")[0][:12],
        act_str,
        f"{r['Weight_Pct']:.2f}%",
        _fmt(r.get("Ret_1D"), signed=True, suffix="%"),
        _fmt(r["Unrealized_PnL_Pct"], signed=True, suffix="%"),
        _fmt(r.get("RSI"), ".0f"),
        _fmt(r.get("Dist_to_200MA"), signed=True, suffix="%"),
        size,
    ])
  headers = [
      "Ticker",
      "Theme",
      "Action",
      "Book Wt%",
      "1D%",
      "Vint%",
      "RSI",
      "vs 200MA",
      "Execution Rule",
  ]
  return tabulate(rows, headers=headers, tablefmt="pipe")


def core_ballast_table(core_df: pd.DataFrame, core_val: float) -> str:
  """Compact 8-column table for Core Ballast holdings."""
  del core_val
  role_map = {
      "VTI":
          "Gate 2 YES (+3.4% 200MA) — Keep scheduled DCA + 30% of core legs",
      "VUG":
          "Gate 1 NO — Freeze adds while 10Y ≥ 4.75%; hold existing lots",
      "VTV":
          "Gate 1 NO — Primary core-leg destination (50% of new core flows)",
      "VGT":
          "Gate 1 NO — Queued to buy GOOG/META/MSFT dip once 10Y < 4.75%",
      "VEA":
          "Intl Anchor — Holding 200MA (+0.7%, RSI 46); maintain weight",
      "SCHD":
          "Dividend Leader (+32.7% YTD, RSI 86) — Receive 10% of core legs",
      "VIG":
          "Dividend Growth (+13.9% YTD, RSI 75) — Receive 10% of core legs",
      "SCHB":
          "Broad US Core (HSA sleeve) — Maintain scheduled DCA",
      "VMFXX":
          "Dry Powder (3 × 2.2% tranches @ ~4.0% yield) + fresh-cash staging",
      "VUSB":
          "Short-Duration Bond Reserve — Secondary liquidity buffer",
  }
  rows = []
  for _, r in core_df.iterrows():
    t = str(r["Ticker"])
    rows.append([
        f"**{t}**",
        r["Theme"].split(" /")[0][:12],
        f"{r['Weight_Pct']:.2f}%",
        _fmt(r["Unrealized_PnL_Pct"], signed=True, suffix="%"),
        _fmt(r.get("Ret_YTD"), signed=True, suffix="%"),
        _fmt(r.get("RSI"), ".0f"),
        _fmt(r.get("Dist_to_200MA"), signed=True, suffix="%"),
        role_map.get(t, "Hold core"),
    ])
  headers = [
      "Ticker",
      "Category",
      "Book Wt%",
      "Vint%",
      "YTD%",
      "RSI",
      "vs 200MA",
      "Gate Rule & Role",
  ]
  return tabulate(rows, headers=headers, tablefmt="pipe")


def semis_hyperscaler_audit_table(df: pd.DataFrame) -> str:
  """Compact 8-column audit table for the Semis & Hyperscaler dip."""
  focus = [
      "SOXX",
      "SMH",
      "NVDA",
      "TSM",
      "AMD",
      "AVGO",
      "MRVL",
      "ANET",
      "ASML",
      "WDC",
      "COHR",
      "GOOG",
      "META",
      "MSFT",
      "AMZN",
      "AAPL",
  ]
  rows = []
  for t in focus:
    r = _row_of(df, t)
    if not r:
      continue
    d200 = r.get("Dist_to_200MA", np.nan)
    rsi = r.get("RSI", np.nan)
    if t in {"GOOG", "META"}:
      regime = "🟡 Hold (RSI<15); dip via VGT/MSFT"
    elif t in {"WDC", "COHR"}:
      regime = "🔴 CUT 50% (<200MA breakdown)"
    elif t == "MRVL":
      regime = "🟠 Blocked from T1 (-6.6% 200MA)"
    elif t == "AVGO":
      regime = "🟠 Hold; wait for 200MA / ANT IPO"
    elif t == "SOXX":
      regime = "🟠 Watch: Fri $462.20 stop (-3% 200MA)"
    elif t in {"AMD", "ANET", "AAPL"}:
      regime = "⏸ Freeze pre-print (Nov 2–3)"
    elif pd.notna(d200) and d200 >= -2.5:
      regime = "🟢 ADD Eligible (holds 200MA)"
    else:
      regime = "🟠 Hold core; freeze adds (<200MA)"

    rows.append([
        f"**{t}**",
        "$" + _fmt(r.get("Price"), ".2f"),
        _fmt(r.get("Ret_1D"), signed=True, suffix="%"),
        _fmt(r.get("Ret_1M"), signed=True, suffix="%"),
        _fmt(r.get("Drawdown_52W"), ".1f", "%"),
        _fmt(rsi, ".1f"),
        _fmt(d200, signed=True, suffix="%"),
        regime,
    ])
  return tabulate(
      rows,
      headers=[
          "Ticker",
          "Close",
          "1D%",
          "1M%",
          "52W DD",
          "RSI",
          "vs 200MA",
          "Nov 2 Action & Rule",
      ],
      tablefmt="pipe",
  )


def earnings_playbook(earn: pd.DataFrame, df: pd.DataFrame,
                      ctx: Dict[str, Any]) -> str:
  """Compact 7-column pre- and post-print earnings table."""
  if earn.empty:
    return "*No model holdings report in the next 75 days.*"
  sleeve = df[~df["Theme"].isin(CORE_THEMES) & ~df["Ticker"].isin(CASH_LIKE)]
  sleeve_val = float(sleeve["Current_Value"].sum())
  rows = []
  for _, r in earn.iterrows():
    action, size, _ = _classify(r, ctx, sleeve_val)
    pnl = r.get("Unrealized_PnL_Pct", np.nan)
    rsi = r.get("RSI", np.nan)
    d200 = r.get("Dist_to_200MA", np.nan)
    if action == "CUT" or (pd.notna(pnl) and pnl <= -15 and pd.notna(d200) and
                           d200 < -5):
      post = "Sell 50–100% on 1st post-print close"
    elif pd.notna(rsi) and rsi >= 68 and pnl > 15:
      post = "Gap >+8% → trim 25%; else hold"
    else:
      post = (f"Hold >200MA + intact guide → eligible for T2/T3 "
              f"(+{ctx['add_pct']/3:.2f}% book)")
    rows.append([
        r["Earn_Date"].strftime("%b %d"),
        f"**{r['Ticker']}**",
        f"{r['Weight_Pct']:.2f}%",
        _fmt(rsi, ".0f"),
        _fmt(d200, signed=True, suffix="%"),
        f"**{action}** · {size}" if action != "HOLD" else "HOLD · freeze",
        post,
    ])
  return tabulate(
      rows,
      headers=[
          "Date",
          "Ticker",
          "Book Wt%",
          "RSI",
          "vs 200MA",
          "Pre-Print Stance",
          "Post-Print Rule",
      ],
      tablefmt="pipe",
  )


def bellwether_earnings_table(held_tickers: set) -> str:
  """Compact 5-column non-held ecosystem bellwether earnings table."""
  rows = []
  for ticker, role in BELLWETHER_WATCH:
    if ticker in held_tickers:
      continue
    edate = get_upcoming_earnings(ticker, TICKERS_DIR)
    if not re.match(r"\d{4}-\d{2}-\d{2}", str(edate)):
      continue
    dt = pd.Timestamp(edate)
    if (dt < pd.Timestamp(REPORT_DATE) or
        dt > pd.Timestamp(REPORT_DATE) + pd.Timedelta(days=60)):
      continue
    px = load_prices(ticker)
    rsi_str = d200_str = "—"
    if px is not None and not px.empty:
      tech = calculate_technical_metrics(px)
      rsi_str = _fmt(tech.get("RSI"), ".0f")
      d200_str = _fmt(tech.get("Dist_to_200MA"), signed=True, suffix="%")
    rows.append((
        dt,
        [
            dt.strftime("%b %d"),
            f"**{ticker}**",
            rsi_str,
            d200_str,
            role.split(" —", maxsplit=1)[0],
        ],
    ))
  rows.sort(key=lambda x: x[0])
  if not rows:
    return "*No non-held ecosystem bellwether prints in window.*"
  return tabulate(
      [r[1] for r in rows[:6]],
      headers=["Date", "Bellwether", "RSI", "vs 200MA", "Read-Through"],
      tablefmt="pipe",
  )


def pillar_table(pillars: List[Dict[str, Any]]) -> str:
  """Compact 5-column live-reading table for the five pillars."""
  rows = []
  for p in pillars:
    rows.append(
        [p["name"], p["trigger"], p["reading"], f"**{p['state']}**", p["sub"]])
  return tabulate(
      rows,
      headers=["Pillar", "Trigger", "Nov 2 Reading", "State", "Live Rule"],
      tablefmt="pipe",
  )


def hypotheses_and_contingencies_md(df: pd.DataFrame, macro: Dict[str, Any],
                                    ctx: Dict[str,
                                              Any], last: pd.Series) -> str:
  """Concise 6-hypothesis table + 5-row scenario contingency matrix."""
  del df, last
  us10y = macro.get("US10Y", {}).get("value", np.nan)
  wti = macro.get("WTI_CRUDE", {}).get("value", np.nan)
  hy = macro.get("HY_SPREAD", {}).get("value", np.nan)
  b = ctx.get("bell", {})
  soxx, smh, nvda, goog = (
      b.get("SOXX", {}),
      b.get("SMH", {}),
      b.get("NVDA", {}),
      b.get("GOOG", {}),
  )
  meta, msft, amzn = b.get("META", {}), b.get("MSFT", {}), b.get("AMZN", {})

  def _g(d: Dict[str, Any], k: str, spec: str = "+.1f") -> str:
    v = d.get(k, np.nan)
    return "—" if pd.isna(v) else f"{v:{spec}}"

  matrix_rows = [
      [
          "**H1: Semis Dip = Pre-IPO & Event Washout**",
          "Hyperscaler capex raised ($220B AMZN, $135B META); TSM/NVDA/SMH hold 200MA",
          "Capex digestion; if AMD/ANET/NVDA guide flat, SOXX breaks 200MA (-15%)",
          f"SOXX {_g(soxx, 'Dist_to_200MA')}% 200MA (RSI {_g(soxx, 'RSI', '.0f')}); "
          f"SMH {_g(smh, 'Dist_to_200MA')}%, NVDA {_g(nvda, 'Dist_to_200MA')}%",
          "Hold >200MA Thu → deploy T1 tactical; Fri SOXX < $462.20 → trim 20%",
      ],
      [
          "**H2: Rates Peak Near 5.0% vs Stagflation**",
          f"10Y capped near {us10y:.2f}%; Dec FOMC hold unlocks oversold VUG/VGT",
          f"WTI ${wti:.2f} (Hormuz) + hot CPI (11/10) pushes 10Y to 5.25–5.50%",
          f"10Y {us10y:.2f}%, HY {hy:.2f}% (+49bp 3M); VTV RSI 76 vs VUG RSI 24",
          "10Y ≥ 4.75% → 100% core to VTV/VTI/SCHD; 10Y > 5.50% → trim VUG 10%",
      ],
      [
          "**H3: Hyperscaler Dispersion (FCF vs Backlog)**",
          f"MSFT ({_g(msft, 'Dist_to_200MA')}% 200MA) & AMZN ({_g(amzn, 'Dist_to_200MA')}% 200MA) prove cloud backlog monetizes",
          "Ad-funded capex (>80% FCF) keeps GOOG/META in multi-quarter penalty box",
          f"GOOG RSI {_g(goog, 'RSI', '.1f')} ({_g(goog, 'Dist_to_200MA')}% 200MA); "
          f"META RSI {_g(meta, 'RSI', '.1f')} ({_g(meta, 'Dist_to_200MA')}% 200MA)",
          "Hold GOOG/META (no panic sale at RSI<15); new adds to MSFT/AMZN or VGT",
      ],
      [
          "**H4: Nov 3 Midterms Clear Policy Hedge Drag**",
          "12 of 12 post-midterm 12M windows since 1950 positive as hedges unwind",
          "Contested count or immediate semiconductor tariff headlines extend vol",
          f"SPY {_g(b.get('SPY', {}), 'Dist_to_50MA')}% 50MA; QQQ RSI "
          f"{_g(b.get('QQQ', {}), 'RSI', '.0f')}",
          "T1 Core (10%) now; T1 Tactical (10%) waits until Thu Nov 5",
      ],
      [
          "**H5: Anthropic 'ANT' IPO Drains Then Re-Rates**",
          "Oct S-1 cash-raising explains SOXX slide; IPO funds TSM/NVDA/ANET orders",
          "AVGO ($43B rack backstop) & neocloud debt stress hit secondary proxies",
          "AIPO -15.2% vs 200MA (RSI 28); AVGO -12.1% vs 200MA; IREN -50% 200MA",
          "Cut AIPO/IREN 50%; cap AIPO+SPCX ≤ 1.5%; freeze AVGO until >200MA",
      ],
      [
          "**H6: 5-Tranche Phasing Beats Lump-Sum**",
          "Gating 20/20/25/20/15% across 5 Nov–Dec catalysts avoids second-leg traps",
          "V-bottom rally after AMD/NVDA makes T3–T5 buy 8–12% higher",
          f"Book 93.4% invested; Cash {ctx['cash_pct']:.1f}% in VMFXX (~4.0%)",
          "40% (T1+T2) deploys in Nov if >200MA holds; HY ≥ 4.0% freezes tactical",
      ],
  ]
  matrix_md = tabulate(
      matrix_rows,
      headers=[
          "Hypothesis",
          "Bull Case",
          "Bear / Contrarian Case",
          "Nov 2 Evidence",
          "Decision Rule (If X → Do Y)",
      ],
      tablefmt="pipe",
  )

  scen_rows = [
      [
          "**A: Positioning Washout (~50% Base)**",
          "AMD/ANET (11/3) & NVDA (11/17) hold guides; SOXX reclaims $476.60 (200MA)",
          "Deploy T1 Tactical (10%) Thu Nov 5 → T2 (20%) post-Midterms → T3 (25%) post-NVDA",
      ],
      [
          "**B: AI Capex Digestion (~25%)**",
          "Fri Nov 6 SOXX closes < $462.20 (>3% below 200MA) OR flat NVDA guide",
          "Cancel T1 tactical clip; trim SOXX/SMH 20% to VMFXX; convert T2/T3 to 100% Core (VTV/VTI)",
      ],
      [
          "**C: Stagflation / Hormuz (~15%)**",
          f"Oct CPI > 0.4% m/m (11/10), WTI > $105 (now ${wti:.2f}), or 10Y > 5.50%",
          "Exit 100% of <200MA spec names; trim VUG 10% to VMFXX; route T2–T4 to VTV/SCHD only",
      ],
      [
          "**D: Duration Relief (~10%)**",
          "2 weekly closes 10Y < 4.75% AND HY Δ3M < +25bp post-CPI/FOMC",
          f"Unlatch Regime Gate (full {ctx['add_pct']*2:.2f}% units); flip Gate 1 to Growth DCA (VUG/VGT)",
      ],
      [
          "**E: Credit / Trend Stop (~5%)**",
          f"HY > 4.00% (now {hy:.2f}%) OR weekly VTI < 200DMA ($357.90)",
          "Liquidate spec tail (BMNR/IREN/RKLB/NASA/AIPO) to 0%; freeze all tactical tranches",
      ],
  ]
  scen_md = tabulate(
      scen_rows,
      headers=[
          "Scenario (Prob)",
          "Observable Trigger",
          "Pre-Committed Portfolio & Tranche Action",
      ],
      tablefmt="pipe",
  )
  return f"{matrix_md}\n\n### 🛠️ Scenario Contingency Matrix (Nov 3 → Dec 15)\n\n{scen_md}"


def bull_bear_md(df: pd.DataFrame, macro: Dict[str, Any], ctx: Dict[str, Any],
                 last: pd.Series) -> str:
  """Concise 3-bullet Bull / Bear / Flip summary."""
  del df
  b = ctx.get("bell", {})
  soxx, smh, nvda, goog, meta = (
      b.get("SOXX", {}),
      b.get("SMH", {}),
      b.get("NVDA", {}),
      b.get("GOOG", {}),
      b.get("META", {}),
  )
  us10y = macro.get("US10Y", {}).get("value", np.nan)
  wti = macro.get("WTI_CRUDE", {}).get("value", np.nan)
  hy = macro.get("HY_SPREAD", {}).get("value", np.nan)
  return f"""- **🐂 Bull Case (Why We Phase In Rather Than Panic-Sell):**
  1. **Physical Monopolies Hold 200DMA:** `SMH` (`{smh.get('Dist_to_200MA', np.nan):+.1f}%`), `NVDA` (`{nvda.get('Dist_to_200MA', np.nan):+.1f}%`), and `TSM` (`-0.1%`, `+68%` IV disc) hold 200DMA support while `GOOG` (`RSI {goog.get('RSI', np.nan):.1f}`) and `META` (`RSI {meta.get('RSI', np.nan):.1f}`) hit 10-year RSI capitulation (`<15`).
  2. **Hyperscaler Capex Raised:** `AMZN` (`+2.2%` 1D, `$220B` capex, AWS `+39%`), `MSFT` (`+16%` vs 200DMA, `$25B` DC debt raise), and `META` (`$135B` capex) confirm hardware orders remain intact.
  3. **80/20 Ballast Works:** Value (`VTV +20.3%` YTD) and Dividend (`SCHD +32.7%` YTD) cushion the full Model Book at **`{last['Portfolio']:+.1f}%` YTD** (`-0.51%` on Nov 2 vs `SOXX -3.79%`).
- **🐻 Bear Case (Why Risk-Off Gate & 200DMA Stops Stay On):**
  1. **Monday Breadth Damage:** `SOXX` slipped to `{soxx.get('Dist_to_200MA', np.nan):+.1f}%` vs 200DMA (`$453.65`), `MRVL` plunged `-12.7%` (`-6.6%` vs 200DMA), and `AMD` fell `-7.5%` ahead of Nov 3 prints.
  2. **Macro & Credit Friction:** `10Y` at `{us10y:.2f}%`, `WTI` at `${wti:.2f}` (`$1.63` below `$105` trigger), and `HY` at `{hy:.2f}%` (`+49bp` 3M) keep the Risk-Off Gate latched.
  3. **15-Day Catalyst Wall:** `AAPL` (11/2), Midterms + `AMD`/`ANET` (11/3), `QCOM`/`ARM` (11/4), NFP (11/6), CPI (11/10), and `NVDA` (11/17) compress binary risk into two weeks."""


def tree_evolution_md() -> str:
  """Compact 4-row table showing 11-01 -> 11-02 rule updates."""
  rows = [
      [
          "Pillar 1 Capitulation Rule",
          "SOXX -1.1% vs 200MA → Exception active",
          "SOXX -4.8% vs 200MA (SMH/NVDA/TSM hold) → **Fri $462.20 Weekly-Close Stop**",
      ],
      [
          "T1 Eligible Leaders",
          "TSM, SMH, MRVL (+7% vs 200MA)",
          "**MRVL disqualified** (-12.7% 1D, -6.6% 200MA); replaced by NVDA/MSFT/AMZN",
      ],
      [
          "T1 Execution Timing",
          "Mon / Thu clips",
          "**Core 10% Now** (VTV/VTI/SCHD); **Tactical 10% Thu Nov 5** post-Midterms/AMD/ANET",
      ],
      [
          "GOOG / META Rule",
          "Index core expression only",
          "**Capitulation Hold** (RSI 12.7 / 8.2): block panic sale, route adds to MSFT/AMZN/VGT",
      ],
  ]
  return tabulate(
      rows,
      headers=["Rule Dimension", "Prior (11-01)", "Updated Today (11-02)"],
      tablefmt="pipe",
  )


def concentration_stats(df: pd.DataFrame) -> Dict[str, Any]:
  """HHI and top-N weights for the tactical sleeve and the full model book."""
  w = df["Weight_Pct"] / 100
  tact = df[~df["Theme"].isin(CORE_THEMES)]
  tw = tact["Current_Value"] / tact["Current_Value"].sum()
  return {
      "hhi_all":
          float((w**2).sum() * 10000),
      "hhi_tactical":
          float((tw**2).sum() * 10000),
      "top5_all":
          float(df.head(5)["Weight_Pct"].sum()),
      "top5_tactical":
          float(
              tact.head(5)["Current_Value"].sum() /
              tact["Current_Value"].sum() * 100),
      "max_tactical":
          float(tact["Current_Value"].max() / tact["Current_Value"].sum() * 100
               ),
      "max_tactical_ticker":
          str(tact.iloc[0]["Ticker"]),
      "tactical_val":
          float(tact["Current_Value"].sum()),
      "tactical_pct":
          float(tact["Current_Value"].sum() / df["Current_Value"].sum() * 100),
      "tactical_pnl":
          float(tact["Unrealized_PnL_Net"].sum()),
      "tactical_cost":
          float(tact["Cost_Basis"].sum()),
      "n_tactical":
          int(len(tact)),
  }


def default_critique_md(ctx: Dict[str, Any]) -> str:
  """Live NotebookLM critique table if present, else compact fallback."""
  del ctx
  if os.path.exists(CRITIQUE_PATH):
    with open(CRITIQUE_PATH, "r", encoding="utf-8") as f:
      txt = f.read().strip()
      if txt:
        return txt
  return "*Red-team audit table unavailable.*"


def compile_report(
    df: pd.DataFrame,
    wrappers: Dict[str, pd.DataFrame],
    macro: Dict[str, Any],
    curve: pd.DataFrame,
    earn: pd.DataFrame,
    ctx: Dict[str, Any],
    ipo_md: str,
    news_md: str,
    critique_md: str,
    pillars: Optional[List[Dict[str, Any]]] = None,
    gates: Optional[List[Dict[str, Any]]] = None,
) -> str:
  """Assembles the concise, action-first, percentage-only 11-02 REPORT.md."""
  del wrappers
  pillars = pillars or build_pillars(df, macro, ctx)
  gates = gates or build_index_gates(df, macro, ctx)
  total = float(df["Current_Value"].sum())
  cost = float(df["Cost_Basis"].sum())
  pnl = float(df["Unrealized_PnL_Net"].sum())
  day = float(df["Day_Change_Net"].sum())
  total_pnl_pct = pnl / cost * 100.0 if cost > 0 else 0.0
  day_pct = day / (total - day) * 100.0 if (total - day) > 0 else 0.0

  last = curve.iloc[-1]
  b = df.attrs["bench_ret"]
  stocks = df[(df["Quote_Type"] == "EQUITY") & ~df["Ticker"].isin(CASH_LIKE)]
  funds = df[(df["Quote_Type"] != "EQUITY") & ~df["Ticker"].isin(CASH_LIKE)]
  core = funds[funds["Theme"].isin(CORE_THEMES)]
  sector_etfs = funds[~funds["Theme"].isin(CORE_THEMES)]
  conc = concentration_stats(df)
  core_pct = 100.0 - conc["tactical_pct"]
  tact_ret = (conc["tactical_pnl"] / conc["tactical_cost"] *
              100.0 if conc["tactical_cost"] else np.nan)
  ctx["tact_ret"] = tact_ret
  tact_last = last.get("Tactical", np.nan)
  sleeve_val = conc["tactical_val"]
  core_val = total - sleeve_val
  bell = ctx.get("bell", {})
  soxx_b, smh_b, goog_b, meta_b = (
      bell.get("SOXX", {}),
      bell.get("SMH", {}),
      bell.get("GOOG", {}),
      bell.get("META", {}),
  )
  plan = ctx.get("plan", [])
  leaders = ctx.get("leaders", [])
  scorecard = ctx.get("scorecard", [])
  n_fired = sum(1 for r in scorecard if r["fired"])

  def _w(t: str) -> float:
    r = df[df["Ticker"] == t]
    return float(r["Weight_Pct"].iloc[0]) if not r.empty else 0.0

  theme = df.groupby("Theme").agg(
      W=("Weight_Pct", "sum"),
      P=("Unrealized_PnL_Net", "sum"),
      C=("Cost_Basis", "sum"),
  )
  theme["R"] = np.where(theme["C"] > 0, theme["P"] / theme["C"] * 100, 0.0)

  def _tw(name: str) -> Tuple[float, float]:
    if name in theme.index:
      return float(theme["W"].loc[name]), float(theme["R"].loc[name])
    return 0.0, 0.0

  spy_px = load_prices("SPY")
  spy_last_date = (spy_px["Date"].iloc[-1].date().isoformat()
                   if spy_px is not None and not spy_px.empty else
                   REPORT_DATE.isoformat())

  bench_rows = [[
      k,
      _fmt(v["1D"], signed=True, suffix="%"),
      _fmt(v["1M"], signed=True, suffix="%"),
      _fmt(v["3M"], signed=True, suffix="%"),
      _fmt(v["YTD"], signed=True, suffix="%"),
      _fmt(v["1Y"], signed=True, suffix="%"),
  ] for k, v in b.items()]
  bench_rows.insert(
      0,
      [
          "**Full Model Book (80% Core / 20% Tactical)**",
          f"**{day_pct:+.2f}%**",
          "—",
          "—",
          f"**{last['Portfolio']:+.1f}%**",
          "—",
      ],
  )
  if "Tactical" in last:
    bench_rows.insert(
        1,
        [
            "**Tactical Sleeve (20% Weight)**",
            "—",
            "—",
            "—",
            f"**{tact_last:+.1f}%**",
            "—",
        ],
    )
  bench_tbl = tabulate(
      bench_rows,
      headers=["Portfolio / Benchmark", "1D (Nov 2)", "1M", "3M", "YTD", "1Y"],
      tablefmt="pipe",
  )

  pillar_tbl = pillar_table(pillars)
  sleeve = df[~df["Theme"].isin(CORE_THEMES) & ~df["Ticker"].isin(CASH_LIKE)]
  cut_release = 0.0
  add_need = 0.0
  cut_names: List[str] = []
  for _, r in sleeve.iterrows():
    action, size, _ = _classify(r, ctx, sleeve_val)
    if action == "CUT":
      frac = 1.0 if ("100%" in size) else 0.5
      cut_release += float(r["Weight_Pct"]) * frac
      cut_names.append(str(r["Ticker"]))
    elif action in ("TRIM", "TRIM PRE-PRINT"):
      cut_release += float(r["Weight_Pct"]) * 0.25
    elif action == "ADD":
      m = re.search(r"\+([\d.]+)% book", size)
      add_need += float(m.group(1)) if m else 0.0

  core_combined = pd.concat([core, df[df["Ticker"].isin(CASH_LIKE)]
                            ]).drop_duplicates("Ticker")
  stocks_act_pct = float(stocks["Weight_Pct"].sum())
  stocks_slv_pct = float(stocks["Current_Value"].sum()) / sleeve_val * 100.0
  etfs_act_pct = float(sector_etfs["Weight_Pct"].sum())
  etfs_slv_pct = float(sector_etfs["Current_Value"].sum()) / sleeve_val * 100.0
  held_set = set(df["Ticker"].tolist())
  n_priority = (ctx["n_cut"] + ctx["n_trim"] + ctx["n_add"] +
                ctx["n_hold_print"])
  cut_str = ", ".join(f"`{t}`" for t in ctx.get("cut_tickers", [])) or "none"
  hp_str = (", ".join(f"`{t}`" for t in ctx.get("hold_print_tickers", [])) or
            "none")

  growth_w = sum(_w(t) for t in CORE_GROWTH)
  value_w = sum(_w(t) for t in CORE_VALUE)
  gv = growth_w / value_w if value_w else np.nan
  semi_w, semi_r = _tw("Semis & AI Hardware")
  core_w, core_r = _tw("Broad Index / Core")
  mega_w, mega_r = _tw("Megacap / Platforms")

  rs = sleeve.dropna(subset=["RS_3M_vs_SPY"]).sort_values("RS_3M_vs_SPY")
  rs_lead = ", ".join(f"`{r.Ticker} {r.RS_3M_vs_SPY:+.0f}`"
                      for r in rs.tail(5).iloc[::-1].itertuples())
  rs_lag = ", ".join(
      f"`{r.Ticker} {r.RS_3M_vs_SPY:+.0f}`" for r in rs.head(5).itertuples())
  contrib = df.dropna(
      subset=["Return_Contrib_Pct"]).sort_values("Return_Contrib_Pct")
  c_top = ", ".join(f"`{r.Ticker} {r.Return_Contrib_Pct:+.2f}`"
                    for r in contrib.tail(4).iloc[::-1].itertuples())
  c_bot = ", ".join(f"`{r.Ticker} {r.Return_Contrib_Pct:+.2f}`"
                    for r in contrib.head(4).itertuples())
  elig_ok = [t for t, why in leaders if why.startswith("✅")]

  md = f"""# 📊 Public Market Strategy & Model Portfolio — November 2, 2026
*Semiconductor (`SOXX`/`SMH`) & Hyperscaler (`GOOG`/`META`) Air-Pocket Playbook · Anonymized Proportions Only (`%` / `bps`)*

## ⚡ Executive TL;DR & This Week's Action Plan (Nov 2 – Nov 6, 2026)

- **Market Diagnosis (Mon Nov 2 Close):** `SOXX` fell **`-3.79%` 1D** to **`{soxx_b.get('Dist_to_200MA', np.nan):+.1f}%` vs 200DMA** (`RSI {soxx_b.get('RSI', np.nan):.1f}`) and `MRVL` plunged **`-12.72%`** (`-6.6%` vs 200DMA), but core AI monopolies **`SMH` (`{smh_b.get('Dist_to_200MA', np.nan):+.1f}%`), `NVDA` (`-1.0%`), and `TSM` (`-0.1%`) held their 200DMAs**, while `GOOG` (**RSI `{goog_b.get('RSI', np.nan):.1f}`**) and `META` (**RSI `{meta_b.get('RSI', np.nan):.1f}`**) hit 99th-percentile oversold capitulation (`RSI < 15`) and `VTI` (`+3.4%` vs 200DMA) held trend.
- **Macro Gate Status:** **Risk-Off Overlay = LATCHED ON** (`US10Y {ctx['us10y']:.2f}%`, `HY {ctx['hy']:.2f}%` / `{ctx['hy_chg']*100:+.0f}bp` 3M, `WTI ${macro.get('WTI_CRUDE', {}).get('value', np.nan):.2f}`). Tactical add units stay halved at **`{ctx['add_pct']:.2f}%` of book (`{ctx['add_sleeve_pct']:.2f}%` of sleeve)**; zero averaging down `>3%` below the 200DMA.
- **Rules Engine Verdict:** Place the **Semis Capitulation Exception on Friday Weekly-Close Watch (`$462.20` hard stop on `SOXX`)**, disqualify `MRVL` from Tranche 1 (`T1`), harvest tax losses on `<200DMA` laggards, and split `T1` (`20%` of fresh capital) into **10% Core Now / 10% Tactical on Thursday, Nov 5** after Midterms and `AMD`/`ANET` prints clear.

### 🎯 Immediate Action Matrix (Week of Nov 2 – Nov 6, 2026)

| Priority | Action | Tickers | Size (% Only) | Trigger & Timing |
| :--- | :--- | :--- | :--- | :--- |
| **1. Cut Laggards** | **CUT (50–100%)** | {cut_str} | Releases **`{cut_release:.2f}%` book** (`{cut_release/conc['tactical_pct']*100:.1f}%` slv) | `>3%` below 200DMA + lagging `SPY`; sell `COHR`/`RKLB`/`IREN` on 1st post-print close |
| **2. Trim Winner** | **TRIM (25%)** | `VHT` | `0.15%` book (`0.7%` slv) → `VMFXX` | Overbought defensive winner (`RSI 78.0`, `+21%` vintage) |
| **3. Deploy T1 Core** | **BUY CORE NOW** | `VTV` 50% / `VTI` 30% / `SCHD-VIG` 20% | **`10.0%` of Fresh Capital** (½ of T1) | Core Gate 1 = `NO` (`10Y 4.98% ≥ 4.75%`) & Gate 2 = `YES` (`VTI +3.4%` 200MA) |
| **4. Stage T1 Tactical** | **BUY LEADERS THU** | {', '.join(f'`{t}`' for t in elig_ok)} (`+CIBR`/`PANW`) | **`10.0%` of Fresh Capital** (`+{add_need:.2f}%` book) | **Execute Thu Nov 5** (`½` units) ONLY if `SMH`/`TSM`/`NVDA` hold 200DMA post-`AMD`/`ANET` |
| **5. Hold Capitulation** | **HOLD / FREEZE** | `GOOG`, `META`, `SOXX`, {hp_str} | `0%` change this week | Block panic sales at `RSI 8–13`; freeze `AAPL`/`AMD`/`ANET` inside 10d of prints; **Fri `SOXX < $462.20` = 20% trim** |

### 🏛️ Anonymized Two-Book Model Portfolio Snapshot (`100.0%` Total · {len(df)} Holdings)

| Model Portfolio Leg | Share of Book | Holdings | Vintage Ret % | YTD Ret % | Nov 2 (1D) | Active Governance Rule |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| **Core Index Ballast** (`VTI`/`VUG`/`VTV`/`VGT`/`VEA`/`SCHD`/`VIG`/`SCHB`) | **`{core_w:.1f}%`** | `8` | `{core_r:+.1f}%` | — | — | **Gate 1 NO / Gate 2 YES:** Route 100% new flows to `VTV`/`VTI`/`SCHD`/`VIG` (`G/V {gv:.2f}x`) |
| **Liquid Cash Reserves** (`VMFXX` + `VUSB` @ `~4.0%` yield) | **`{ctx['cash_pct']:.1f}%`** | `2` | `+0.0%` | — | `+0.00%` | **Gate 3 YES:** 3 tranches × `{ctx['tranche_pct']:.2f}%` book; max 1 tranche live while Gate ON |
| **Tactical Sleeve** ({len(stocks)} Stocks `{stocks_act_pct:.1f}%` + {len(sector_etfs)} ETFs `{etfs_act_pct:.1f}%`) | **`{conc['tactical_pct']:.1f}%`** | `{conc['n_tactical']}` | `{tact_ret:+.1f}%` | `{tact_last:+.1f}%` | — | **Risk-Off Gate ON:** `½` add units (`{ctx['add_pct']:.2f}%` book); Sleeve `HHI {conc['hhi_tactical']:.0f}`; Semis `{semi_w:.1f}%` book |
| **Full Model Portfolio (80% Core / 20% Tactical)** | **`100.0%`** | **`{len(df)}`** | **`{total_pnl_pct:+.1f}%`** | **`{last['Portfolio']:+.1f}%`** | **`{day_pct:+.2f}%`** | Rolling 60D Beta vs `QQQ`: **`{ctx['port_beta']:.2f}`** (`SOXX -3.8%` 1D cushioned to `-0.51%`) |

---

## 📈 1. Benchmark Performance & Semis / Hyperscaler Dip Audit

![Equity Curve](plots/{TAG}_equity_curve_vs_benchmarks.png)
*💡 **Performance**: Full Model Book is **`{last['Portfolio']:+.1f}%` YTD** (`{day_pct:+.2f}%` on Nov 2) and Tactical Sleeve is **`{tact_last:+.1f}%` YTD** vs `QQQ {last['QQQ']:+.1f}%` and `SOXX {last['SOXX']:+.1f}%` (`-23.0%` 1M).*

{bench_tbl}

![Relative Strength](plots/{TAG}_relative_strength.png)
*💡 **3M Relative Strength vs `SPY`**: Right-tail leaders ({rs_lead}) hold trend; left-tail `<200DMA` laggards ({rs_lag}) are assigned `CUT` rules.*

![Rolling Beta](plots/{TAG}_rolling_beta.png)
*💡 **Risk Dampening**: 60-day portfolio beta to `QQQ` is **`{ctx['port_beta']:.2f}`**, cushioned by counter-cyclical inflows into `VTV`, `SCHD`, `VHT`, and `VPU`.*

### 🔬 Why Semis & Hyperscalers Sold Off — And How the Rules Separate Winners from Traps

- **Hyperscaler Dispersion (`GOOG` & `META` vs. `MSFT` & `AMZN`):** Investors are penalizing ad-funded AI capex where FCF margins compress (`GOOG` RSI `12.7`, `-17.8%` vs 200DMA; `META` RSI `8.2`, `-3.9%` vs 200DMA) while rewarding enterprise cloud backlog (`MSFT +16.0%` vs 200DMA; `AMZN +2.2%` 1D, `+0.9%` vs 200DMA, AWS `+39%`). **Rule:** Hold `GOOG`/`META` (`RSI < 15` blocks panic selling), but route new platform adds strictly to `MSFT`/`AMZN` (`>200DMA`) or `VGT`/`VUG` core once `10Y < 4.75%`.
- **Semiconductor Bifurcation (`SMH`/`NVDA`/`TSM` vs. `MRVL`/`WDC`/`COHR`):** Every dollar of hyperscaler capex flows into `TSM` (`-0.1%` vs 200DMA, `+68%` IV disc) and `NVDA` (`-1.0%` vs 200DMA), which held their 200DMAs today alongside `SMH` (`-2.3%`). High-beta ASIC/memory/optics (`MRVL -12.7%` 1D to `-6.6%` vs 200DMA, `WDC -19.3%`, `COHR -32.6%`) broke trend. **Rule:** Disqualify `MRVL` from `T1` adds, cut `WDC`/`COHR`/`DRAM`/`XSD` `50%`, and concentrate Thu `T1` semi adds in `TSM` / `SMH` / `NVDA`.

{semis_hyperscaler_audit_table(df)}

---

## 📡 2. Trigger Scorecard, Macro Regime & Hypothesis Playbook

### 🎯 Strategy Trigger Scorecard ({n_fired} of {len(scorecard)} Fired)

{scorecard_md(scorecard)}

### 🌐 Key Macro Indicators (Thru Nov 2, 2026)

{macro_table(macro)}

### 🧠 Core Hypotheses, Contrarian Alternatives & Scenario Matrix

{hypotheses_and_contingencies_md(df, macro, ctx, last)}

### 🐂🐻 Bull / Bear Synthesis & Rule Evolution (`11-01` → `11-02`)

{bull_bear_md(df, macro, ctx, last)}

{tree_evolution_md()}

---

## 🚀 3. Tactical Sleeve (`{conc['tactical_pct']:.1f}%` of Book · {conc['n_tactical']} Holdings)

### 3.1 Tactical Decision Tree (Regime Gate + 5 Pillars)

![Decision Tree](plots/{TAG}_decision_tree.png)
*💡 **Live Path**: Macro Gate **ON** (`½` units) · **P1**: `NO (Capitulation Watch — Fri SOXX $462.20 stop)` · **P2**: `NO (Value tilt)` · **P3**: `NO (Hold VPU, cut NLR/CCJ)` · **P4**: `PENDING (Cut AIPO 50%)` · **P5**: `PARTIAL (Hold IBIT, cut IREN/BMNR)`.*

{pillar_tbl}

### 3.2 Theme Exposure, Technical Map, Attribution & Correlation

![Theme Exposure](plots/{TAG}_theme_exposure.png)
*💡 **Themes**: Core Index (`{core_w:.1f}%`) + Cash (`{ctx['cash_pct']:.1f}%`) = `80.0%` Ballast; Semis (`{semi_w:.1f}%` book, `{semi_r:+.1f}%` vintage) + Megacap (`{mega_w:.1f}%` book, `{mega_r:+.1f}%` vintage) drive tactical growth.*

![Drawdown vs RSI Bubble](plots/{TAG}_drawdown_vs_rsi.png)
*💡 **200DMA Filter**: Oversold leaders on their 200DMA (`TSM`, `NVDA`, `SMH`, `MSFT`, `AMZN`) are `ADD`s; deep `<200DMA` breakdowns (`IREN`, `RKLB`, `WDC`, `COHR`, `NLR`, `CCJ`) are `CUT`s.*

![PnL Contribution](plots/{TAG}_pnl_contribution.png)
*💡 **Attribution**: Top vintage contributors ({c_top}) vs `<200DMA` drags ({c_bot}) slated for tax-loss harvesting.*

![Correlation Heatmap](plots/{TAG}_correlation_heatmap.png)
*💡 **Correlation**: `SMH`/`SOXX`/`TSM`/`NVDA` correlate at `0.78–0.92` (consolidate new ETF adds into `SMH`); `VTV`/`SCHD`/`VPU`/`VHT` provide true diversification.*

### 3.3 Priority Tactical Action Queue ({n_priority} Active Orders)

Self-funding rebalance: `CUT` + `TRIM` orders release **`{cut_release:.2f}%` of model book**, funding **`{add_need:.2f}%` of book** in `ADD`s.

{priority_actions_table(df, ctx)}

### 3.4 Individual Tactical Equities ({len(stocks)} Holdings · `{stocks_act_pct:.1f}%` Book / `{stocks_slv_pct:.1f}%` Sleeve)

{unified_stocks_table(stocks, ctx, sleeve_val)}

### 3.5 Thematic & Sector ETFs ({len(sector_etfs)} Holdings · `{etfs_act_pct:.1f}%` Book / `{etfs_slv_pct:.1f}%` Sleeve)

{unified_etfs_table(sector_etfs, ctx, sleeve_val)}

### 3.6 Earnings Calendar & Binary Catalyst Rules

![Earnings Timeline](plots/{TAG}_earnings_timeline.png)
*💡 **Catalyst Wall**: `AAPL` (11/2), `AMD` & `ANET` (11/3 + Midterms), `QCOM` & `ARM` (11/4), NFP (11/6), CPI (11/10), `NVDA` (11/17). Zero adds ≤ 10 sessions pre-print.*

{earnings_playbook(earn, df, ctx)}

#### Ecosystem Bellwethers (Non-Held Read-Throughs)

{bellwether_earnings_table(held_set)}

### 3.7 AI Mega-IPO Pipeline (`Anthropic 'ANT'` S-1)

{ipo_md}

---

## 🏦 4. Core Ballast (`{core_pct:.1f}%` of Book · {len(core_combined)} Holdings)

### 4.1 Core Ballast Decision Tree (3 Sequential Gates)

![Index Tree](plots/{TAG}_index_tree.png)
*💡 **Live Gates**: **G1 Duration = NO** (`10Y 4.98% ≥ 4.75%` → 100% new flows to `VTV`/`VTI`/`SCHD`/`VIG`) · **G2 Trend = YES** (`VTI +3.4%` vs 200DMA → keep DCA) · **G3 Liquidity = YES** (`Cash {ctx['cash_pct']:.1f}% ≥ 6.0%`).*

### 4.2 Core Index & Cash Holdings Table

{core_ballast_table(core_combined, core_val)}

---

## 💵 5. Phased Fresh-Capital Plan (`100%` New Money · 5 Conditional Tranches)

### 5.1 Fresh-Capital Deployment Decision Tree (`20 / 20 / 25 / 20 / 15%`)

![Deployment Tree](plots/{TAG}_deployment_tree.png)
*💡 **T1 Split Execution**: Deploy **T1 Core (`10%` fresh capital into `VTV 50% / VTI 30% / SCHD-VIG 20%`) now**; gate **T1 Tactical (`10%` into `TSM 35% / SMH 35% / NVDA-MSFT 30%`) until Thursday, Nov 5** after Midterms and `AMD`/`ANET` clear.*

### 5.2 Tranche Execution Schedule & Fallback Rules

{deployment_table_md(plan)}

### 5.3 Tax-Wrapper Routing & Expected Outcomes Matrix

{wrapper_routing_md()}

| Macro Path (Prob) | Mid-Dec Signal | Fresh-Capital Outcome | Edge vs Lump-Sum Today |
| :--- | :--- | :--- | :--- |
| **A: Positioning Washout (~50%)** | `AMD`/`ANET`/`NVDA` hold guides; `SOXX > 200MA` | `85%` deployed (T1–T4); `15%` T5 in `VMFXX` | Captures 200DMA rebound, avoids `<200MA` traps (`MRVL`/`WDC`) |
| **B: Capex Digestion (~25%)** | Fri `SOXX < $462.20` (`-3%` 200MA); flat `NVDA` | `50%` deployed (`100%` Core `VTV`/`VTI`); Semis roll to T5 | **`+400–700 bps` alpha**: avoids `-15%` second leg in semis |
| **C: Stagflation Shock (~15%)** | Hot CPI, `WTI > $105`, `10Y > 5.25%` | `40%` deployed (`VTV`/`SCHD` only); `60%` in `VMFXX` | Preserves principal during multiple compression |
| **D: Duration Relief (~10%)** | `10Y < 4.75%` & `HY < 3.0%` post-FOMC | `100%` deployed; T4 unlocks `VUG`/`VGT` growth core | Participates via T1+T2 (`40%`) + `93.4%` invested Model Book |

---

## 🤖 6. Red-Team Risk Audit & Live News Digest

### 6.1 Chief Risk Officer Critique & Adopted Safeguards

{critique_md}

### 6.2 Key Market & Sector Headlines (Thru Nov 2, 2026)

{news_md}

---

*Generated on {datetime.datetime.now():%Y-%m-%d %H:%M} from `market_data/` pipelines (closes through `{spy_last_date}`). All weights, attribution figures, and trade sizes are expressed strictly as percentages (`%`) or basis points (`bps`) of the anonymized model portfolio or fresh-capital allocation. Not personalized investment advice.*
"""
  return md


def main() -> None:
  """Main entry point for the November 2, 2026 public strategy report."""
  os.makedirs(PLOTS_DIR, exist_ok=True)
  agg, wrappers = build_model_portfolio()
  df = enrich(agg)
  logger.info("Enriched %d model portfolio tickers", len(df))

  curve = frozen_weight_curve(df)
  beta = portfolio_rolling_beta(df)
  macro = load_macro()
  soxx = df[df["Ticker"] == "SOXX"]
  soxx_rsi = float(soxx["RSI"].iloc[0]) if not soxx.empty else np.nan
  if np.isnan(soxx_rsi):
    soxx_px = load_prices("SOXX")
    if soxx_px is not None:
      soxx_rsi = calculate_technical_metrics(soxx_px)["RSI"]

  total_val = float(df["Current_Value"].sum())
  cash_val = float(df[df["Ticker"].isin(CASH_LIKE)]["Current_Value"].sum())
  cash_pct = cash_val / total_val * 100.0
  conc = concentration_stats(df)
  hy_chg = macro.get("HY_SPREAD", {}).get("chg_3m", np.nan)
  us10y = macro.get("US10Y", {}).get("value", np.nan)
  gate_trip = bool(us10y >= 5.0 and hy_chg >= 0.25)
  gate_release = bool(us10y < 4.75 and hy_chg < 0.25)
  risk_off = gate_trip or (PREV_GATE_ON and not gate_release)

  tranche_val = cash_val / 3.0
  tranche_pct = cash_pct / 3.0
  add_val = tranche_val / 4.0 * (0.5 if risk_off else 1.0)
  add_pct = tranche_pct / 4.0 * (0.5 if risk_off else 1.0)
  add_sleeve_pct = add_val / conc["tactical_val"] * 100.0

  ctx: Dict[str, Any] = {
      "soxx_rsi": soxx_rsi,
      "us10y": us10y,
      "hy": macro.get("HY_SPREAD", {}).get("value", np.nan),
      "hy_chg": hy_chg,
      "risk_off": risk_off,
      "cash_val": cash_val,
      "cash_pct": cash_pct,
      "tranche": tranche_val,
      "tranche_pct": tranche_pct,
      "add_size": add_val,
      "add_pct": add_pct,
      "add_sleeve_pct": add_sleeve_pct,
      "port_beta": float(beta.iloc[-1]),
      "semi_pct": df[df["Theme"] == "Semis & AI Hardware"]["Weight_Pct"].sum(),
      "qqq_ytd": df.attrs["bench_ret"]["QQQ"]["YTD"],
      "tactical_val": conc["tactical_val"],
      "tactical_pct": conc["tactical_pct"],
      "n_tactical": conc["n_tactical"],
      "core_val": total_val - conc["tactical_val"],
  }

  sleeve = df[~df["Theme"].isin(CORE_THEMES) & ~df["Ticker"].isin(CASH_LIKE)]
  sleeve_sum = float(sleeve["Current_Value"].sum())
  classified = [(str(r["Ticker"]), _classify(r, ctx, sleeve_sum)[0])
                for _, r in sleeve.iterrows()]
  acts = [a for _, a in classified]
  ctx.update({
      "n_cut":
          acts.count("CUT"),
      "n_trim":
          acts.count("TRIM") + acts.count("TRIM PRE-PRINT"),
      "n_add":
          acts.count("ADD"),
      "n_hold_print":
          acts.count("HOLD-THRU-PRINT"),
      "cut_tickers": [t for t, a in classified if a == "CUT"],
      "trim_tickers": [
          t for t, a in classified if a in ("TRIM", "TRIM PRE-PRINT")
      ],
      "add_tickers": [t for t, a in classified if a == "ADD"],
      "hold_print_tickers": [
          t for t, a in classified if a == "HOLD-THRU-PRINT"
      ],
  })

  pillars = build_pillars(df, macro, ctx)
  gates = build_index_gates(df, macro, ctx)

  plot_equity_curve(
      curve, os.path.join(PLOTS_DIR, f"{TAG}_equity_curve_vs_benchmarks.png"))
  plot_relative_strength(
      df, os.path.join(PLOTS_DIR, f"{TAG}_relative_strength.png"))
  plot_pnl_contribution(df,
                        os.path.join(PLOTS_DIR, f"{TAG}_pnl_contribution.png"))
  plot_drawdown_bubble(df, os.path.join(PLOTS_DIR,
                                        f"{TAG}_drawdown_vs_rsi.png"))
  plot_theme_exposure(df, os.path.join(PLOTS_DIR, f"{TAG}_theme_exposure.png"))
  earn = plot_earnings_timeline(
      df, os.path.join(PLOTS_DIR, f"{TAG}_earnings_timeline.png"))
  plot_rolling_beta(beta, os.path.join(PLOTS_DIR, f"{TAG}_rolling_beta.png"))
  top20 = df[~df["Ticker"].isin(CASH_LIKE)].head(20)["Ticker"].tolist()
  plot_correlation_heatmap(
      top20,
      TICKERS_DIR,
      os.path.join(PLOTS_DIR, f"{TAG}_correlation_heatmap.png"),
  )
  create_decision_tree(os.path.join(PLOTS_DIR, f"{TAG}_decision_tree"), pillars,
                       ctx)
  create_index_tree(os.path.join(PLOTS_DIR, f"{TAG}_index_tree"), gates, ctx)

  ctx["scorecard"] = trigger_scorecard(df, macro, ctx)
  ctx["bell"] = {
      t: tech_of(t) for t in (
          "SOXX",
          "SMH",
          "SPY",
          "QQQ",
          "VTI",
          "NVDA",
          "GOOG",
          "AMD",
          "TSM",
          "AVGO",
          "MSFT",
          "META",
          "AMZN",
          "IBIT",
          "VTV",
          "VUG",
          "VEA",
          "MRVL",
          "ANET",
          "AAPL",
      )
  }
  leaders = _eligible_leaders(df)
  plan = build_deployment_plan(df, macro, ctx)
  ctx["plan"] = plan
  ctx["leaders"] = leaders
  create_deployment_tree(os.path.join(PLOTS_DIR, f"{TAG}_deployment_tree"),
                         plan, ctx, leaders)

  ipo_md = ai_ipo_digest(max_items=5)
  key_news = [
      "TSM",
      "AMD",
      "AVGO",
      "NVDA",
      "ANET",
      "GOOG",
      "META",
      "MSFT",
      "AMZN",
      "AAPL",
      "NLR",
      "IBIT",
      "COHR",
      "WDC",
  ]
  news_md = format_recent_news_markdown(
      topics={
          "Semiconductor Fabs": "Fabs",
          "Memory Shortage": "Memory",
          "Hyperscalers": "Hyperscalers",
          "Federal Reserve": "Fed",
          "AI Agents": "AI",
      },
      market_data_dir=MARKET_DATA_DIR,
      tickers=key_news,
      max_items=24,
  )
  news_lines = [
      line for line in news_md.splitlines()
      if line.strip() and not NEWS_JUNK.search(line)
  ][:8]
  news_md = "\n".join(news_lines) if news_lines else "*No recent news.*"

  critique_md = default_critique_md(ctx)
  report = compile_report(
      df,
      wrappers,
      macro,
      curve,
      earn,
      ctx,
      ipo_md,
      news_md,
      critique_md,
      pillars,
      gates,
  )
  out = os.path.join(SCRIPT_DIR, "REPORT.md")
  with open(out, "w", encoding="utf-8") as f:
    f.write(clean_md(report))
  export_df = df.drop(
      columns=[
          "Current_Value",
          "Cost_Basis",
          "Unrealized_PnL_Net",
          "Day_Change_Net",
      ],
      errors="ignore",
  )
  export_df.to_csv(
      os.path.join(SCRIPT_DIR, "model_holdings_metrics.tsv"),
      sep="\t",
      index=False,
  )
  logger.info("✅ Wrote %s", out)
  try:
    render_markdown_to_pdf(out)
  except Exception as exc:  # pylint: disable=broad-except
    logger.warning("PDF render failed: %s", exc)


if __name__ == "__main__":
  main()
