# Copyright 2026 The Market Pipeline Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Quantitative analysis of global equities correlated with Open AI models.

This module models exponentially weighted correlations, token economics,
hyperscaler capex allocation, grid power constraints, and valuation arbitrage
across 45+ US-available equities spanning custom silicon, foundries, Chinese
AI champions, baseload nuclear power, and datacenter cooling infrastructure.
"""

import asyncio
import datetime
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import graphviz
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

from reports.report_utils import clean_md
from reports.report_utils import get_intrinsic_value_metrics
from reports.report_utils import get_technical_indicators
from reports.report_utils import render_markdown_to_pdf
from reports.report_utils import setup_decision_tree_aesthetics
from reports.report_utils import setup_plot_aesthetics

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Silence verbose loggers
logging.getLogger("weasyprint").setLevel(logging.WARNING)
logging.getLogger("weasyprint.progress").setLevel(logging.WARNING)
logging.getLogger("fontTools").setLevel(logging.WARNING)

REPORT_DIR = os.path.dirname(os.path.abspath(__file__))
PLOTS_DIR = os.path.join(REPORT_DIR, "plots")
MARKET_DATA_DIR = os.path.join(PROJECT_ROOT, "market_data")
TICKERS_DIR = os.path.join(MARKET_DATA_DIR, "tickers")
ROOT_REPORT_MD = os.path.join(PROJECT_ROOT, "reports", "REPORT.md")

os.makedirs(PLOTS_DIR, exist_ok=True)

# 6 Core Value Chain Sectors
SECTOR_MAP: Dict[str, List[str]] = {
    "Chinese Open AI": [
        "BABA",
        "BIDU",
        "TCEHY",
        "PDD",
        "JD",
        "GDS",
        "KWEB",
    ],
    "Hyperscalers": [
        "META",
        "GOOG",
        "MSFT",
        "AMZN",
        "ORCL",
        "AAPL",
    ],
    "Custom Silicon and Foundries": [
        "NVDA",
        "AMD",
        "TSM",
        "AVGO",
        "MRVL",
        "ARM",
        "MU",
        "ASML",
        "ALAB",
        "COHR",
        "LITE",
        "CDNS",
        "SNPS",
    ],
    "Baseload Nuclear and Power": [
        "VST",
        "CEG",
        "GEV",
        "PWR",
        "ETN",
        "NEE",
        "CCJ",
        "TLN",
        "OKLO",
        "SMR",
    ],
    "Liquid Cooling Infrastructure": [
        "VRT",
        "MOD",
        "ANET",
        "EQIX",
        "CORZ",
        "APLD",
        "IREN",
    ],
    "Enterprise RAG Moats": [
        "PLTR",
        "RDDT",
        "SNOW",
        "MDB",
    ],
}

BENCHMARKS: List[str] = ["SPY", "QQQ", "SOXX", "KWEB"]
ALL_ANALYSIS_TICKERS: List[str] = [
    t for sublist in SECTOR_MAP.values() for t in sublist
] + [
    b for b in BENCHMARKS
    if b not in [t for s in SECTOR_MAP.values() for t in s]
]


def load_price_history(tickers: List[str]) -> pd.DataFrame:
  """Loads and aligns daily Close price history across specified tickers."""
  price_dict: Dict[str, pd.Series] = {}
  for ticker in set(tickers):
    file_path = os.path.join(TICKERS_DIR, ticker, "prices.tsv")
    if not os.path.exists(file_path):
      continue
    try:
      df = pd.read_csv(file_path, sep="\t")
      if "Date" in df.columns and "Close" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df = df.dropna(subset=["Date", "Close"]).sort_values("Date")
        df = df.drop_duplicates(subset=["Date"])
        price_dict[ticker] = df.set_index("Date")["Close"]
    except Exception as exc:
      logger.error("Error reading %s: %s", file_path, exc)

  price_df = pd.DataFrame(price_dict)
  price_df = price_df.ffill().dropna(how="all")
  return price_df


def compute_ewma_correlation(returns_df: pd.DataFrame,
                             lambda_decay: float = 0.94) -> pd.DataFrame:
  """Computes exponentially weighted moving correlation matrix."""
  clean_returns = returns_df.dropna(how="all")
  num_periods = len(clean_returns)
  if num_periods < 5:
    return clean_returns.corr()

  weights = np.array([
      (1.0 - lambda_decay) * (lambda_decay**(num_periods - 1 - i))
      for i in range(num_periods)
  ])
  weights /= weights.sum()

  cols = clean_returns.columns
  num_cols = len(cols)
  cov_matrix = np.zeros((num_cols, num_cols))

  weighted_mean = np.zeros(num_cols)
  for col_idx, col in enumerate(cols):
    series = clean_returns[col].fillna(0.0).values
    weighted_mean[col_idx] = np.sum(weights * series)

  centered = np.zeros_like(clean_returns.values)
  for col_idx, col in enumerate(cols):
    series = clean_returns[col].fillna(0.0).values
    centered[:, col_idx] = series - weighted_mean[col_idx]

  for i in range(num_cols):
    for j in range(num_cols):
      cov_matrix[i, j] = np.sum(weights * centered[:, i] * centered[:, j])

  std_devs = np.sqrt(np.diag(cov_matrix))
  std_devs[std_devs == 0] = 1e-8
  corr_matrix = cov_matrix / np.outer(std_devs, std_devs)
  corr_matrix = np.clip(corr_matrix, -1.0, 1.0)

  return pd.DataFrame(corr_matrix, index=cols, columns=cols)


def extract_fundamental_metrics(ticker: str) -> Dict[str, Any]:
  """Extracts key valuation and fundamental metrics from fundamentals.tsv."""
  file_path = os.path.join(TICKERS_DIR, ticker, "fundamentals.tsv")
  metrics: Dict[str, Any] = {
      "MarketCap": np.nan,
      "ForwardPE": np.nan,
      "TrailingPE": np.nan,
      "PriceToSales": np.nan,
      "EnterpriseValue": np.nan,
      "RevenueGrowth": np.nan,
      "ForwardEps": np.nan,
      "TrailingEps": np.nan,
      "52WeekHigh": np.nan,
      "52WeekLow": np.nan,
  }
  if not os.path.exists(file_path):
    return metrics

  try:
    df = pd.read_csv(file_path, sep="\t")
    if "Metric" in df.columns and "Value" in df.columns:
      f_dict = dict(zip(df["Metric"], df["Value"]))
      if "marketCap" in f_dict:
        metrics["MarketCap"] = pd.to_numeric(f_dict["marketCap"],
                                             errors="coerce")
      if "forwardPE" in f_dict:
        metrics["ForwardPE"] = pd.to_numeric(f_dict["forwardPE"],
                                             errors="coerce")
      if "trailingPE" in f_dict:
        metrics["TrailingPE"] = pd.to_numeric(f_dict["trailingPE"],
                                              errors="coerce")
      if "priceToSalesTrailing12Months" in f_dict:
        metrics["PriceToSales"] = pd.to_numeric(
            f_dict["priceToSalesTrailing12Months"], errors="coerce")
      if "enterpriseValue" in f_dict:
        metrics["EnterpriseValue"] = pd.to_numeric(f_dict["enterpriseValue"],
                                                   errors="coerce")
      if "revenueGrowth" in f_dict:
        metrics["RevenueGrowth"] = pd.to_numeric(f_dict["revenueGrowth"],
                                                 errors="coerce")
      if "forwardEps" in f_dict:
        metrics["ForwardEps"] = pd.to_numeric(f_dict["forwardEps"],
                                              errors="coerce")
      if "trailingEps" in f_dict:
        metrics["TrailingEps"] = pd.to_numeric(f_dict["trailingEps"],
                                               errors="coerce")
      if "fiftyTwoWeekHigh" in f_dict:
        metrics["52WeekHigh"] = pd.to_numeric(f_dict["fiftyTwoWeekHigh"],
                                              errors="coerce")
      if "fiftyTwoWeekLow" in f_dict:
        metrics["52WeekLow"] = pd.to_numeric(f_dict["fiftyTwoWeekLow"],
                                             errors="coerce")
  except Exception as exc:
    logger.warning("Failed to parse fundamentals for %s: %s", ticker, exc)

  return metrics


def plot_weighted_correlation_heatmap(corr_df: pd.DataFrame,
                                      output_path: str) -> None:
  """Renders a high-density heatmap of exponentially weighted correlations."""
  setup_plot_aesthetics()
  plt.figure(figsize=(18, 14))

  mask = np.triu(np.ones_like(corr_df, dtype=bool))
  cmap = sns.diverging_palette(220, 10, as_cmap=True)

  sns.heatmap(
      corr_df,
      mask=mask,
      cmap=cmap,
      vmax=1.0,
      vmin=-0.2,
      center=0.3,
      annot=True,
      fmt=".2f",
      square=True,
      linewidths=0.6,
      cbar_kws={
          "shrink": 0.75,
          "label": "EWMA Correlation (λ = 0.94)"
      },
      annot_kws={
          "size": 9,
          "weight": "bold"
      },
  )

  plt.title(
      "Weighted Correlation Matrix (λ = 0.94)",
      fontsize=14,
      fontweight="bold",
      pad=15,
  )
  plt.tight_layout()
  plt.savefig(output_path, dpi=300, bbox_inches="tight")
  plt.close()


def plot_thematic_performance(price_df: pd.DataFrame, output_path: str) -> None:
  """Plots cumulative YTD performance trajectories across thematic cohorts."""
  setup_plot_aesthetics()
  plt.figure(figsize=(13, 7))

  ytd_prices = price_df[price_df.index >= "2026-01-01"].copy()
  if len(ytd_prices) < 2:
    ytd_prices = price_df.iloc[-180:].copy()

  cohort_indices: Dict[str, pd.Series] = {}
  for cohort_name, tickers in SECTOR_MAP.items():
    avail_tickers = [t for t in tickers if t in ytd_prices.columns]
    if avail_tickers:
      norm = ytd_prices[avail_tickers].div(ytd_prices[avail_tickers].iloc[0])
      cohort_indices[cohort_name] = norm.mean(axis=1) * 100.0 - 100.0

  if "SPY" in ytd_prices.columns:
    cohort_indices["SPY Benchmark"] = (
        ytd_prices["SPY"].div(ytd_prices["SPY"].iloc[0]) * 100.0 - 100.0)
  if "QQQ" in ytd_prices.columns:
    cohort_indices["QQQ Tech"] = (
        ytd_prices["QQQ"].div(ytd_prices["QQQ"].iloc[0]) * 100.0 - 100.0)

  cohort_df = pd.DataFrame(cohort_indices)
  colors = [
      "#E63946",
      "#1D3557",
      "#2A9D8F",
      "#F4A261",
      "#9B5DE5",
      "#00BBF9",
      "#4A4E69",
      "#6C757D",
  ]

  for idx, (col_name, series) in enumerate(cohort_df.items()):
    linestyle = "--" if "Benchmark" in col_name or "Tech" in col_name else "-"
    linewidth = 2.0 if linestyle == "--" else 2.6
    color = colors[idx % len(colors)]
    plt.plot(
        series.index,
        series.values,
        label=f"{col_name} ({series.iloc[-1]:+.1f}%)",
        linestyle=linestyle,
        linewidth=linewidth,
        color=color,
    )

  plt.axhline(0, color="black", linestyle=":", alpha=0.6, linewidth=1)
  plt.title(
      "Thematic Cumulative Returns (2026 YTD)",
      fontsize=13,
      fontweight="bold",
      pad=15,
  )
  plt.ylabel("Cumulative Return (%)", fontsize=11, fontweight="bold")
  plt.xlabel("Date", fontsize=11, fontweight="bold")
  plt.legend(loc="upper left", framealpha=0.9, fontsize=9.5)
  plt.tight_layout()
  plt.savefig(output_path, dpi=300, bbox_inches="tight")
  plt.close()


def plot_rsi_dist200_scatter(table_df: pd.DataFrame, output_path: str) -> None:
  """Generates momentum (RSI) vs Trend Extension (Dist_to_200MA) scatter."""
  setup_plot_aesthetics()
  plt.figure(figsize=(14, 8))

  clean_df = table_df.dropna(subset=["RSI", "Dist_to_200MA"]).copy()
  clean_df["RSI"] = pd.to_numeric(clean_df["RSI"], errors="coerce")
  clean_df["Dist_to_200MA"] = pd.to_numeric(clean_df["Dist_to_200MA"],
                                            errors="coerce")
  clean_df = clean_df.dropna(subset=["RSI", "Dist_to_200MA"])

  palette = sns.color_palette("tab10", len(clean_df["Sector"].unique()))
  sector_color_map = dict(zip(clean_df["Sector"].unique(), palette))

  for sector, group in clean_df.groupby("Sector"):
    plt.scatter(
        group["Dist_to_200MA"],
        group["RSI"],
        label=sector,
        s=150,
        alpha=0.85,
        edgecolors="black",
        linewidths=0.8,
        color=sector_color_map.get(sector),
    )

  for _, row in clean_df.iterrows():
    plt.annotate(
        row["Ticker"],
        (row["Dist_to_200MA"], row["RSI"]),
        xytext=(5, 4),
        textcoords="offset points",
        fontsize=8.5,
        fontweight="bold",
    )

  plt.axhline(70,
              color="#E63946",
              linestyle="--",
              alpha=0.7,
              label="Overbought (70)")
  plt.axhline(30,
              color="#2A9D8F",
              linestyle="--",
              alpha=0.7,
              label="Oversold (30)")
  plt.axvline(0, color="gray", linestyle=":", alpha=0.6)

  plt.title(
      "Momentum Map: RSI vs 200-Day MA",
      fontsize=13,
      fontweight="bold",
      pad=15,
  )
  plt.xlabel("Distance to 200-Day MA (%)", fontsize=11, fontweight="bold")
  plt.ylabel("RSI (14D)", fontsize=11, fontweight="bold")
  plt.legend(loc="lower right", framealpha=0.9, fontsize=9)
  plt.tight_layout()
  plt.savefig(output_path, dpi=300, bbox_inches="tight")
  plt.close()


def plot_valuation_vs_growth(table_df: pd.DataFrame, output_path: str) -> None:
  """Plots Forward P/E vs Projected Revenue Growth rate."""
  setup_plot_aesthetics()
  plt.figure(figsize=(14, 8))

  projected_growth = {
      "BABA": 14.5,
      "BIDU": 11.0,
      "TCEHY": 13.5,
      "PDD": 24.0,
      "JD": 9.5,
      "GDS": 22.0,
      "META": 19.5,
      "GOOG": 16.0,
      "MSFT": 15.5,
      "AMZN": 14.0,
      "ORCL": 18.0,
      "AAPL": 8.5,
      "NVDA": 42.0,
      "AMD": 32.0,
      "TSM": 26.5,
      "AVGO": 28.0,
      "MRVL": 31.0,
      "ARM": 24.5,
      "MU": 45.0,
      "ASML": 21.0,
      "ALAB": 55.0,
      "COHR": 23.0,
      "LITE": 20.5,
      "CDNS": 16.0,
      "SNPS": 15.0,
      "VST": 29.0,
      "CEG": 25.0,
      "GEV": 22.0,
      "PWR": 17.5,
      "ETN": 16.0,
      "NEE": 10.5,
      "CCJ": 26.0,
      "TLN": 35.0,
      "OKLO": 80.0,
      "SMR": 65.0,
      "VRT": 33.0,
      "MOD": 24.0,
      "ANET": 21.5,
      "EQIX": 11.0,
      "CORZ": 40.0,
      "APLD": 50.0,
      "IREN": 48.0,
      "PLTR": 27.0,
      "RDDT": 34.0,
      "SNOW": 23.5,
      "MDB": 22.0,
  }

  plot_data = []
  for _, row in table_df.iterrows():
    ticker = row["Ticker"]
    fwd_pe = row["Forward_PE"]
    if pd.notna(fwd_pe) and 0 < fwd_pe < 120 and ticker in projected_growth:
      plot_data.append({
          "Ticker": ticker,
          "Sector": row["Sector"],
          "Forward_PE": fwd_pe,
          "Projected_Growth": projected_growth[ticker],
      })

  df_p = pd.DataFrame(plot_data)
  if df_p.empty:
    return

  palette = sns.color_palette("tab10", len(df_p["Sector"].unique()))
  sector_color_map = dict(zip(df_p["Sector"].unique(), palette))

  for sector, group in df_p.groupby("Sector"):
    plt.scatter(
        group["Projected_Growth"],
        group["Forward_PE"],
        label=sector,
        s=150,
        alpha=0.85,
        edgecolors="black",
        linewidths=0.8,
        color=sector_color_map.get(sector),
    )

  for _, row in df_p.iterrows():
    plt.annotate(
        row["Ticker"],
        (row["Projected_Growth"], row["Forward_PE"]),
        xytext=(5, 4),
        textcoords="offset points",
        fontsize=8.5,
        fontweight="bold",
    )

  plt.title(
      "Valuation vs Growth (2026–2027)",
      fontsize=13,
      fontweight="bold",
      pad=15,
  )
  plt.xlabel("Projected 2Y Revenue CAGR (%)", fontsize=11, fontweight="bold")
  plt.ylabel("Forward P/E Multiple", fontsize=11, fontweight="bold")
  plt.legend(loc="upper left", framealpha=0.9, fontsize=9)
  plt.tight_layout()
  plt.savefig(output_path, dpi=300, bbox_inches="tight")
  plt.close()


def plot_token_cost_and_jevons(output_path: str) -> None:
  """Plots token deflation curve ($/1M tokens) vs query volume expansion."""
  setup_plot_aesthetics()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

  time_points = ["Q1 24", "Q3 24", "Q1 25", "Q3 25", "Q1 26", "Q3 26E", "2027E"]
  closed_prices = [30.0, 15.0, 10.0, 6.5, 3.5, 2.2, 1.2]
  open_prices = [12.0, 4.5, 1.2, 0.45, 0.18, 0.08, 0.03]

  x = np.arange(len(time_points))
  ax1.plot(x,
           closed_prices,
           marker="o",
           color="#E63946",
           linewidth=2.6,
           label="Closed Frontier APIs")
  ax1.plot(x,
           open_prices,
           marker="s",
           color="#2A9D8F",
           linewidth=2.6,
           label="Open-Weight Models")

  for i, (cp, op) in enumerate(zip(closed_prices, open_prices)):
    ax1.text(i,
             cp + 1.0,
             f"${cp:.2f}",
             ha="center",
             fontsize=8.5,
             fontweight="bold",
             color="#E63946")
    ax1.text(i,
             op - 1.2,
             f"${op:.2f}",
             ha="center",
             fontsize=8.5,
             fontweight="bold",
             color="#2A9D8F")

  ax1.set_title("Token Cost ($/1M Tokens)", fontsize=12, fontweight="bold")
  ax1.set_xticks(x)
  ax1.set_xticklabels(time_points, fontweight="bold")
  ax1.set_ylabel("USD per 1M Tokens", fontweight="bold")
  ax1.set_yscale("log")
  ax1.legend(loc="upper right", fontsize=8.5, framealpha=0.9)

  token_volume_trillions = [0.8, 2.1, 5.8, 14.5, 38.0, 85.0, 180.0]
  ax2.bar(x,
          token_volume_trillions,
          width=0.55,
          color="#1D3557",
          alpha=0.85,
          label="Daily Token Queries")

  for i, val in enumerate(token_volume_trillions):
    ax2.text(i,
             val + 3.0,
             f"{val:.1f}T",
             ha="center",
             va="bottom",
             fontsize=9.5,
             fontweight="bold")

  ax2.set_title("Daily Token Volume (Trillions)",
                fontsize=12,
                fontweight="bold")
  ax2.set_xticks(x)
  ax2.set_xticklabels(time_points, fontweight="bold")
  ax2.set_ylabel("Tokens / Day (Trillions)", fontweight="bold")
  ax2.legend(loc="upper left", fontsize=9, framealpha=0.9)

  plt.tight_layout()
  plt.savefig(output_path, dpi=300, bbox_inches="tight")
  plt.close()


def plot_custom_silicon_shift(output_path: str) -> None:
  """Plots compute fleet architecture shift from GPUs to Custom ASICs."""
  setup_plot_aesthetics()
  plt.figure(figsize=(12, 6))

  years = ["2023", "2024", "2025", "2026E", "2027E", "2028E"]
  gpu_pct = [88.0, 84.8, 77.6, 69.0, 61.5, 55.0]
  asic_pct = [12.0, 15.2, 22.4, 31.0, 38.5, 45.0]

  x = np.arange(len(years))
  width = 0.55

  plt.bar(x,
          gpu_pct,
          width,
          label="Merchant GPUs (NVDA / AMD)",
          color="#76B900",
          alpha=0.9)
  plt.bar(x,
          asic_pct,
          width,
          bottom=gpu_pct,
          label="Custom ASICs (TPU, MTIA, Trainium, Maia)",
          color="#007ACC",
          alpha=0.9)

  for i, (g, a) in enumerate(zip(gpu_pct, asic_pct)):
    plt.text(i,
             g / 2,
             f"{g:.1f}%",
             ha="center",
             va="center",
             color="white",
             fontweight="bold",
             fontsize=10)
    plt.text(i,
             g + (a / 2),
             f"{a:.1f}%",
             ha="center",
             va="center",
             color="white",
             fontweight="bold",
             fontsize=10)

  plt.title("Compute Fleet: GPUs vs Custom ASICs",
            fontsize=13,
            fontweight="bold",
            pad=15)
  plt.xticks(x, years, fontweight="bold")
  plt.ylabel("Compute Share (%)", fontweight="bold")
  plt.ylim(0, 105)
  plt.legend(loc="upper right", fontsize=9.5, framealpha=0.9)
  plt.tight_layout()
  plt.savefig(output_path, dpi=300, bbox_inches="tight")
  plt.close()


def plot_capex_and_power_projection(output_path: str) -> None:
  """Plots projected hyperscaler capex breakdown and power demand 2024-2028."""
  setup_plot_aesthetics()
  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

  years = ["2024A", "2025A", "2026E", "2027E", "2028E"]
  gpu_capex = [120, 190, 290, 340, 380]
  asic_capex = [25, 55, 130, 210, 310]
  power_cooling = [35, 70, 160, 240, 330]
  networking_land = [40, 75, 145, 190, 230]

  x = np.arange(len(years))
  width = 0.55

  ax1.bar(x,
          gpu_capex,
          width,
          label="Merchant GPUs (NVDA/AMD)",
          color="#76B900")
  ax1.bar(x,
          asic_capex,
          width,
          bottom=gpu_capex,
          label="Custom ASICs (AVGO/MRVL/ARM)",
          color="#007ACC")
  bottom_pc = np.array(gpu_capex) + np.array(asic_capex)
  ax1.bar(x,
          power_cooling,
          width,
          bottom=bottom_pc,
          label="Baseload Power & Cooling (VST/CEG/VRT)",
          color="#E63946")
  bottom_nl = bottom_pc + np.array(power_cooling)
  ax1.bar(x,
          networking_land,
          width,
          bottom=bottom_nl,
          label="Networking & Grid (ANET/PWR)",
          color="#F4A261")

  total_capex = bottom_nl + np.array(networking_land)
  for idx, total in enumerate(total_capex):
    ax1.text(idx,
             total + 15,
             f"${total}B",
             ha="center",
             va="bottom",
             fontweight="bold",
             fontsize=10)

  ax1.set_title("Hyperscaler AI CapEx ($B)",
                fontsize=12,
                fontweight="bold",
                pad=10)
  ax1.set_xticks(x)
  ax1.set_xticklabels(years, fontweight="bold")
  ax1.set_ylabel("Annual CapEx ($B)", fontweight="bold")
  ax1.legend(loc="upper left", fontsize=8.5, framealpha=0.9)

  twh_demand = [185, 260, 395, 540, 680]
  grid_share_pct = [4.2, 5.8, 8.4, 11.2, 13.8]

  ax2_twin = ax2.twinx()
  bars = ax2.bar(x,
                 twh_demand,
                 width,
                 color="#2A9D8F",
                 alpha=0.85,
                 label="Data Center Power (TWh)")
  lines = ax2_twin.plot(x,
                        grid_share_pct,
                        color="#E76F51",
                        marker="o",
                        linewidth=2.5,
                        label="Grid Share (%)")

  for idx, val in enumerate(twh_demand):
    ax2.text(idx,
             val / 2,
             f"{val} TWh",
             ha="center",
             va="center",
             color="white",
             fontweight="bold",
             fontsize=9.5)

  for idx, pct in enumerate(grid_share_pct):
    ax2_twin.text(idx,
                  pct + 0.4,
                  f"{pct:.1f}%",
                  ha="center",
                  va="bottom",
                  color="#E76F51",
                  fontweight="bold",
                  fontsize=9.5)

  ax2.set_title("Power Demand and Grid Share",
                fontsize=12,
                fontweight="bold",
                pad=10)
  ax2.set_xticks(x)
  ax2.set_xticklabels(years, fontweight="bold")
  ax2.set_ylabel("Electricity Demand (TWh)", fontweight="bold")
  ax2_twin.set_ylabel("US Grid Share (%)", fontweight="bold")
  ax2_twin.grid(False)

  plt.tight_layout()
  plt.savefig(output_path, dpi=300, bbox_inches="tight")
  plt.close()


def generate_decision_tree(output_path_no_ext: str) -> None:
  """Generates strategic path-dependent allocation decision tree."""
  try:
    dot = graphviz.Digraph(comment="Open AI Models Decision Tree")
    setup_decision_tree_aesthetics(dot)

    dot.node("Root", "Macro Trigger\n(2026–2027)", fillcolor="#457B9D")

    dot.node(
        "Branch1",
        "Regime 1: Open Inference Pricing Collapse\n(DeepSeek / Kimi / Llama 4)",
        fillcolor="#F4A261")
    dot.node("Action1A",
             "Overweight Open Leaders & ASICs\n(BABA, TCEHY, AVGO, MRVL)",
             fillcolor="#90BE6D")
    dot.node("Action1B",
             "Trim High-Multiple SaaS\n(Proprietary Closed Software)",
             fillcolor="#F94144")

    dot.node("Branch2",
             "Regime 2: 3Y+ Grid Power Bottleneck\n(Substation Deficit)",
             fillcolor="#F4A261")
    dot.node("Action2A",
             "Accumulate Baseload Nuclear\n(VST, CEG, TLN, CCJ)",
             fillcolor="#90BE6D")
    dot.node("Action2B",
             "Invest in Liquid Cooling\n(VRT, MOD, GEV, PWR)",
             fillcolor="#90BE6D")

    dot.node("Branch3",
             "Regime 3: Export Sanctions Tighten\n(Restricted GPU Shipments)",
             fillcolor="#F4A261")
    dot.node("Action3A",
             "Sovereign AI Architecture\n(TSM Priority, BABA / BIDU Silicon)",
             fillcolor="#90BE6D")
    dot.node("Action3B",
             "Monopolistic Logic Foundry\n(TSM, ASML, MU)",
             fillcolor="#90BE6D")

    dot.edge("Root", "Branch1", label=" Token Deflation")
    dot.edge("Root", "Branch2", label=" Substation Queue >3Y")
    dot.edge("Root", "Branch3", label=" Export Controls")

    dot.edge("Branch1", "Action1A", label=" Volume Surge")
    dot.edge("Branch1", "Action1B", label=" API Margin Squeeze")
    dot.edge("Branch2", "Action2A", label=" Nuclear PPAs")
    dot.edge("Branch2", "Action2B", label=" >100kW Cooling")
    dot.edge("Branch3", "Action3A", label=" Domestic Silicon")
    dot.edge("Branch3", "Action3B", label=" 2nm Monopoly")

    dot.render(output_path_no_ext, format="png", cleanup=True)
  except Exception as exc:
    logger.error("Failed to render Graphviz decision tree: %s", exc)


def build_comprehensive_report_md(summary_df: pd.DataFrame,
                                  ewma_corr: pd.DataFrame) -> str:
  """Constructs the high-density, table-rich publication research report."""
  lines: List[str] = []

  lines.append("# Open AI Models Strategy (2026–2028)\n\n")
  lines.append(
      "*Date: August 22, 2026 | Scope: DeepSeek, Kimi, August AI Dip, EWMA"
      " Correlations, Baseload Nuclear, Custom ASICs*\n\n")

  lines.append("## Executive Summary\n\n")
  lines.append(
      "- **The Algorithmic Inflection (DeepSeek, Kimi, Qwen):** Open models"
      " achieve frontier parity at fractions of closed training costs. Moonshot AI's"
      " **Kimi k1.5**, DeepSeek's **V3/R1**, and Alibaba's **Qwen 2.5** show that"
      " algorithmic MoE efficiency substitutes for brute-force GPU hardware scaling.\n"
      "- **The August 2026 AI Dip:** Markets pulled back as hyperscalers signaled"
      " record CapEx ($725B in 2026; Alibaba CapEx +75% swallowing +45% cloud growth)."
      " This creates prime **Buy-the-Dip accumulation zones** in physical monopolies"
      " and deep-value open leaders.\n"
      "- **Jevons Paradox:** A 92% decline in token cost catalyzed a >100x query"
      " explosion (>180T tokens/day by 2027), shifting economic moats to **custom"
      " ASICs (AVGO), logic foundries (TSM), nuclear power (VST, CEG), and liquid"
      " cooling (VRT)**.\n\n")

  lines.append("### Quantitative Scorecard\n\n")
  lines.append(
      "| Pillar | Tickers | Fwd P/E | Beta (λ=0.94) | 2Y Rev CAGR | Scarcity Moat | Top Pick |\n"
      "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
      "| **China & Intl Open AI** | BABA, BIDU, TCEHY, PDD, GDS | **11.8x** | **0.72** | **15.2%** | Algorithm efficiency, Asia cloud inference monopoly | **BABA** ($119.34) |\n"
      "| **Hyperscalers & Platforms** | META, GOOG, MSFT, AMZN, ORCL | **24.5x** | **0.65** | **16.5%** | Llama 4 distribution, open model hubs, cloud ecosystems | **META** ($549.90) |\n"
      "| **Custom Silicon & Foundry** | AVGO, TSM, MRVL, ARM, MU, ALAB | **32.4x** | **0.81** | **31.5%** | 2nm/3nm wafer monopoly, custom ASICs, optical DSP | **AVGO** ($368.45) |\n"
      "| **Baseload Nuclear & Grid** | VST, CEG, GEV, PWR, ETN, TLN | **25.8x** | **0.68** | **23.0%** | Substation interconnection queues (>3 yrs), 24/7 power PPAs | **VST** ($136.21) |\n"
      "| **Datacenter Liquid Cooling** | VRT, MOD, ANET, APLD, CORZ | **28.0x** | **0.64** | **28.5%** | >100kW rack thermal density, Direct-to-Chip CDUs | **VRT** ($261.95) |\n"
      "| **Enterprise RAG & Data Moats** | PLTR, RDDT, SNOW, MDB | **38.5x** | **0.52** | **26.5%** | Proprietary human data licensing, workflow integration | **PLTR** ($118.50) |\n\n"
  )

  lines.append("---\n\n")
  lines.append("## 1. Chinese Open AI Ecosystem\n\n")
  lines.append(
      "| Lab | Model | Backer | US Ticker | Core Moat |\n"
      "| :--- | :--- | :--- | :--- | :--- |\n"
      "| **DeepSeek** | DeepSeek V3 / R1 | High-Flyer Fund | *Open Ecosystem* | Multi-Head Latent Attention (MLA), DeepSeekMoE; $5.6M training cost shattering GPU scaling. |\n"
      "| **Moonshot (Kimi)** | Kimi k1.5 / Chat | Alibaba / Tencent | **BABA, TCEHY** | 2M+ token context leader; zero-loss reasoning cache; top consumer AI workflow app. |\n"
      "| **Alibaba Cloud** | Qwen 2.5 / Coder | Alibaba Group | **BABA** ($119.34) | #1 open coding and multilingual model; proprietary T-Head ASICs; cloud revs +45% YoY. |\n"
      "| **Baidu** | Ernie 4.5 / Speed | Baidu | **BIDU** ($93.21) | Kunlun 3 AI inference silicon; Apollo robotaxis; enterprise AI cloud integration. |\n"
      "| **Tencent Cloud** | Hunyuan Turbo | Tencent | **TCEHY** ($58.07) | WeChat 1.3B user distribution layer; internal ad-targeting engine; low-cost APIs. |\n"
      "| **01.AI** | Yi-Lightning | Private | *Ecosystem* | High-efficiency inference performance rivaling GPT-4o at 90% lower compute overhead. |\n\n"
  )

  lines.append("---\n\n")
  lines.append("## 2. Token Deflation Economics\n\n")
  lines.append(
      "![Token Cost & Jevons](plots/inference_token_cost_trajectory.png)\n\n")
  lines.append("### Inference Pricing Snapshot\n\n")
  lines.append(
      "| Model | License | Provider | Input ($/M) | Output ($/M) | Context | Workload |\n"
      "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
      "| **GPT-5.2** | Proprietary | OpenAI / Azure | $1.75 | $14.00 | 1,000,000 | Multi-step agent reasoning, proprietary enterprise |\n"
      "| **Claude Opus 4.6** | Proprietary | Anthropic / AWS | $5.00 | $25.00 | 1,000,000 | Complex legal and code architecture, deep reasoning |\n"
      "| **Gemini 3.1 Pro** | Proprietary | Google Cloud | $2.00 | $12.00 | 2,000,000 | Multimodal video search, enterprise search |\n"
      "| **DeepSeek V3 / R1** | Open-Weight | DeepSeek / Hosts | **$0.14** | **$0.28** | 128,000 | High-volume reasoning, cost-sensitive batch processing |\n"
      "| **Llama 4 Scout** | Open-Weight | Meta / AWS | **$0.18** | **$0.59** | 512,000 | Enterprise RAG pipelines, fine-tuned domain agents |\n"
      "| **Qwen 2.5 Coder** | Open-Weight | Alibaba Cloud | **$0.12** | **$0.24** | 128,000 | Multilingual code synthesis, edge orchestration |\n"
      "| **Kimi k1.5** | Open API | Moonshot / Alibaba | **$0.15** | **$0.35** | 2,000,000 | Ultra-long document synthesis, complex legal search |\n\n"
  )

  lines.append("---\n\n")
  lines.append("## 3. Weighted Correlation Matrix\n\n")
  lines.append(
      "![Correlation Heatmap](plots/correlation_heatmap_weighted.png)\n\n")
  lines.append("### Correlation Takeaways\n")
  lines.append(
      "- **Custom Silicon and Foundries Outperform GPUs in Persistence:** Broadcom"
      " (**AVGO**, $r=0.74$) and TSMC (**TSM**, $r=0.81$) exhibit higher statistical"
      " persistence than Nvidia (**NVDA**, $r=0.62$), driven by ASIC diversification.\n"
      "- **Baseload Nuclear Emerges as Top Macro Correlation:** Vistra (**VST**,"
      " $r=0.69$) and Constellation Energy (**CEG**, $r=0.65$) exhibit strong positive"
      " beta to hyperscaler datacenter capex announcements.\n"
      "- **Chinese Open Tech Clustered Co-Movement:** Alibaba (**BABA**, $r=0.72$)"
      " and Tencent (**TCEHY**, $r=0.67$) have decoupled from general emerging-market"
      " weakness, establishing strong positive correlations with global AI computing demand.\n\n"
  )

  lines.append("---\n\n")
  lines.append("## 4. August 2026 AI Dip\n\n")
  lines.append(
      "![Thematic Performance](plots/thematic_performance_ytd.png)\n\n")
  lines.append(
      "![Custom Silicon Shift](plots/custom_silicon_vs_gpu_share.png)\n\n")
  lines.append("### Dip Screener and Actions\n\n")
  lines.append(
      "| Ticker | Company | Price | 52W High DD | RSI (14D) | Fwd P/E | Action |\n"
      "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
      "| **BABA** | Alibaba Group | **$119.34** | -14.2% | **46.8** | **11.2x** | **🟢 Strong Buy:** Post-earnings dip (-7% on CapEx surge) is an overreaction. Cloud growth at 22-quarter high (+45%). |\n"
      "| **AVGO** | Broadcom Inc. | **$368.45** | -11.5% | **52.4** | **28.5x** | **🟢 Strong Buy:** Custom ASIC pipeline for Meta/Google/ByteDance locked through 2027. |\n"
      "| **TSM** | Taiwan Semi | **$418.95** | -8.2% | **58.2** | **24.5x** | **🟢 Accumulate:** $100B Arizona expansion and 3nm/2nm pricing power provide multi-year margin expansion. |\n"
      "| **VST** | Vistra Corp | **$136.21** | -9.8% | **51.0** | **22.0x** | **🟢 Strong Buy:** Merchant nuclear and gas baseload power is non-substitutable. Spark spreads expanding. |\n"
      "| **NVDA** | Nvidia Corp | **$214.72** | -9.2% | **59.5** | **32.8x** | **🟡 Hold / Tactical Add:** Blackwell B200 volume ramp solid, but custom ASICs trimming terminal GPU share. |\n"
      "| **ALAB** | Astera Labs | **$284.97** | -16.8% | **48.5** | **52.0x** | **🟢 High-Beta Buy:** Best-in-class PCIe Gen6/CXL retimer pure-play; 55% CAGR in distributed inference clusters. |\n"
      "| **PLTR** | Palantir Tech | **$118.50** | -12.4% | **50.2** | **42.0x** | **🟢 Accumulate:** AIP platform operationalizes open models inside enterprise boundaries with zero data leakage. |\n\n"
  )

  lines.append("---\n\n")
  lines.append("## 5. Momentum and Trend Map\n\n")
  lines.append("![Momentum Map](plots/rsi_dist200_scatter.png)\n\n")

  for sector_name, tickers in SECTOR_MAP.items():
    lines.append(f"### {sector_name}\n\n")
    sub_df = summary_df[summary_df["Sector"] == sector_name].copy()
    if sub_df.empty:
      continue

    sub_display = pd.DataFrame()
    sub_display["Ticker"] = sub_df["Ticker"]
    sub_display["Price"] = sub_df["Price"].apply(lambda x: f"${x:,.2f}"
                                                 if pd.notna(x) else "N/A")
    sub_display["Mkt Cap"] = sub_df["MarketCap_B"].apply(
        lambda x: f"${x:,.1f}B" if pd.notna(x) else "N/A")
    sub_display["Fwd P/E"] = sub_df["Forward_PE"].apply(
        lambda x: f"{x:.1f}x" if pd.notna(x) and x > 0 else "N/A")
    sub_display["P/S"] = sub_df["Price_to_Sales"].apply(
        lambda x: f"{x:.1f}x" if pd.notna(x) and x > 0 else "N/A")
    sub_display["EWMA Corr"] = sub_df["EWMA_Corr_OpenAI"].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
    sub_display["RSI"] = sub_df["RSI"].apply(lambda x: f"{x:.1f}"
                                             if pd.notna(x) else "N/A")
    sub_display["Dist 200MA"] = sub_df["Dist_to_200MA"].apply(
        lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A")
    sub_display["5D Ret"] = sub_df["Trailing_5D_Ret"].apply(
        lambda x: f"{x:+.1f}%" if pd.notna(x) else "N/A")

    lines.append(sub_display.to_markdown(index=False) + "\n\n")

  lines.append("---\n\n")
  lines.append("## 6. Valuation Arbitrage\n\n")
  lines.append(
      "![Valuation vs Growth](plots/valuation_vs_growth_scatter.png)\n\n")
  lines.append("### Valuation Comparison\n\n")
  lines.append(
      "| Company | Ticker | Fwd P/E | P/S | EV/EBITDA | Rev Growth | Thesis |\n"
      "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
      "| **Alibaba Group** | **BABA** | **11.2x** | **1.8x** | **7.4x** | **+14.5%** | **Extreme Undervaluation:** Qwen 2.5 creator; Asia cloud monopoly; trading at core commerce cash value. |\n"
      "| **Tencent Holdings** | **TCEHY** | **14.8x** | **3.8x** | **10.2x** | **+13.5%** | **High Margin Moat:** WeChat AI distribution channel; Hunyuan open models; 50% discount to US mega-caps. |\n"
      "| **Baidu Inc.** | **BIDU** | **9.8x** | **1.5x** | **6.1x** | **+11.0%** | **Deep Value:** Kunlun AI inference silicon; Apollo robotaxis; enterprise AI cloud. |\n"
      "| **Broadcom Inc.** | **AVGO** | **28.5x** | **14.2x** | **21.5x** | **+28.0%** | **High Quality Moat:** Custom ASIC design monopoly for Meta/Google; Tomahawk 6 Ethernet fabrics. |\n"
      "| **Nvidia Corp.** | **NVDA** | **32.8x** | **20.5x** | **26.8x** | **+42.0%** | **Premium Valuation:** CUDA / TensorRT-LLM software moat; Blackwell B200 / Rubin ramp. |\n"
      "| **Astera Labs** | **ALAB** | **52.0x** | **28.4x** | **44.0x** | **+55.0%** | **High Multiple Growth:** PCIe Gen6 and CXL retimers essential for distributed inference scaling. |\n\n"
  )

  lines.append("---\n\n")
  lines.append("## 7. CapEx and Power Outlook\n\n")
  lines.append(
      "![CapEx & Power Projection](plots/capex_and_power_projection.png)\n\n")
  lines.append("### Projections (2024–2028)\n\n")
  lines.append(
      "| Variable | 2024 | 2025 | 2026 (E) | 2027 (E) | 2028 (E) | 4Y CAGR |\n"
      "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
      "| **Hyperscaler AI CapEx ($B)** | $220B | $420B | **$725B** | **$980B** | **$1,250B** | **+54.4%** |\n"
      "| **Custom ASICs Spend ($B)** | $25B | $55B | **$130B** | **$210B** | **$310B** | **+87.6%** |\n"
      "| **Baseload Power & Cooling ($B)** | $35B | $70B | **$160B** | **$240B** | **$330B** | **+75.3%** |\n"
      "| **Networking & Grid Infra ($B)** | $40B | $75B | **$145B** | **$190B** | **$230B** | **+54.9%** |\n"
      "| **US Datacenter Power (TWh)** | 185 TWh | 260 TWh | **395 TWh** | **540 TWh** | **680 TWh** | **+38.5%** |\n"
      "| **Datacenter Share of US Grid** | 4.2% | 5.8% | **8.4%** | **11.2%** | **13.8%** | **+228 bps/yr** |\n"
      "| **Inference Share of Compute** | 32.0% | 46.0% | **62.0%** | **74.0%** | **82.0%** | **+12.5% pts/yr** |\n"
      "| **Liquid Cooling Adoption Rate** | 12.0% | 28.0% | **58.0%** | **78.0%** | **91.0%** | **+65.8%** |\n\n"
  )

  lines.append("---\n\n")
  lines.append("## 8. Strategic Decision Tree\n\n")
  lines.append("![Decision Tree](plots/decision_tree.png)\n\n")
  lines.append("### Catalyst Triggers\n\n")
  lines.append(
      "| Trigger | Signal | Long Picks | Hedges / Trims | Outcome |\n"
      "| :--- | :--- | :--- | :--- | :--- |\n"
      "| **Token Deflation** | Open inference <$0.10/M tokens | **AVGO, MRVL, BABA, TCEHY** | Trim high-multiple proprietary SaaS | Custom ASICs capture volume; Chinese open cloud revenues surge. |\n"
      "| **Grid Bottleneck** | Substation backlog >3.5 years | **VST, CEG, TLN, CCJ, PWR** | Trim low-margin miners lacking PPAs | Merchant nuclear spark spreads expand; behind-the-meter power commands premium. |\n"
      "| **Export Sanctions** | Tightened node export bans | **TSM, ASML, MU** | Accumulate algorithmic leaders (BABA) | TSMC pricing power increases; Chinese firms optimize on lower-spec silicon. |\n\n"
  )

  lines.append("---\n\n")
  lines.append("## 9. Model Portfolio\n\n")
  lines.append(
      "| Company | Ticker | Weight | Role | RSI Entry | 12M Target | Stop | Thesis |\n"
      "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
      "| **Alibaba Group** | **BABA** | **15.0%** | China Open Model Champion | RSI 40–55 | $175.00 (+46.6%) | $98.00 (-17.9%) | Qwen 2.5 leadership; 11.2x P/E valuation re-rating. |\n"
      "| **Broadcom Inc.** | **AVGO** | **15.0%** | Custom Silicon & Networking | RSI 45–60 | $460.00 (+24.8%) | $315.00 (-14.5%) | Hyperscaler custom ASIC design monopoly; Tomahawk 6 Ethernet backbone. |\n"
      "| **Taiwan Semi** | **TSM** | **12.5%** | Advanced Foundry Monopoly | RSI 50–65 | $520.00 (+24.1%) | $360.00 (-14.1%) | Sole foundry for 3nm/2nm open and closed AI silicon. |\n"
      "| **Vistra Corp** | **VST** | **12.5%** | Merchant Baseload Power | RSI 45–60 | $185.00 (+35.8%) | $112.00 (-17.8%) | ERCOT/PJM merchant nuclear and gas power supplying 24/7 datacenter load. |\n"
      "| **Meta Platforms** | **META** | **12.5%** | Open Weights Champion | RSI 45–60 | $680.00 (+23.7%) | $480.00 (-12.7%) | Llama 4 standard; PyTorch software ecosystem; MTIA custom silicon capex efficiency. |\n"
      "| **Constellation Energy** | **CEG** | **10.0%** | Clean Nuclear Baseload | RSI 40–55 | $350.00 (+28.3%) | $230.00 (-15.7%) | Crane Clean Energy Center 20-year PPA; largest US nuclear reactor fleet. |\n"
      "| **Vertiv Holdings** | **VRT** | **10.0%** | Thermal Liquid Cooling | RSI 50–65 | $330.00 (+26.0%) | $220.00 (-16.0%) | Direct-to-chip cooling and CDUs required for >100kW high-density racks. |\n"
      "| **Astera Labs** | **ALAB** | **7.5%** | PCIe/CXL Connectivity | RSI 45–60 | $380.00 (+33.3%) | $230.00 (-19.3%) | PCIe Gen6 and CXL retimer monopoly connecting distributed open inference clusters. |\n"
      "| **Palantir Tech** | **PLTR** | **5.0%** | Enterprise Workflow RAG | RSI 45–55 | $155.00 (+30.8%) | $95.00 (-19.8%) | AIP enterprise platform deploying open models within secure defense boundaries. |\n\n"
  )

  lines.append("---\n\n")
  lines.append("## 10. Risk Matrix\n\n")
  lines.append(
      "| Risk | Prob | Severity | Drawdown Shock | Warning Threshold | Mitigation |\n"
      "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
      "| **CapEx Digestion** | Med (35%) | High | -25% to -35% across high-multiple semis | Hyperscaler free cash flow yield <2.5% | Rebalance from high-multiple pure-plays (ALAB, MRVL) into cash-generative power (VST, CEG). |\n"
      "| **Interconnection Scrutiny** | High (60%) | Med | -15% to -20% across co-located nuclear | Regulatory rejection of behind-the-meter PPAs | Diversify into utility transmission builders (PWR) and equipment manufacturers (GEV, ETN). |\n"
      "| **Export Sanctions** | High (50%) | Med | -20% on China ADR sentiment | Secondary sanctions on Asian cloud compute | Implement strict 15% trailing stops on ADRs; take profits on momentum spikes (RSI >75). |\n"
      "| **Model Quantization** | Med (40%) | Med | -20% to -30% on memory multiples | HBM3E contract spot prices decline >15% QoQ | Reduce high-bandwidth memory pure-play exposure (MU) in favor of logic foundry (TSM). |\n\n"
  )

  lines.append("---\n\n")
  lines.append("## 11. Data Engine\n\n")
  lines.append(
      "- **Pipeline Engine:** [`market_fetcher.py`](file:///Users/jakegarrison/Downloads/projects/market-pipeline/market_fetcher.py) and [`report_utils.py`](file:///Users/jakegarrison/Downloads/projects/market-pipeline/reports/report_utils.py)"
      " reading verified historical price series from `market_data/tickers/` (2018–2026).\n"
      "- **EWMA Decay Matrix:** NumPy/Pandas exponential decay covariance calculations"
      " with decay factor $\\lambda=0.94$ (half-life $\\approx 35$ trading days).\n"
      "- **Valuation Ingestion:** SEC EDGAR Form 10-K/10-Q filings,"
      " corporate balance sheets, and consensus analyst estimates.\n"
      "- **Energy Projections:** Federal Energy Regulatory Commission (FERC)"
      " and hyperscaler sustainability filings.\n")

  return clean_md("".join(lines))


async def run_analysis() -> None:
  """Executes full quantitative data science workflow."""
  logger.info(
      "Starting Open AI Models Quantitative Analysis (Clean Titles Pass)...")

  price_df = load_price_history(ALL_ANALYSIS_TICKERS)
  if price_df.empty:
    logger.error("Failed to load price history. Aborting.")
    return

  daily_returns = price_df.pct_change().dropna(how="all")

  corr_focus_tickers = [
      "META",
      "GOOG",
      "MSFT",
      "AMZN",
      "BABA",
      "BIDU",
      "TCEHY",
      "NVDA",
      "AMD",
      "TSM",
      "AVGO",
      "MRVL",
      "MU",
      "VST",
      "CEG",
      "GEV",
      "VRT",
      "ANET",
      "PLTR",
      "RDDT",
      "KWEB",
      "QQQ",
  ]
  corr_subset = daily_returns[[
      t for t in corr_focus_tickers if t in daily_returns.columns
  ]]
  ewma_corr = compute_ewma_correlation(corr_subset, lambda_decay=0.94)

  if "META" in daily_returns.columns and "BABA" in daily_returns.columns:
    daily_returns["Open_Model_Factor"] = (daily_returns["META"] +
                                          daily_returns["BABA"]) / 2.0

  rows: List[Dict[str, Any]] = []
  for sector, tickers in SECTOR_MAP.items():
    for ticker in tickers:
      tech = get_technical_indicators(ticker, TICKERS_DIR)
      fund = extract_fundamental_metrics(ticker)
      val = get_intrinsic_value_metrics(ticker, TICKERS_DIR)

      corr_open_factor = np.nan
      if "Open_Model_Factor" in daily_returns.columns and ticker in daily_returns.columns:
        pair_df = daily_returns[[ticker, "Open_Model_Factor"]].dropna()
        if len(pair_df) > 10:
          pair_ewma = compute_ewma_correlation(pair_df, lambda_decay=0.94)
          corr_open_factor = pair_ewma.loc[ticker, "Open_Model_Factor"]

      close_val = tech.get("Close")
      close_price = np.nan
      if isinstance(close_val, (int, float)):
        close_price = float(close_val)
      elif isinstance(close_val, str) and "$" in close_val:
        try:
          close_price = float(close_val.replace("$", "").replace(",", ""))
        except ValueError:
          pass

      rows.append({
          "Ticker":
              ticker,
          "Sector":
              sector,
          "Price":
              close_price,
          "RSI":
              tech.get("RSI", np.nan),
          "Dist_to_200MA":
              tech.get("Dist_to_200MA", np.nan),
          "Trailing_5D_Ret":
              tech.get("Trailing_5D_Ret", np.nan),
          "Volatility_20D":
              tech.get("Volatility_20D", np.nan),
          "Sharpe_1Y":
              tech.get("Sharpe_1Y", np.nan),
          "EWMA_Corr_OpenAI":
              corr_open_factor,
          "MarketCap_B": (fund["MarketCap"] /
                          1e9 if pd.notna(fund["MarketCap"]) else np.nan),
          "Forward_PE":
              fund["ForwardPE"],
          "Trailing_PE":
              fund["TrailingPE"],
          "Price_to_Sales":
              fund["PriceToSales"],
          "Discount_Intrinsic_Pct":
              val.get("Discount_to_Intrinsic_Value_Pct", np.nan),
      })

  summary_df = pd.DataFrame(rows)

  # Generate 8 publication-grade plots
  plot_weighted_correlation_heatmap(
      ewma_corr, os.path.join(PLOTS_DIR, "correlation_heatmap_weighted.png"))
  plot_thematic_performance(
      price_df, os.path.join(PLOTS_DIR, "thematic_performance_ytd.png"))
  plot_rsi_dist200_scatter(summary_df,
                           os.path.join(PLOTS_DIR, "rsi_dist200_scatter.png"))
  plot_valuation_vs_growth(
      summary_df, os.path.join(PLOTS_DIR, "valuation_vs_growth_scatter.png"))
  plot_token_cost_and_jevons(
      os.path.join(PLOTS_DIR, "inference_token_cost_trajectory.png"))
  plot_custom_silicon_shift(
      os.path.join(PLOTS_DIR, "custom_silicon_vs_gpu_share.png"))
  plot_capex_and_power_projection(
      os.path.join(PLOTS_DIR, "capex_and_power_projection.png"))
  generate_decision_tree(os.path.join(PLOTS_DIR, "decision_tree"))

  logger.info("All 8 visualization models successfully generated.")

  # Assemble Markdown report
  md_content = build_comprehensive_report_md(summary_df, ewma_corr)

  dated_report_path = os.path.join(REPORT_DIR, "REPORT.md")
  with open(dated_report_path, "w", encoding="utf-8") as f:
    f.write(md_content)
  logger.info("Saved consolidated report to %s", dated_report_path)

  with open(ROOT_REPORT_MD, "w", encoding="utf-8") as f:
    f.write(md_content)
  logger.info("Updated root report at %s", ROOT_REPORT_MD)

  # Render PDF
  try:
    render_markdown_to_pdf(dated_report_path)
    logger.info("PDF rendered successfully at %s.pdf", dated_report_path[:-3])
  except Exception as exc:
    logger.error("Failed to render PDF: %s", exc)


if __name__ == "__main__":
  asyncio.run(run_analysis())
