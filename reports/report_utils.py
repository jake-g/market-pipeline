# pylint: disable=duplicate-code
import datetime
import difflib
import logging
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from graphviz import Digraph
import markdown  # type: ignore
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from tabulate import tabulate
from weasyprint import CSS
from weasyprint import HTML

# Append project root to import config
REPORTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(REPORTS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

import config
from market_fetcher import MarketFetcher

logger = logging.getLogger(__name__)

# Silence verbose third-party PDF rendering and font engine logs
logging.getLogger("weasyprint").setLevel(logging.WARNING)
logging.getLogger("weasyprint.progress").setLevel(logging.WARNING)
logging.getLogger("fontTools").setLevel(logging.WARNING)

# ==========================================
# STRING & FORMATTING UTILITIES
# ==========================================


def clean_md(text: str) -> str:
  """Sanitizes markdown strings to prevent whitespace and EOF check failures."""
  if not text:
    return "\n"
  lines = [l.rstrip() for l in text.splitlines()]
  return "\n".join(lines).rstrip("\r\n") + "\n"


# ==========================================
# QUANTITATIVE & TECHNICAL METRICS
# ==========================================


def compute_sector_summary(df: pd.DataFrame,
                           sector_col: str = 'Sector') -> pd.DataFrame:
  """Computes aggregate statistics per sector.

  Args:
    df: DataFrame with columns including 'Sector', 'RSI',
        'Dist_to_200MA', 'Forward_PE', 'Sharpe_1Y',
        'Volatility_20D'.
    sector_col: Column name for sector grouping.

  Returns:
    DataFrame with sector-level mean/median metrics.
  """
  metric_cols = [
      'RSI',
      'Dist_to_200MA',
      'Forward_PE',
      'Sharpe_1Y',
      'Volatility_20D',
  ]
  if df.empty or sector_col not in df.columns:
    logger.warning("Cannot compute sector summary: missing data.")
    return pd.DataFrame()
  available = [c for c in metric_cols if c in df.columns]
  if not available:
    logger.warning("No metric columns found for sector summary.")
    return pd.DataFrame()
  summary = df.groupby(sector_col).agg(**{
      f"Mean_{col}": pd.NamedAgg(column=col, aggfunc='mean') for col in available
  })
  summary['Ticker_Count'] = df.groupby(sector_col).size()
  summary = summary.round(2)
  return summary.sort_values('Ticker_Count', ascending=False)


def compute_rsi(data: pd.Series, window: int = 14) -> pd.Series:
  """Calculates the Relative Strength Index (RSI) for a given pandas Series."""
  delta = data.diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
  rs = gain / loss
  return 100 - (100 / (1 + rs))


def setup_plot_aesthetics():
  """Configures a clean, consistent Seaborn visual aesthetic for all automated trading reports."""
  sns.set_theme(style="whitegrid",
                font_scale=1.1,
                rc={
                    "font.family": "sans-serif",
                    "axes.spines.top": False,
                    "axes.spines.right": False,
                    "legend.frameon": False
                })


def setup_decision_tree_aesthetics(dot: Digraph):
  """Applies a clean, readable global font and structural style to Graphviz Digraph objects."""
  dot.attr(rankdir="TB",
           size="12,12!",
           dpi="300",
           nodesep="0.5",
           ranksep="0.8",
           fontname="Helvetica",
           fontsize="14")
  dot.attr("node",
           shape="box",
           style="rounded,filled",
           fontname="Helvetica-Bold",
           fontsize="14")
  dot.attr("edge", fontname="Helvetica-Bold", fontsize="12")


def draw_matplotlib_decision_tree(nodes: Dict[str, Dict[str, Any]],
                                  edges: List[Tuple[str, str]],
                                  title: str,
                                  output_path: str,
                                  edge_labels: Optional[Dict[Tuple[str, str],
                                                             str]] = None,
                                  figsize: Tuple[int, int] = (14, 8)):
  """Generalized helper to render matplotlib-based node decision trees, extracting legacy repetitive code."""
  os.makedirs(os.path.dirname(output_path), exist_ok=True)
  plt.figure(figsize=figsize)
  ax = plt.gca()
  ax.axis('off')

  for k, v in nodes.items():
    pos_x, pos_y = float(v["pos"][0]), float(v["pos"][1])
    ax.text(pos_x,
            pos_y,
            str(v["label"]),
            size=v.get("size", 10),
            ha="center",
            va="center",
            bbox={
                "boxstyle": "round,pad=0.5",
                "facecolor": str(v["color"]),
                "edgecolor": "black",
                "alpha": 0.9
            })

  edge_labels = edge_labels or {}
  for start, end in edges:
    if start not in nodes or end not in nodes:
      continue
    start_x, start_y = float(nodes[start]["pos"][0]), float(
        nodes[start]["pos"][1])
    end_x, end_y = float(nodes[end]["pos"][0]), float(nodes[end]["pos"][1])

    ax.annotate("",
                xy=(end_x, end_y + 0.05),
                xycoords='data',
                xytext=(start_x, start_y - 0.05),
                textcoords='data',
                arrowprops={
                    "arrowstyle": "->",
                    "color": "black",
                    "lw": 1.5,
                    "shrinkA": 5,
                    "shrinkB": 5
                })

    label = edge_labels.get((start, end), "")
    if label:
      ax.text((start_x + end_x) / 2.0, (start_y + end_y) / 2.0,
              label,
              fontsize=8,
              ha='center',
              va='center',
              backgroundcolor='white')

  plt.title(title, fontsize=16, fontweight='bold', y=1.0)
  plt.xlim(0, 1.25)
  plt.ylim(-0.1, 1.1)
  plt.savefig(output_path, bbox_inches='tight', dpi=150)
  plt.close()


def calculate_technical_metrics(df: pd.DataFrame) -> Dict[str, Any]:
  """Calculates RSI, Moving Averages, MACD, and Risk Metrics from a raw price dataframe."""
  if df.empty or len(df) < 200:
    return {}

  close = df['Close']
  vol = df['Volume']

  # RSI (14 day)
  rsi = compute_rsi(close, window=14)
  current_rsi = rsi.iloc[-1]

  # MAs
  ma20 = close.rolling(window=20).mean().iloc[-1]
  ma50 = close.rolling(window=50).mean().iloc[-1]
  ma200 = close.rolling(window=200).mean().iloc[-1]
  current_price = close.iloc[-1]

  dist_to_200ma = ((current_price - ma200) / ma200) * 100
  dist_to_50ma = ((current_price - ma50) / ma50) * 100
  ma_cross = "Golden" if ma50 > ma200 else "Death"

  # MACD
  ema12 = close.ewm(span=12, adjust=False).mean()
  ema26 = close.ewm(span=26, adjust=False).mean()
  macd = ema12.iloc[-1] - ema26.iloc[-1]

  # Volume Momentum
  vol_5d = vol.tail(5).mean()
  vol_20d = vol.tail(20).mean()
  vol_momentum = vol_5d / vol_20d if vol_20d > 0 else 1.0

  # 5D Return
  ret_5d = ((current_price - close.iloc[-6]) / close.iloc[-6]) * 100

  # Historical Volatility & Sharpe (1yr)
  log_ret = pd.Series(np.log(close / close.shift(1)))
  volatility_20d = log_ret.tail(20).std() * np.sqrt(252) * 100
  volatility_252d = log_ret.tail(252).std() * np.sqrt(252) * 100

  close_1y = close.tail(252)
  if len(close_1y) >= 200:
    ann_ret = (close_1y.iloc[-1] / close_1y.iloc[0] - 1) * 100
    sharpe = (ann_ret - 4.2) / volatility_252d if volatility_252d > 0 else 0

    roll_max = close_1y.cummax()
    drawdown = (close_1y / roll_max) - 1.0
    max_dd = drawdown.min() * 100
  else:
    sharpe = np.nan
    max_dd = np.nan

  # Q3 2025 Performance (approx Sept 30 2025 to Current)
  q3_end_date = pd.to_datetime('2025-09-30')
  q3_df = df[df['Date'] >= q3_end_date]
  if not q3_df.empty:
    q3_price = q3_df.iloc[0]['Close']
    ret_since_q3 = ((current_price - q3_price) / q3_price) * 100
  else:
    ret_since_q3 = np.nan

  return {
      "RSI": round(current_rsi, 1),
      "MA50": round(ma50, 2),
      "MA200": round(ma200, 2),
      "Dist_to_50MA": round(dist_to_50ma, 2),
      "Dist_to_200MA": round(dist_to_200ma, 2),
      "MACD": round(macd, 2),
      "Vol_Momentum": round(vol_momentum, 2),
      "MA_Cross": ma_cross,
      "Trailing_5D_Ret": round(ret_5d, 2),
      "Volatility_20D": round(volatility_20d, 2),
      "Max_Drawdown_1Y": round(max_dd, 2),
      "Sharpe_1Y": round(sharpe, 2),
      "Ret_Since_Q3_25": round(ret_since_q3, 2),
      "Current_Price": round(current_price, 2)
  }


def get_technical_indicators(ticker: str, tickers_dir: str) -> Dict[str, Any]:
  """Retrieves a minimal set of technical indicators specifically formatted for single-ticker lookups."""
  try:
    prices = pd.read_csv(os.path.join(tickers_dir, ticker, "prices.tsv"),
                         sep="\t")
    prices['Date'] = pd.to_datetime(prices['Date'])
    prices = prices.sort_values('Date').reset_index(drop=True)
    prices['MA200'] = prices['Close'].rolling(window=200).mean()
    prices['RSI'] = compute_rsi(prices['Close'])

    last_row = prices.iloc[-1]
    dist_200 = (
        (last_row['Close'] - last_row['MA200']) / last_row['MA200']) * 100
    last5_return = (last_row['Close'] / prices.iloc[-6]['Close'] - 1) * 100

    # Historical Volatility & Sharpe (1yr)
    log_ret = pd.Series(np.log(prices['Close'] / prices['Close'].shift(1)))
    volatility_20d = log_ret.tail(20).std() * np.sqrt(252) * 100
    volatility_252d = log_ret.tail(252).std() * np.sqrt(252) * 100

    close_1y = prices['Close'].tail(252)
    sharpe = np.nan
    if len(close_1y) >= 200:
      ann_ret = (close_1y.iloc[-1] / close_1y.iloc[0] - 1) * 100
      sharpe = (ann_ret - 4.2) / volatility_252d if volatility_252d > 0 else 0

    return {
        "Ticker":
            ticker,
        "Close":
            f"${last_row['Close']:.2f}",
        "RSI":
            round(last_row['RSI'], 1),
        "Dist_to_200MA":
            round(dist_200, 1),
        "Trailing_5D_Ret":
            round(last5_return, 1),
        "Volatility_20D":
            round(volatility_20d, 2)
            if not np.isnan(volatility_20d) else np.nan,
        "Sharpe_1Y":
            round(sharpe, 2) if not np.isnan(sharpe) else np.nan
    }
  except Exception as e:
    logger.warning("Could not calculate minimal technicals for %s: %s", ticker,
                   e)
    return {}


def get_intrinsic_value_metrics(ticker: str,
                                tickers_dir: str) -> Dict[str, Any]:
  """Retrieves Graham Intrinsic Value and Discount metrics from fundamentals."""
  try:
    fund_path = os.path.join(tickers_dir, ticker, "fundamentals.tsv")
    if not os.path.exists(fund_path):
      return {}

    df = pd.read_csv(fund_path, sep="\t", names=['Metric', 'Value'], header=0)
    df.set_index('Metric', inplace=True)

    graham_val = df.loc[
        'graham_intrinsic_value',
        'Value'] if 'graham_intrinsic_value' in df.index else np.nan
    discount = df.loc[
        'discount_to_intrinsic_value',
        'Value'] if 'discount_to_intrinsic_value' in df.index else np.nan

    return {
        "Ticker":
            ticker,
        "Graham_Value":
            float(str(graham_val)) if pd.notna(graham_val) and
            str(graham_val).lower() != 'nan' else np.nan,
        "Discount_to_Intrinsic_Value_Pct":
            float(str(discount))
            if pd.notna(discount) and str(discount).lower() != 'nan' else np.nan
    }
  except Exception as e:
    logger.warning("Could not retrieve intrinsic value metrics for %s: %s",
                   ticker, e)
    return {}


# ==========================================
# ADVANCED VISUALIZATIONS
# ==========================================


def generate_sector_risk_return_plot(
    df: pd.DataFrame,
    output_path: str,
    sector_col: str = 'Sector',
    title: str = 'Sector Risk-Return Profile') -> None:
  """Plots sector-level Sharpe ratio vs volatility scatter.

  Args:
    df: DataFrame with Sector, Sharpe_1Y, Volatility_20D columns.
    output_path: Path to save the plot.
    sector_col: Column name for sector grouping.
    title: Plot title.
  """
  required = {sector_col, 'Sharpe_1Y', 'Volatility_20D'}
  if df.empty or not required.issubset(df.columns):
    logger.warning("Missing columns for sector risk-return plot.")
    return
  plot_df = df.dropna(subset=['Sharpe_1Y', 'Volatility_20D']).copy()
  if plot_df.empty:
    return
  sector_stats = plot_df.groupby(sector_col).agg(
      mean_sharpe=('Sharpe_1Y', 'mean'),
      mean_vol=('Volatility_20D', 'mean'),
  ).reset_index()
  if sector_stats.empty:
    return

  setup_plot_aesthetics()
  os.makedirs(os.path.dirname(output_path), exist_ok=True)
  fig, ax = plt.subplots(figsize=(10, 8))
  palette = sns.color_palette('husl', n_colors=len(sector_stats))

  for i, row in sector_stats.iterrows():
    ax.scatter(row['mean_vol'],
               row['mean_sharpe'],
               color=palette[i],
               s=120,
               edgecolor='black',
               zorder=3)
    ax.annotate(row[sector_col], (row['mean_vol'], row['mean_sharpe']),
                textcoords='offset points',
                xytext=(8, 4),
                fontsize=9,
                fontweight='bold')

  # Quadrant lines at mean-of-means.
  vol_mean = sector_stats['mean_vol'].mean()
  sharpe_mean = sector_stats['mean_sharpe'].mean()
  ax.axhline(sharpe_mean,
             color='gray',
             linestyle='--',
             linewidth=0.8,
             alpha=0.6)
  ax.axvline(vol_mean, color='gray', linestyle='--', linewidth=0.8, alpha=0.6)

  ax.set_xlabel('Mean 20-Day Volatility (%)', fontsize=12)
  ax.set_ylabel('Mean 1Y Sharpe Ratio', fontsize=12)
  ax.set_title(title, fontweight='bold', fontsize=14)
  plt.tight_layout()
  plt.savefig(output_path, dpi=300)
  plt.close()
  logger.info("Saved sector risk-return plot to %s", output_path)


def generate_screening_scatter(df: pd.DataFrame, output_path: str):
  """Generates the EPS Surprise vs. Intrinsic Value Discount scatter plot."""
  if df.empty or 'Discount_to_Intrinsic_Value_Pct' not in df or 'Last_EPS_Surprise_Pct' not in df:
    logger.warning("No data to plot scatter.")
    return

  setup_plot_aesthetics()

  # Tighter outlier filtering for better zoom and readability
  plot_df = df.dropna(
      subset=['Discount_to_Intrinsic_Value_Pct', 'Last_EPS_Surprise_Pct'
             ]).copy()

  if plot_df.empty:
    return

  # Calculate IQR to remove extreme outliers dynamically
  q1_disc = plot_df['Discount_to_Intrinsic_Value_Pct'].quantile(0.15)
  q3_disc = plot_df['Discount_to_Intrinsic_Value_Pct'].quantile(0.85)
  iqr_disc = q3_disc - q1_disc

  q1_eps = plot_df['Last_EPS_Surprise_Pct'].quantile(0.15)
  q3_eps = plot_df['Last_EPS_Surprise_Pct'].quantile(0.85)
  iqr_eps = q3_eps - q1_eps

  plot_df = plot_df[
      (plot_df['Discount_to_Intrinsic_Value_Pct'] >= q1_disc - 1.5 * iqr_disc) &
      (plot_df['Discount_to_Intrinsic_Value_Pct'] <= q3_disc + 1.5 * iqr_disc)]
  plot_df = plot_df[
      (plot_df['Last_EPS_Surprise_Pct'] >= q1_eps - 1.5 * iqr_eps) &
      (plot_df['Last_EPS_Surprise_Pct'] <= q3_eps + 1.5 * iqr_eps)]

  plt.figure(figsize=(14, 10))

  # Simple Quadrant logic highlighting Actionable vs Value Trap zones
  plt.axhline(0, color='black', alpha=0.3, linestyle='--')
  plt.axvline(0, color='black', alpha=0.3, linestyle='--')

  # Shade the "Deep Value / Holy Grail" Quadrant (Positive Discount, Positive EPS Surprise)
  plt.axvspan(0,
              q3_eps + 1.5 * iqr_eps,
              ymin=0.5,
              ymax=1,
              alpha=0.08,
              color='green')

  # Shade the "Value Trap" Quadrant (Positive Discount, Negative EPS Surprise)
  plt.axvspan(q1_eps - 1.5 * iqr_eps,
              0,
              ymin=0.5,
              ymax=1,
              alpha=0.08,
              color='red')

  # Fallback size value if 'Current_Price' isn't available in standard TSV passes
  size_col = 'Current_Value' if 'Current_Value' in plot_df else 'Current_Price' if 'Current_Price' in plot_df else None

  scatter = sns.scatterplot(data=plot_df,
                            x='Last_EPS_Surprise_Pct',
                            y='Discount_to_Intrinsic_Value_Pct',
                            hue='Ticker',
                            palette='viridis',
                            size=size_col,
                            sizes=(30, 300) if size_col else None,
                            alpha=0.7,
                            edgecolor='black',
                            legend=False)

  # Annotate all points shown on the scatter
  for i in range(plot_df.shape[0]):
    plt.text(x=plot_df['Last_EPS_Surprise_Pct'].iloc[i] + 0.3,
             y=plot_df['Discount_to_Intrinsic_Value_Pct'].iloc[i] + 0.3,
             s=plot_df['Ticker'].iloc[i],
             fontdict={
                 "color": 'black',
                 "weight": "bold",
                 "size": 8
             })

  plt.title('Value Screener: Intrinsic Value Discount vs. Last EPS Surprise',
            fontweight='bold',
            fontsize=16)
  plt.xlabel('Most Recent EPS Surprise (%)', fontsize=12)
  plt.ylabel('Discount to Graham Intrinsic Value (%)', fontsize=12)

  plt.grid(True, alpha=0.3)
  plt.tight_layout()
  plt.savefig(output_path, dpi=300)
  plt.close()
  logger.info(f"Saved Screener Scatter plot to {output_path}")


def generate_risk_return_scatter(df: pd.DataFrame, output_path: str):
  """Plots 20-Day Volatility vs. Sharpe Ratio to visualize speculative risk/reward profile."""
  if df.empty or 'Volatility_20D' not in df or 'Sharpe_1Y' not in df:
    logger.warning("No data to plot risk scatter.")
    return

  # Use the aesthetic routine from advanced plots
  plt.style.use('seaborn-v0_8-whitegrid')

  plot_df = df.dropna(subset=['Volatility_20D', 'Sharpe_1Y']).copy()
  if plot_df.empty:
    return

  plt.figure(figsize=(12, 9))

  # Simple Quadrant logic highlighting High Risk vs Good Return zones
  avg_vol = plot_df['Volatility_20D'].mean()
  avg_sharpe = plot_df['Sharpe_1Y'].mean()

  plt.axvline(avg_vol, color='gray', alpha=0.4, linestyle='--')
  plt.axhline(avg_sharpe, color='gray', alpha=0.4, linestyle='--')

  size_col = 'Current_Value' if 'Current_Value' in plot_df else 'Current_Price' if 'Current_Price' in plot_df else None

  scatter = sns.scatterplot(data=plot_df,
                            x='Volatility_20D',
                            y='Sharpe_1Y',
                            hue='Ticker',
                            palette='viridis',
                            size=size_col,
                            sizes=(40, 400) if size_col else None,
                            alpha=0.8,
                            edgecolor='black',
                            legend=False)

  # Annotations
  for i in range(plot_df.shape[0]):
    plt.text(x=plot_df['Volatility_20D'].iloc[i] +
             (plot_df['Volatility_20D'].max() * 0.01),
             y=plot_df['Sharpe_1Y'].iloc[i] +
             (plot_df['Sharpe_1Y'].max() * 0.01),
             s=plot_df['Ticker'].iloc[i],
             fontdict={
                 "color": 'black',
                 "weight": "bold",
                 "size": 9
             })

  plt.title('Risk-Return Matrix: 20-Day Volatility vs. Sharpe Ratio',
            fontweight='bold',
            fontsize=16)
  plt.xlabel('20-Day Volatility (StdDev %)', fontsize=12)
  plt.ylabel('1-Year Sharpe Ratio (Annualized)', fontsize=12)

  plt.grid(True, alpha=0.3)
  plt.tight_layout()
  plt.savefig(output_path, dpi=300)
  plt.close()
  logger.info(f"Saved Risk-Return Scatter plot to {output_path}")


def build_decision_tree(df: pd.DataFrame, out_path: str):
  """Generates a quantitative Graphviz decision tree mapping value actionability."""
  if df.empty or 'Discount_to_Intrinsic_Value_Pct' not in df or 'Last_EPS_Surprise_Pct' not in df:
    logger.warning("No data to plot decision tree.")
    return

  logger.info("Rendering Graphviz Value Decision Tree...")
  dot = Digraph(comment='Value Execution Tree')
  setup_decision_tree_aesthetics(dot)

  # Core Pipeline state at head
  dot.node(
      'A',
      f"Intrinsic Value\nScreener Matrix\n({datetime.date.today().strftime('%b %d, %Y')})",
      shape='box',
      style='filled',
      fillcolor='lightblue')

  # Identify extreme groupings if data exists
  deep_value = df[df['Discount_to_Intrinsic_Value_Pct'] > 40]['Ticker'].head(
      3).tolist()
  fair_value = df[(df['Discount_to_Intrinsic_Value_Pct'] > 0) & (
      df['Discount_to_Intrinsic_Value_Pct'] <= 40)]['Ticker'].head(3).tolist()
  overvalued = df[df['Discount_to_Intrinsic_Value_Pct'] < -20]['Ticker'].head(
      3).tolist()
  value_traps = df[(df['Discount_to_Intrinsic_Value_Pct'] > 20) & (
      df['Last_EPS_Surprise_Pct'] < 0)]['Ticker'].head(3).tolist()

  dot.node('B1',
           'Deep Value\n(Discount > 40%)',
           style='filled',
           fillcolor='lightgreen')
  dot.node('B2',
           'Fair Value\n(Discount 0% - 40%)',
           style='filled',
           fillcolor='lightyellow')
  dot.node('B3',
           'Overvalued Risk\n(Premium > 20%)',
           style='filled',
           fillcolor='lightcoral')
  dot.node('B4',
           'Value Traps\n(Discount > 20%, EPS Miss)',
           style='filled',
           fillcolor='lightgray')

  dot.edge('A', 'B1', label='Margin of Safety')
  dot.edge('A', 'B2', label='Steady Accumulation')
  dot.edge('A', 'B3', label='Capitulation Risk')
  dot.edge('A', 'B4', label='Fading Fundamentals')

  # Dynamic Allocations
  dot.node(
      'C1',
      f"BUY / CALL LEAPS:\n{', '.join(deep_value) if deep_value else 'No candidates'}",
      shape='ellipse')
  dot.node(
      'C2',
      f"HOLD / SELL PUTS:\n{', '.join(fair_value) if fair_value else 'No candidates'}",
      shape='ellipse')
  dot.node(
      'C3',
      f"TRIM EXPOSURE:\n{', '.join(overvalued) if overvalued else 'No candidates'}",
      shape='ellipse')
  dot.node(
      'C4',
      f"AVOID / SHORT:\n{', '.join(value_traps) if value_traps else 'No candidates'}",
      shape='ellipse')

  dot.edge('B1', 'C1')
  dot.edge('B2', 'C2')
  dot.edge('B3', 'C3')
  dot.edge('B4', 'C4')

  dot.render(out_path, format='png', cleanup=True)


# ==========================================
# DATA PIPELINE INTEGRATION (I/O)
# ==========================================


def load_macro_snapshot(market_data_dir: str) -> Dict[str, Any]:
  """Loads the latest macro economic indicators.

  Reads economic_indicators.tsv and returns a dict of the most
  recent non-NaN value for key indicators: FEDFUNDS, US10Y, US02Y,
  CPI, UNRATE, HY_SPREAD, WTI_CRUDE, USD_INDEX, RECESSION_PROB,
  UMICH_SENTIMENT, US_POLICY_UNCERTAINTY, GDP, M2_MONEY.

  Args:
    market_data_dir: Path to the market_data directory.

  Returns:
    Dict mapping indicator names to their latest values.
  """
  indicators = [
      'FEDFUNDS',
      'US10Y',
      'US02Y',
      'CPI',
      'UNRATE',
      'HY_SPREAD',
      'WTI_CRUDE',
      'USD_INDEX',
      'RECESSION_PROB',
      'UMICH_SENTIMENT',
      'US_POLICY_UNCERTAINTY',
      'GDP',
      'M2_MONEY',
  ]
  tsv_path = os.path.join(market_data_dir, 'macro', 'economic_indicators.tsv')
  if not os.path.exists(tsv_path):
    logger.warning("Macro indicators file not found: %s", tsv_path)
    return {}
  try:
    df = pd.read_csv(tsv_path, sep='\t', index_col='DATE', parse_dates=True)
  except (pd.errors.ParserError, ValueError) as e:
    logger.error("Failed to parse macro indicators: %s", e)
    return {}
  snapshot: Dict[str, Any] = {}
  for col in indicators:
    if col not in df.columns:
      logger.debug("Indicator %s not in macro data.", col)
      continue
    series = pd.to_numeric(df[col], errors='coerce').dropna()
    if series.empty:
      continue
    snapshot[col] = float(series.iloc[-1])
  return snapshot


def get_news_sentiment_summary(ticker: str,
                               market_data_dir: str,
                               days: int = 30) -> Dict[str, Any]:
  """Computes aggregate news sentiment for a ticker.

  Args:
    ticker: Stock ticker symbol.
    market_data_dir: Path to market_data directory.
    days: Number of days of recent news to analyze.

  Returns:
    Dict with avg_sentiment, positive_count, negative_count,
    neutral_count, and total_articles.
  """
  news_path = os.path.join(market_data_dir, 'tickers', ticker, 'news.tsv')
  if not os.path.exists(news_path):
    logger.warning("News file not found for %s: %s", ticker, news_path)
    return {}
  try:
    df = pd.read_csv(news_path, sep='\t', parse_dates=['Date'])
  except (pd.errors.ParserError, ValueError) as e:
    logger.error("Failed to parse news for %s: %s", ticker, e)
    return {}
  if df.empty or 'Sentiment' not in df.columns:
    return {}
  cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
  recent = df[df['Date'] >= cutoff].copy()
  if recent.empty:
    return {
        'avg_sentiment': 0.0,
        'positive_count': 0,
        'negative_count': 0,
        'neutral_count': 0,
        'total_articles': 0,
    }
  sentiments = pd.to_numeric(recent['Sentiment'], errors='coerce').dropna()
  positive = int((sentiments > 0.1).sum())
  negative = int((sentiments < -0.1).sum())
  neutral = int(len(sentiments) - positive - negative)
  return {
      'avg_sentiment': round(float(sentiments.mean()), 4),
      'positive_count': positive,
      'negative_count': negative,
      'neutral_count': neutral,
      'total_articles': len(sentiments),
  }


def generate_eps_surprise_scatter(df: pd.DataFrame, output_path: str):
  """
  Plot Unrealized PnL % vs Latest EPS Surprise % for Active Holdings.
  Visualizes whether portfolio gains correspond to earnings momentum vs. hype.
  """
  if df.empty or 'Last_EPS_Surprise_Pct' not in df or 'Unrealized_PnL_Pct' not in df:
    logger.warning("No EPS Surprise data to plot active scatter.")
    return

  # Filter out rows with NaN in these columns
  plot_df = df.dropna(
      subset=['Last_EPS_Surprise_Pct', 'Unrealized_PnL_Pct']).copy()
  if plot_df.empty:
    logger.warning("No valid overlapping EPS/PnL data to plot active scatter.")
    return

  logger.info("Generating Active EPS Surprise Scatter plot...")
  fig, ax = plt.subplots(figsize=(10, 8))

  # Create scatter with sizes proportional to position size (log scaled for viewability)
  sizes = np.log1p(plot_df['Current_Value']) * 20

  scatter = ax.scatter(plot_df['Last_EPS_Surprise_Pct'],
                       plot_df['Unrealized_PnL_Pct'],
                       c=plot_df['Day_Change_Pct'],
                       cmap='RdYlGn',
                       s=sizes,
                       alpha=0.7,
                       edgecolors='black')

  # Annotate all positions
  for _, row in plot_df.iterrows():
    ax.annotate(row['Ticker'],
                (row['Last_EPS_Surprise_Pct'], row['Unrealized_PnL_Pct']),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=9)

  # Add zero-lines
  ax.axhline(0, color='gray', linestyle='--', alpha=0.5)
  ax.axvline(0, color='gray', linestyle='--', alpha=0.5)

  # Quadrant Labels
  ax.text(0.02,
          0.98,
          "High Surprise\nBig Winners",
          transform=ax.transAxes,
          alpha=0.3,
          fontsize=12,
          verticalalignment='top')
  ax.text(0.98,
          0.02,
          "High Surprise\nUnderperformers",
          transform=ax.transAxes,
          alpha=0.3,
          fontsize=12,
          verticalalignment='bottom',
          horizontalalignment='right')

  cbar = plt.colorbar(scatter)
  cbar.set_label('Daily Change %')

  plt.grid(True, linestyle=':', alpha=0.6)
  plt.title("Active Holdings: Unrealized PnL vs. Last Earnings Surprise")
  plt.xlabel("Latest EPS Surprise (%)")
  plt.ylabel("Unrealized PnL (%)")
  plt.tight_layout()

  plt.savefig(output_path, bbox_inches='tight', dpi=300)
  plt.close()


def generate_rsi_dist200_scatter(
    df: pd.DataFrame,
    output_path: str,
    title: str = "Technical Extension: RSI vs Distance to 200MA"):
  """Plot RSI vs Distance to 200MA.

  Identifies overextended vs oversold conditions for rotation timing.
  """
  if df.empty or 'RSI' not in df or 'Dist_to_200MA' not in df:
    logger.warning("No RSI/200MA data to plot scatter.")
    return

  plot_df = df.dropna(subset=['RSI', 'Dist_to_200MA']).copy()
  if plot_df.empty:
    return

  logger.info("Generating RSI vs 200MA Scatter plot...")
  setup_plot_aesthetics()
  fig, ax = plt.subplots(figsize=(10, 8))

  sizes = np.log1p(plot_df['Current_Value'].fillna(1000)) * 20

  scatter = ax.scatter(plot_df['RSI'],
                       plot_df['Dist_to_200MA'],
                       c=plot_df['RSI'],
                       cmap='coolwarm',
                       s=sizes,
                       alpha=0.7,
                       edgecolors='black')

  for _, row in plot_df.iterrows():
    ax.annotate(row['Ticker'], (row['RSI'], row['Dist_to_200MA']),
                xytext=(5, 5),
                textcoords='offset points',
                fontsize=9)

  ax.axhline(0, color='gray', linestyle='--', alpha=0.5)
  ax.axvline(50, color='gray', linestyle='--', alpha=0.5)
  ax.axvline(30, color='green', linestyle=':', alpha=0.5)
  ax.axvline(70, color='red', linestyle=':', alpha=0.5)

  ax.text(0.98,
          0.98,
          "Overbought & Overextended\n(Take Profits)",
          transform=ax.transAxes,
          alpha=0.3,
          fontsize=12,
          verticalalignment='top',
          horizontalalignment='right')
  ax.text(0.02,
          0.02,
          "Oversold & Below Trend\n(Deep Value)",
          transform=ax.transAxes,
          alpha=0.3,
          fontsize=12,
          verticalalignment='bottom')

  cbar = plt.colorbar(scatter)
  cbar.set_label('RSI')

  plt.title(title, fontweight='bold', fontsize=14)
  plt.xlabel('RSI (Momentum)', fontweight='bold')
  plt.ylabel('Distance to 200MA (%) (Trend Extension)', fontweight='bold')

  plt.tight_layout()
  plt.savefig(output_path, bbox_inches='tight', dpi=300)
  plt.close()
  logger.info(f"Generated RSI Scatter at {output_path}")


def generate_semiconductor_moat_watch_plot(
    df_stocks: pd.DataFrame,
    output_path: str,
    target_tickers: Optional[List[str]] = None):
  """Plots PnL % vs 200MA Extension for Semiconductor moat leaders with white background styling."""
  setup_plot_aesthetics()
  target_tickers = target_tickers or ['NVDA', 'TSM', 'AMD', 'AVGO']
  semi_df = df_stocks[df_stocks['Ticker'].isin(target_tickers)].copy()
  if semi_df.empty:
    return

  fig, ax = plt.subplots(figsize=(10, 6))
  x = np.arange(len(semi_df))
  width = 0.35

  ax.bar(x - width / 2,
         semi_df['Unrealized_PnL_Pct'],
         width,
         label='Unrealized PnL %',
         color='#27ae60',
         edgecolor='black',
         alpha=0.85)
  ax.bar(x + width / 2,
         semi_df['Dist_to_200MA'],
         width,
         label='Dist 200MA %',
         color='#e74c3c',
         edgecolor='black',
         alpha=0.85)

  ax.set_xticks(x)
  ax.set_xticklabels(semi_df['Ticker'], fontweight='bold', fontsize=11)
  ax.set_title('Semiconductor Moat Leaders: PnL % vs 200MA Extension',
               fontsize=14,
               fontweight='bold')
  ax.set_ylabel('Percentage (%)', fontweight='bold')
  ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
  ax.legend(frameon=True, facecolor='white', edgecolor='gray')
  ax.grid(True, alpha=0.3)

  plt.tight_layout()
  plt.savefig(output_path, bbox_inches='tight', dpi=300)
  plt.close()
  logger.info(f"Generated Semiconductor Moat Watch Plot at {output_path}")


def analyze_earnings_movement(ticker: str,
                              market_data_dir: str) -> pd.DataFrame:
  """Computes post-earnings price reactions (T0 close -> T1 open/high/close) for a generic ticker."""
  try:
    earnings = pd.read_csv(os.path.join(market_data_dir,
                                        f"tickers/{ticker}/earnings.tsv"),
                           sep="\t")
    prices = pd.read_csv(os.path.join(market_data_dir,
                                      f"tickers/{ticker}/prices.tsv"),
                         sep="\t")

    prices['Date'] = pd.to_datetime(prices['Date']).dt.date
    prices = prices.sort_values('Date').reset_index(drop=True)

    earnings = earnings.dropna(subset=['Reported EPS'])  # Drop future
    earnings['Earnings Date'] = pd.to_datetime(earnings['Earnings Date'],
                                               utc=True)
    earnings['Date'] = earnings['Earnings Date'].dt.tz_convert(
        'America/New_York').dt.date

    results = []

    for _, row in earnings.iterrows():
      edate = row['Date']

      t0_idx = prices.index[prices['Date'] == edate].tolist()
      if not t0_idx:
        t0_idx = prices.index[prices['Date'] < edate].tolist()
        if not t0_idx:
          continue
        t0_idx = [t0_idx[-1]]

      t0_idx = t0_idx[0]

      if t0_idx + 1 >= len(prices):
        continue
      t1_idx = t0_idx + 1

      t0_row = prices.iloc[t0_idx]
      t1_row = prices.iloc[t1_idx]

      t0_close = t0_row['Close']
      t1_open = t1_row['Open']
      t1_high = t1_row['High']
      t1_close = t1_row['Close']

      open_pct = (t1_open - t0_close) / t0_close * 100
      close_pct = (t1_close - t0_close) / t0_close * 100
      high_pct = (t1_high - t0_close) / t0_close * 100

      results.append({
          'Earnings_Date': edate,
          'Surprise_Pct': row['Surprise(%)'],
          'T0_Close': t0_close,
          'T1_Open': t1_open,
          'T1_High': t1_high,
          'T1_Close': t1_close,
          'Open_Change_Pct': open_pct,
          'High_Change_Pct': high_pct,
          'Close_Change_Pct': close_pct
      })

    df = pd.DataFrame(results)
    df = df.sort_values('Earnings_Date', ascending=True).reset_index(drop=True)
    return df
  except Exception as e:
    logger.warning("Error computing earnings movement for %s: %s", ticker, e)
    return pd.DataFrame()


def get_recent_news(
    topic: str,
    market_data_dir: str,
    limit: int = 40,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None) -> pd.DataFrame:
  """Retrieves the most recent news headlines for a generalized topic."""
  try:
    path = os.path.join(market_data_dir, f"topics/{topic}/news.tsv")
    news = pd.read_csv(path, sep="	")
    news['Date'] = pd.to_datetime(news['Date'])
    if start_date:
      news = news[news['Date'] >= start_date]
    if end_date:
      news = news[news['Date'] <= end_date]

    news = news.sort_values('Date', ascending=False)

    # If we have a bounded range, include everything up to a reasonable cap (e.g., 50)
    # If it exceeds the cap, sample systematically to fit the cap to prevent huge payloads
    if start_date and end_date:
      cap = max(limit, 50)  # Fallback to 50 if limit is low but we are bounded
      if len(news) > cap:
        indices = np.linspace(0, len(news) - 1, cap, dtype=int)
        return news.iloc[indices]
      return news

    return news.head(limit)
  except FileNotFoundError:
    logger.debug("News file not found for topic %s.", topic)
    return pd.DataFrame()
  except Exception as e:
    logger.warning("Could not retrieve generic news for topic %s: %s", topic, e)
    return pd.DataFrame()


def get_recent_ticker_news(
    ticker: str,
    market_data_dir: str,
    limit: int = 40,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None) -> pd.DataFrame:
  """Retrieves the most recent news headlines for a specific ticker."""
  try:
    path = os.path.join(market_data_dir, f"tickers/{ticker}/news.tsv")
    news = pd.read_csv(path, sep="	")
    news['Date'] = pd.to_datetime(news['Date'])
    if start_date:
      news = news[news['Date'] >= start_date]
    if end_date:
      news = news[news['Date'] <= end_date]

    news = news.sort_values('Date', ascending=False)

    # If we have a bounded range, include everything up to a reasonable cap (e.g., 50)
    if start_date and end_date:
      cap = max(limit, 50)
      if len(news) > cap:
        indices = np.linspace(0, len(news) - 1, cap, dtype=int)
        return news.iloc[indices]
      return news

    return news.head(limit)
  except FileNotFoundError:
    logger.debug("News file not found for ticker %s.", ticker)
    return pd.DataFrame()
  except Exception as e:
    logger.warning("Could not retrieve news for ticker %s: %s", ticker, e)
    return pd.DataFrame()


def _is_similar(text1: str, text2: str, threshold: float = 0.6) -> bool:
  if not pd.notna(text1) or not pd.notna(text2):
    return False
  seq = difflib.SequenceMatcher(None, str(text1).lower(), str(text2).lower())
  return seq.ratio() > threshold


def format_recent_news_markdown(
    topics: Dict[str, str],
    market_data_dir: str,
    tickers: Optional[List[str]] = None,
    max_items: int = 15,
    max_per_source: int = 2,
    target_date: Optional[datetime.datetime] = None) -> str:
  """Takes a dict of {topic_dir_name: Display Label} and/or a list of tickers,

  aggregates, deduplicates via fuzzy matching, enforces per-source caps,
  and returns a formatted Markdown string.
  """
  all_news = []
  tickers = tickers or []

  for topic, label in topics.items():
    df = get_recent_news(topic, market_data_dir, end_date=target_date)
    if df.empty:
      df = get_recent_news(topic.lower(), market_data_dir, end_date=target_date)
    if not df.empty:
      df['Source_Label'] = label
      if target_date:
        df = df[df['Date'] <= target_date]
      all_news.append(df)

  for ticker in tickers:
    df = get_recent_ticker_news(ticker, market_data_dir, end_date=target_date)
    if not df.empty:
      df['Source_Label'] = ticker
      if target_date:
        df = df[df['Date'] <= target_date]
      all_news.append(df)

  if not all_news:
    return ""

  combined_df = pd.concat(all_news, ignore_index=True)

  if 'Date' not in combined_df.columns or 'Headline' not in combined_df.columns:
    return ""

  combined_df = combined_df.sort_values('Date',
                                        ascending=False).reset_index(drop=True)

  news_items: List[str] = []
  seen_headlines: List[str] = []
  source_counts: Dict[str, int] = {}

  for _, row in combined_df.iterrows():
    if not pd.notna(row['Date']) or not pd.notna(row['Headline']):
      continue

    headline = str(row['Headline']).strip()
    label = str(row.get('Source_Label', 'News'))

    if source_counts.get(label, 0) >= max_per_source:
      continue

    # Check similarity
    if any(_is_similar(headline, seen) for seen in seen_headlines):
      continue

    seen_headlines.append(headline)
    source_counts[label] = source_counts.get(label, 0) + 1

    summary_text = ""
    if 'Summary' in row and pd.notna(row['Summary']) and len(
        str(row['Summary']).strip()) > 10:
      summary_raw = str(row['Summary']).strip()
      if len(summary_raw) > 150:
        summary_raw = summary_raw[:147] + "..."
      # Removing potential newlines in summary to not break markdown list
      summary_raw = summary_raw.replace('\\n',
                                        ' ').replace('\\r',
                                                     '').replace('\n', ' ')
      summary_text = f" - *{summary_raw}*"

    date_str = pd.to_datetime(row['Date']).strftime('%m/%d')
    url = row.get('URL', '')

    # Strip any rogue escaped newlines from the headline or url itself just in case
    headline = headline.replace('\\n', ' ').replace('\n', ' ')
    url = str(url).replace('\\n', '').replace('\n', '')

    if url and str(url) != 'nan':
      item = f"- **{label} ({date_str})**: [{headline}]({url}){summary_text}"
    else:
      item = f"- **{label} ({date_str})**: {headline}{summary_text}"

    news_items.append(item)

    if len(news_items) >= max_items:
      break

  if news_items:
    return "\n".join(news_items) + "\n\n"
  return ""


def build_ticker_context_markdown(tickers: List[str],
                                  market_data_dir: str) -> str:
  """Builds a dense Markdown string containing Intrinsic Value and Recent News for a specific list of tickers.
  Useful for injecting bespoke context into LLM prompts.
  """
  if not tickers:
    return ""

  context = "### Detailed Portfolio Context (News & Intrinsic Value)\n"
  for t in tickers:
    # Fetch Intrinsic Value
    metrics = get_intrinsic_value_metrics(
        t, os.path.join(market_data_dir, "tickers"))
    if metrics:
      discount = metrics.get('Discount_to_Intrinsic_Value_Pct')
      if discount is not None and pd.notna(discount):
        context += f"- **{t}**: Intrinsic Discount: {discount:.1f}%\n"
      else:
        context += f"- **{t}**: Intrinsic Discount: N/A\n"

    # Fetch Ticker News
    news_df = get_recent_ticker_news(t, market_data_dir, limit=3)
    if not news_df.empty:
      context += f"  - Recent News for {t}:\n"
      for _, r in news_df.iterrows():
        headline = r.get('Headline', '')[:100]
        if headline:
          context += f"    - {headline}...\n"
  return context + "\n"


def generate_portfolio_markdown_table(df: pd.DataFrame) -> str:
  """Generates a clean markdown table of the portfolio using purely relative percentages."""

  # Ensure intrinsic value columns exist even if empty
  if 'Graham_Value' not in df.columns:
    df['Graham_Value'] = np.nan
  if 'Discount_to_Intrinsic_Value_Pct' not in df.columns:
    df['Discount_to_Intrinsic_Value_Pct'] = np.nan

  desired_cols = [
      'Ticker', 'Name', 'Quantity', 'Portfolio_Weight_Pct', 'Cost_Basis',
      'Unrealized_PnL_Net', 'Unrealized_PnL_Pct', 'Graham_Value',
      'Discount_to_Intrinsic_Value_Pct', 'RSI', 'Dist_to_200MA', 'MACD',
      'MA_Cross', 'Upcoming_Earnings', 'Time_Horizon', 'Exit_Strategy'
  ]
  actual_cols = [c for c in desired_cols if c in df.columns]
  display_df = df[actual_cols].copy()

  # Replace NaNs in Discount with N/A BEFORE fillna("-")
  if 'Discount_to_Intrinsic_Value_Pct' in display_df.columns:
    display_df['Discount_to_Intrinsic_Value_Pct'] = display_df[
        'Discount_to_Intrinsic_Value_Pct'].fillna("N/A")

  display_df = display_df.fillna("-")

  if 'Portfolio_Weight_Pct' in display_df.columns:
    display_df['Portfolio_Weight_Pct'] = display_df[
        'Portfolio_Weight_Pct'].apply(lambda x: format_num(x, is_pct=True)
                                      if x != "-" else x)
  if 'Unrealized_PnL_Pct' in display_df.columns:
    display_df['Unrealized_PnL_Pct'] = display_df['Unrealized_PnL_Pct'].apply(
        lambda x: format_num(x, is_pct=True, is_signed=True) if x != "-" else x)

  if 'Cost_Basis' in display_df.columns:
    display_df['Cost_Basis'] = display_df['Cost_Basis'].apply(
        lambda x: format_num(x, prefix="$") if x != "-" else x)
  if 'Unrealized_PnL_Net' in display_df.columns:
    display_df['Unrealized_PnL_Net'] = display_df['Unrealized_PnL_Net'].apply(
        lambda x: format_num(x, prefix="$", is_signed=True) if x != "-" else x)

  if 'Graham_Value' in display_df.columns:
    display_df['Graham_Value'] = display_df['Graham_Value'].apply(
        lambda x: format_num(x, prefix="$") if x != "-" else x)
  if 'Discount_to_Intrinsic_Value_Pct' in display_df.columns:
    display_df['Discount_to_Intrinsic_Value_Pct'] = display_df[
        'Discount_to_Intrinsic_Value_Pct'].apply(lambda x: format_num(
            x, is_pct=True, is_signed=True) if x not in ["-", "N/A"] else x)

  if 'Dist_to_200MA' in display_df.columns:
    display_df['Dist_to_200MA'] = display_df['Dist_to_200MA'].apply(
        lambda x: format_num(x, is_pct=True, is_signed=True) if x != "-" else x)
  if 'RSI' in display_df.columns:
    display_df['RSI'] = display_df['RSI'].apply(lambda x: format_num(x)
                                                if x != "-" else x)
  if 'MACD' in display_df.columns:
    display_df['MACD'] = display_df['MACD'].apply(lambda x: format_num(x)
                                                  if x != "-" else x)

  headers = display_df.columns.tolist()
  data = display_df.values.tolist()
  return tabulate(data, headers=headers, tablefmt='pipe')


# ==========================================
# PLOTTING
# ==========================================


def plot_portfolio_allocation(df: pd.DataFrame, out_path: str):
  """Generates a pie chart of the portfolio allocation without absolute totals."""
  setup_plot_aesthetics()
  plt.figure(figsize=(10, 8))
  # Group small positions
  threshold = 1.0  # Group below 1% to clean chart
  plot_df = df.copy()
  plot_df.loc[plot_df['Portfolio_Weight_Pct'] < threshold, 'Ticker'] = 'Other'
  plot_df = plot_df.groupby(
      'Ticker')['Portfolio_Weight_Pct'].sum().reset_index()

  plt.pie(plot_df['Portfolio_Weight_Pct'],
          labels=plot_df['Ticker'],
          autopct=lambda p: f'{p:.1f}%' if p > 2.0 else '',
          startangle=140,
          colors=sns.color_palette("crest", len(plot_df)),
          textprops={'fontsize': 10})
  plt.title('Current Portfolio Allocation (% Relative Weight)',
            fontweight='bold')
  plt.savefig(out_path, bbox_inches='tight', dpi=300)
  plt.close()


def plot_momentum_scatter(df: pd.DataFrame, out_path: str):
  """Generates a scatter plot of RSI vs Distance to 200MA."""
  setup_plot_aesthetics()
  plt.figure(figsize=(12, 8))
  sns.scatterplot(data=df,
                  x='Dist_to_200MA',
                  y='RSI',
                  s=150,
                  hue='Unrealized_PnL_Pct',
                  palette='vlag',
                  legend=False,
                  edgecolor='black',
                  alpha=0.8)

  for i in range(df.shape[0]):
    plt.text(x=df.Dist_to_200MA[i] + 0.5,
             y=df.RSI[i] + 0.5,
             s=df.Ticker[i],
             fontdict={
                 "color": 'black',
                 "size": 10
             })

  plt.axhline(70,
              color='red',
              linestyle='--',
              alpha=0.5,
              label='Overbought (RSI 70)')
  plt.axhline(30,
              color='green',
              linestyle='--',
              alpha=0.5,
              label='Oversold (RSI 30)')
  plt.axvline(0, color='grey', linestyle='-.', alpha=0.5, label='200 MA Line')

  plt.title('Portfolio Technical Momentum: RSI vs Distance to 200-Day MA',
            fontweight='bold')
  plt.xlabel('Distance to 200-Day MA (%)')
  plt.ylabel('14-Day RSI')
  plt.grid(True, alpha=0.3)
  plt.savefig(out_path, bbox_inches='tight', dpi=300)
  plt.close()


def plot_correlation_heatmap(tickers: List[str],
                             tickers_dir: str,
                             out_path: str,
                             figsize=(14, 12)):
  """Generates a correlation heatmap based on the last 180 days of returns."""
  setup_plot_aesthetics()

  price_dict = {}
  for ticker in tickers:
    filepath = os.path.join(tickers_dir, ticker, "prices.tsv")
    try:
      df = pd.read_csv(filepath, sep='\t')
      df['Date'] = pd.to_datetime(df['Date'])
      df = df.sort_values('Date').tail(180).set_index('Date')
      price_dict[ticker] = df['Close']
    except FileNotFoundError:
      pass

  if not price_dict:
    return

  prices_df = pd.DataFrame(price_dict)
  returns_df = prices_df.pct_change().dropna()
  corr_matrix = returns_df.corr()

  plt.figure(figsize=figsize)
  sns.heatmap(corr_matrix,
              annot=True,
              cmap='vlag',
              vmin=-1,
              vmax=1,
              fmt=".2f",
              linewidths=.5,
              cbar_kws={"shrink": .8})
  plt.title('Portfolio Cross-Asset Correlation (Trailing 6 Months)',
            fontweight='bold')
  plt.savefig(out_path, bbox_inches='tight', dpi=300)
  plt.close()


def plot_winners_losers(df: pd.DataFrame, out_path: str):
  """Plots percentage return of portfolio assets."""
  setup_plot_aesthetics()
  plt.figure(figsize=(12, 8))
  # Filter out cash and sort by % PnL
  plot_df = df[df['Ticker'] != 'CASH'].copy()
  plot_df = plot_df.sort_values('Unrealized_PnL_Pct')
  colors = [
      '#c0392b' if val < 0 else '#27ae60'
      for val in plot_df['Unrealized_PnL_Pct']
  ]

  sns.barplot(x='Unrealized_PnL_Pct',
              y='Ticker',
              data=plot_df,
              hue='Ticker',
              palette=colors,
              legend=False)
  plt.title('Relative Portfolio Winners & Losers (Net P/L %)',
            fontweight='bold')
  plt.xlabel('Net Unrealized P/L (%)')
  plt.ylabel('')
  plt.axvline(0, color='black', linewidth=1)

  for index, (_, row) in enumerate(plot_df.iterrows()):
    val = row['Unrealized_PnL_Pct']
    offset = abs(plot_df['Unrealized_PnL_Pct'].max()) * 0.05
    align = 'left' if val > 0 else 'right'
    x_pos = val + offset if val > 0 else val - offset
    plt.text(x_pos, index, f"{val:+.1f}%", va='center', ha=align, fontsize=10)

  plt.savefig(out_path, bbox_inches='tight', dpi=300)
  plt.close()


def plot_portfolio_rsi(techs: List[Dict[str, Any]], out_path: str):
  """Plots a generic RSI heat check for a list of dictionaries tracking RSI."""
  if not techs:
    return
  df = pd.DataFrame(techs)
  if 'RSI' not in df.columns:
    return
  df = df.sort_values('RSI', ascending=False)
  plt.figure(figsize=(10, 6))
  setup_plot_aesthetics()
  colors = [
      '#e74c3c' if pd.notna(rsi) and rsi >= 70 else
      ('#2ecc71' if pd.notna(rsi) and rsi <= 30 else '#95a5a6')
      for rsi in df['RSI']
  ]
  sns.barplot(x='Ticker',
              y='RSI',
              hue='Ticker',
              data=df,
              palette=colors,
              legend=False)
  plt.axhline(70,
              color='red',
              linestyle='--',
              alpha=0.7,
              label='Overbought Threshold (70)')
  plt.axhline(30,
              color='green',
              linestyle='--',
              alpha=0.7,
              label='Oversold Threshold (30)')
  plt.title("Portfolio RSI (Relative Strength Index) Heat Check",
            fontsize=14,
            fontweight='bold')
  plt.ylabel("14-Day RSI", fontsize=12)
  plt.xlabel("Ticker", fontsize=12)
  plt.legend(loc='best')
  plt.tight_layout()
  plt.savefig(out_path, dpi=300)
  plt.close()


def plot_ma200_distance(techs: List[Dict[str, Any]], out_path: str):
  """Plots a generic moving average structural distance heatmap."""
  if not techs:
    return
  df = pd.DataFrame(techs)
  if 'Dist_to_200MA' not in df.columns:
    return
  df = df.sort_values('Dist_to_200MA', ascending=False)
  plt.figure(figsize=(10, 6))
  setup_plot_aesthetics()
  colors = [
      '#27ae60' if pd.notna(dist) and dist > 0 else '#c0392b'
      for dist in df['Dist_to_200MA']
  ]
  ax = sns.barplot(x='Ticker',
                   y='Dist_to_200MA',
                   hue='Ticker',
                   data=df,
                   palette=colors,
                   legend=False)
  plt.axhline(0, color='black', linewidth=1, linestyle='-')
  plt.title("Portfolio Structural Momentum (Distance to 200-Day MA)",
            fontsize=14,
            fontweight='bold')
  plt.ylabel("Percentage Distance (%)", fontsize=12)
  plt.xlabel("Ticker", fontsize=12)

  for i, v in enumerate(df['Dist_to_200MA']):
    if pd.notna(v):
      ax.text(i,
              v + (1 if v > 0 else -3),
              f"{v:+.1f}%",
              ha='center',
              fontsize=10)

  plt.tight_layout()
  plt.savefig(out_path, dpi=300)
  plt.close()


# ==========================================
# STRING & NUMBER FORMATTING UTILITIES
# ==========================================


def format_num(x, is_pct=False, is_signed=False, prefix="", default_nan="NaN"):
  """Gracefully formats floats avoiding trailing zeros if they represent integers."""
  if pd.isna(x):
    return default_nan
  try:
    x_val = float(x)
  except (ValueError, TypeError):
    return x
  sign = "+" if is_signed and x_val > 0 else ""
  suffix = "%" if is_pct else ""
  if abs(x_val - round(x_val)) < 1e-6:
    return f"{prefix}{sign}{int(round(x_val))}{suffix}"
  return f"{prefix}{sign}{x_val:.2f}{suffix}"


def format_macro_summary_md(macro: Dict[str, Any]) -> str:
  """Formats macro snapshot dict into a markdown table.

  Args:
    macro: Dict from load_macro_snapshot().

  Returns:
    Formatted markdown string with a macro summary table.
  """
  if not macro:
    return "No macro data available.\n"
  display_names = {
      'FEDFUNDS': 'Fed Funds Rate (%)',
      'US10Y': '10Y Treasury (%)',
      'US02Y': '2Y Treasury (%)',
      'CPI': 'CPI Index',
      'UNRATE': 'Unemployment Rate (%)',
      'HY_SPREAD': 'HY Spread (bps)',
      'WTI_CRUDE': 'WTI Crude ($/bbl)',
      'USD_INDEX': 'USD Index',
      'RECESSION_PROB': 'Recession Probability (%)',
      'UMICH_SENTIMENT': 'UMich Sentiment',
      'US_POLICY_UNCERTAINTY': 'Policy Uncertainty',
      'GDP': 'GDP ($B)',
      'M2_MONEY': 'M2 Money Supply ($B)',
  }
  lines = ['| Indicator | Value |', '|---|---|']
  for key, value in macro.items():
    label = display_names.get(key, key)
    if isinstance(value, float):
      formatted = f"{value:,.2f}"
    else:
      formatted = str(value)
    lines.append(f"| {label} | {formatted} |")
  return '\n'.join(lines) + '\n'


# ==========================================
# PORTFOLIO THEMES & CUSTOM PLOTS
# ==========================================

# Ensure project root is in path to import config
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _root not in sys.path:
  sys.path.insert(0, _root)


def get_theme(ticker: str) -> str:
  """Returns the macro sector/theme for a given ticker using config.SECTORS."""
  for sector, tickers in config.SECTORS.items():
    if ticker in tickers:
      return sector
  return "Other"


def load_portfolio_tsv(filepath: str) -> pd.DataFrame:
  """Loads a portfolio TSV file and annotates it with themes."""
  if not os.path.exists(filepath):
    raise FileNotFoundError(f"Missing TSV: {filepath}")
  df = pd.read_csv(filepath, sep="\t")
  if "Ticker" in df.columns:
    df["Theme"] = df["Ticker"].apply(get_theme)
  return df


def enrich_portfolio_df(df: pd.DataFrame, market_data_dir: str) -> pd.DataFrame:
  """Enriches a portfolio DataFrame with intrinsic value and technical metrics."""
  tickers_dir = os.path.join(market_data_dir, "tickers")
  if "Ticker" not in df.columns:
    return df

  intrinsic_list = []
  tech_list = []

  for ticker in df["Ticker"]:
    iv = get_intrinsic_value_metrics(ticker, tickers_dir)
    if iv:
      intrinsic_list.append(iv)

    prices_path = os.path.join(tickers_dir, ticker, "prices.tsv")
    if os.path.exists(prices_path):
      try:
        prices = pd.read_csv(prices_path, sep="\t")
        prices['Date'] = pd.to_datetime(prices['Date'])
        techs = calculate_technical_metrics(prices)
        if techs:
          techs["Ticker"] = ticker
          tech_list.append(techs)
      except Exception as e:
        logger.warning("Error calculating techs for %s: %s", ticker, e)

  if intrinsic_list:
    iv_df = pd.DataFrame(intrinsic_list).dropna(how='all')
    if not iv_df.empty and 'Ticker' in iv_df.columns:
      for col in iv_df.columns:
        if col != 'Ticker' and col in df.columns:
          df = df.drop(columns=[col])
      df = df.merge(iv_df, on="Ticker", how="left")

  if tech_list:
    tech_df = pd.DataFrame(tech_list).dropna(how='all')
    if not tech_df.empty and 'Ticker' in tech_df.columns:
      for col in tech_df.columns:
        if col != 'Ticker' and col in df.columns:
          df = df.drop(columns=[col])
      df = df.merge(tech_df, on="Ticker", how="left")

  return df


# ==========================================
# REPORT RENDERING & EXPORT UTILITIES
# ==========================================

DEFAULT_PDF_CSS = """
@page {
    size: A4;
    margin: 1.0cm;
}
body {
    font-family: 'Helvetica', 'Arial', sans-serif;
    line-height: 1.4;
    color: #333;
    font-size: 9pt;
}
h1, h2, h3 {
    color: #111;
    margin-top: 1.0em;
    margin-bottom: 0.4em;
}
h1 { font-size: 16pt; }
h2 { font-size: 14pt; }
h3 { font-size: 12pt; }
img {
    max-width: 100%;
    max-height: 600px;
    height: auto;
    display: block;
    margin: 20px auto;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    font-size: 7pt;
    table-layout: auto;
    word-wrap: break-word;
}
th, td {
    border: 1px solid #ddd;
    padding: 6px;
    text-align: left;
    word-break: break-all;
}
th {
    background-color: #f5f5f5;
    font-weight: bold;
}
ul, ol {
    margin: 10px 0 10px 20px;
    padding: 0;
}
pre, code {
    background-color: #f8f9fa;
    border-radius: 4px;
    padding: 2px 4px;
    font-family: monospace;
}
pre {
    padding: 10px;
    overflow-x: auto;
}
"""


def render_markdown_to_pdf(md_path: str,
                           output_path: Optional[str] = None) -> str:
  """
    Converts a Markdown file containing local image links to a self-contained PDF.
    Returns the path to the generated PDF.
    """
  if not os.path.exists(md_path):
    raise FileNotFoundError(f"Markdown file not found: {md_path}")

  md_dir = os.path.abspath(os.path.dirname(md_path))
  md_basename = os.path.basename(md_path)

  if not output_path:
    # Default save to reports/rendered/
    root_dir = os.path.dirname(md_dir) if os.path.basename(
        md_dir) != 'reports' else md_dir
    if not root_dir.endswith('reports'):
      parts = md_dir.split(os.sep)
      if 'reports' in parts:
        root_dir = os.sep.join(parts[:parts.index('reports') + 1])
      else:
        root_dir = md_dir

    rendered_dir = os.path.join(root_dir, 'rendered')
    os.makedirs(rendered_dir, exist_ok=True)
    pdf_filename = os.path.splitext(md_basename)[0] + ".pdf"

    parent_dir_name = os.path.basename(md_dir)
    if parent_dir_name not in ("reports", "rendered"):
      if parent_dir_name == "news":
        pass
      else:
        pdf_filename = f"{parent_dir_name}_{pdf_filename}"

    output_path = os.path.join(rendered_dir, pdf_filename)

  with open(md_path, 'r', encoding='utf-8') as f:
    md_text = f.read()

  def make_abs_path(match):
    alt_text = match.group(1)
    rel_path = match.group(2)
    if rel_path.startswith(('http://', 'https://')):
      return match.group(0)

    if rel_path.startswith('./'):
      rel_path = rel_path[2:]

    abs_path = os.path.join(md_dir, rel_path)
    abs_uri = f"file://{abs_path}"
    return f"![{alt_text}]({abs_uri})"

  md_text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', make_abs_path, md_text)

  html_body = markdown.markdown(md_text,
                                extensions=['tables', 'fenced_code', 'nl2br'])

  logger.info("Rendering PDF for %s...", md_basename)
  try:
    # Weasyprint expects a full HTML document structure for reliable rendering
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{os.path.basename(md_path)}</title>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """
    HTML(string=full_html,
         base_url=md_dir).write_pdf(output_path,
                                    stylesheets=[CSS(string=DEFAULT_PDF_CSS)])
    logger.info("Successfully rendered PDF: %s", output_path)
  except Exception as e:
    logger.error("Failed to render PDF file: %s", e)

  return output_path


def generate_exposure_plot(df: pd.DataFrame,
                           title: str,
                           save_path: str,
                           privacy_mode: bool = False):
  """Generates a bar plot of portfolio exposure by theme."""
  if "Theme" not in df.columns or df.empty:
    return
  setup_plot_aesthetics()

  if privacy_mode and "Portfolio_Weight_Pct" in df.columns:
    theme_values = df.groupby(
        "Theme")["Portfolio_Weight_Pct"].sum().sort_values(ascending=False)
    x_label = "Portfolio Weight (%)"
  else:
    theme_values = df.groupby("Theme")["Current_Value"].sum().sort_values(
        ascending=False)
    x_label = "Total Value ($)"

  plt.figure(figsize=(10, 6))
  ax = sns.barplot(x=theme_values.values,
                   y=theme_values.index,
                   hue=theme_values.index,
                   palette="viridis",
                   legend=False)

  # Add explicit data labels to the end of each bar
  for i, v in enumerate(theme_values.values):
    label = f"{v:.1f}%" if "Portfolio Weight" in x_label else f"${v:,.0f}"
    ax.text(v, i, f" {label}", va='center', fontsize=10, fontweight='bold')

  plt.title(title, fontweight='bold')
  plt.xlabel(x_label)
  plt.ylabel("")
  plt.tight_layout()
  plt.savefig(save_path, dpi=300)
  plt.close()


def generate_pnl_plot(df: pd.DataFrame,
                      title: str,
                      save_path: str,
                      privacy_mode: bool = False):
  """Generates a bar plot of unrealized PnL by theme."""
  if "Theme" not in df.columns or df.empty:
    return
  setup_plot_aesthetics()

  if privacy_mode and "Unrealized_PnL_Net" in df.columns and "Cost_Basis" in df.columns:
    theme_grouped = df.groupby("Theme").agg({
        "Unrealized_PnL_Net": "sum",
        "Cost_Basis": "sum"
    })
    theme_pnl = (theme_grouped["Unrealized_PnL_Net"] /
                 theme_grouped["Cost_Basis"].replace(0, 1)) * 100
    theme_pnl = theme_pnl.sort_values(ascending=False)
    x_label = "Unrealized PnL (%)"
  elif "Unrealized_PnL_Net" in df.columns:
    theme_pnl = df.groupby("Theme")["Unrealized_PnL_Net"].sum().sort_values(
        ascending=False)
    x_label = "PnL ($)"
  else:
    return

  plt.figure(figsize=(10, 6))
  colors = ["g" if val > 0 else "r" for val in theme_pnl.values]
  ax = sns.barplot(x=theme_pnl.values,
                   y=theme_pnl.index,
                   hue=theme_pnl.index,
                   palette=colors,
                   legend=False)

  # Add explicit data labels to the end of each bar
  for i, v in enumerate(theme_pnl.values):
    label = f"{v:+.1f}%" if "Unrealized PnL (%)" in x_label else f"${v:+,.0f}"
    align = 'left' if v >= 0 else 'right'
    offset = theme_pnl.abs().max() * 0.02
    x_pos = v + offset if v >= 0 else v - offset
    ax.text(x_pos,
            i,
            label,
            va='center',
            ha=align,
            fontsize=10,
            fontweight='bold')

  plt.title(title, fontweight='bold')
  plt.xlabel(x_label)
  plt.ylabel("")
  plt.axvline(0, color="black", linestyle="--")
  plt.tight_layout()
  plt.savefig(save_path, dpi=300)
  plt.close()


def generate_quantitative_alerts(df: pd.DataFrame) -> str:
  """Generates dynamic markdown bullets highlighting extremely overbought/oversold and anomalous assets."""
  alerts = ""
  if df.empty:
    return "*No data available for quantitative scanning.*"

  # 1. RSI Extremes
  if 'RSI' in df.columns:
    overbought = df[(df['RSI'].notna()) & (df['RSI'] > 70)]
    if not overbought.empty:
      alerts += "**⚠️ Overbought Targets (Trim Warning - RSI > 70):**\n"
      for _, row in overbought.sort_values('RSI', ascending=False).iterrows():
        alerts += f"- **{row['Ticker']}**: RSI {row['RSI']:.1f}\n"
      alerts += "\n"

    oversold = df[(df['RSI'].notna()) & (df['RSI'] < 40)]
    if not oversold.empty:
      alerts += "**✅ Oversold Accumulation Zones (RSI < 40):**\n"
      for _, row in oversold.sort_values('RSI').iterrows():
        alerts += f"- **{row['Ticker']}**: RSI {row['RSI']:.1f}\n"
      alerts += "\n"

  # 2. Moving Average Extension
  if 'Dist_to_200MA' in df.columns:
    extended = df[(df['Dist_to_200MA'].notna()) & (df['Dist_to_200MA'] > 40)]
    if not extended.empty:
      alerts += "**🚀 Structurally Over-Extended (>40% above 200MA):**\n"
      for _, row in extended.sort_values('Dist_to_200MA',
                                         ascending=False).iterrows():
        alerts += f"- **{row['Ticker']}**: +{row['Dist_to_200MA']:.1f}%\n"
      alerts += "\n"

  # 3. Deep Intrinsic Value Discount
  if 'Discount_to_Intrinsic_Value_Pct' in df.columns:
    deep_value = df[(df['Discount_to_Intrinsic_Value_Pct'].notna()) &
                    (df['Discount_to_Intrinsic_Value_Pct'] > 25)]
    if not deep_value.empty:
      alerts += "**💎 Deep Intrinsic Value (>25% Discount to Graham Base):**\n"
      for _, row in deep_value.sort_values('Discount_to_Intrinsic_Value_Pct',
                                           ascending=False).iterrows():
        alerts += f"- **{row['Ticker']}**: {row['Discount_to_Intrinsic_Value_Pct']:.1f}% Undervalued\n"
      alerts += "\n"

  # 4. Volume Momentum Surges
  if 'Vol_Momentum' in df.columns:
    high_vol = df[(df['Vol_Momentum'].notna()) & (df['Vol_Momentum'] > 2.0)]
    if not high_vol.empty:
      alerts += "**🌊 Massive Volume Inflow (>2x Average 20D):**\n"
      for _, row in high_vol.sort_values('Vol_Momentum',
                                         ascending=False).iterrows():
        alerts += f"- **{row['Ticker']}**: {row['Vol_Momentum']:.1f}x Avg Volume\n"
      alerts += "\n"

  return alerts if alerts else "*No extreme quantitative anomalies detected across the current dataset.*"


def generate_near_term_action_plan(df: pd.DataFrame) -> str:
  """Generates a Top 3 Buys and Top 3 Sells markdown block for near-term 1-2 day tactical actions based on momentum."""
  actions = ""
  if df.empty or 'RSI' not in df.columns:
    return "*No tactical data available.*"

  # Top 3 Buys: Lowest RSI, largest negative Dist_to_200MA
  buys_df = df[(df['RSI'].notna()) & (df['Ticker'] != 'CASH')].sort_values(
      by=['RSI', 'Dist_to_200MA'], ascending=[True, True]).head(3)

  # Top 3 Sells: Highest RSI, largest positive Dist_to_200MA
  sells_df = df[(df['RSI'].notna()) & (df['Ticker'] != 'CASH')].sort_values(
      by=['RSI', 'Dist_to_200MA'], ascending=[False, False]).head(3)

  actions += "**📈 Top 3 Tactical BUYS (1-2 Day Horizon):**\n"
  if buys_df.empty:
    actions += "- None meeting criteria.\n"
  for _, row in buys_df.iterrows():
    rsi = row.get('RSI', 'N/A')
    dist = row.get('Dist_to_200MA', 'N/A')
    ret_5d = row.get('Trailing_5D_Ret', 'N/A')
    vol_mom = row.get('Vol_Momentum', 'N/A')
    why = f"Severely oversold (RSI: {rsi:.1f}). " if isinstance(
        rsi, float) and rsi < 40 else f"Cooling off (RSI: {rsi:.1f}). "
    why += f"Extended {dist:+.1f}% from 200MA. " if isinstance(dist,
                                                               float) else ""
    why += f"5D Momentum: {ret_5d:+.1f}%. " if isinstance(ret_5d, float) else ""
    why += f"Vol Surge: {vol_mom:.1f}x." if isinstance(
        vol_mom, float) and vol_mom > 1.5 else ""
    actions += f"- **{row['Ticker']}**: {why.strip()}\n"

  actions += "\n**📉 Top 3 Tactical SELLS (1-2 Day Horizon):**\n"
  if sells_df.empty:
    actions += "- None meeting criteria.\n"
  for _, row in sells_df.iterrows():
    rsi = row.get('RSI', 'N/A')
    dist = row.get('Dist_to_200MA', 'N/A')
    ret_5d = row.get('Trailing_5D_Ret', 'N/A')
    why = f"Overbought exhaustion risk (RSI: {rsi:.1f}). " if isinstance(
        rsi, float) and rsi > 70 else f"Elevated momentum (RSI: {rsi:.1f}). "
    why += f"Overextended {dist:+.1f}% from 200MA. " if isinstance(
        dist, float) else ""
    why += f"5D Run: {ret_5d:+.1f}%. " if isinstance(ret_5d, float) else ""
    actions += f"- **{row['Ticker']}**: {why.strip()}\n"

  return actions


def build_standard_portfolio_report(script_dir: str,
                                    tsv_filename: str,
                                    title_prefix: str,
                                    tree_func,
                                    markdown_template: str,
                                    market_analysis: str = "",
                                    privacy_mode: bool = False):
  """
  Abstracts the boilerplate sequence:
  1. Creates plot directory.
  2. Runs decision tree custom logic.
  3. Loads TSV and plots theme exposures/PnL.
  4. Generates standard metrics table (enriched with intrinsic/technical data).
  5. Injects the table and market analysis into a customized markdown template.
  """
  plots_dir = os.path.join(script_dir, "plots")
  os.makedirs(plots_dir, exist_ok=True)

  tree_path = os.path.join(plots_dir, "decision_tree")
  tree_func(tree_path)

  tsv_path = os.path.abspath(
      os.path.join(script_dir, f"../../portfolios/tsvs/{tsv_filename}"))
  if not os.path.exists(tsv_path):
    logging.warning("TSV not found: %s", tsv_path)
    return

  df = load_portfolio_tsv(tsv_path)

  market_data_dir = os.path.abspath(
      os.path.join(script_dir, "../../market_data"))
  df = enrich_portfolio_df(df, market_data_dir)

  generate_exposure_plot(df,
                         f"{title_prefix} - Theme Exposure",
                         os.path.join(plots_dir, "theme_exposure.png"),
                         privacy_mode=privacy_mode)
  generate_pnl_plot(df,
                    f"{title_prefix} - Theme PnL",
                    os.path.join(plots_dir, "theme_pnl.png"),
                    privacy_mode=privacy_mode)

  metrics_table = generate_portfolio_markdown_table(df)
  quantitative_alerts = generate_quantitative_alerts(df)

  # Explicit Static Trade Injection
  trades_path = os.path.join(script_dir, "trades.tsv")
  if os.path.exists(trades_path):
    try:
      trades_df = pd.read_csv(trades_path, sep='\t')
      tactical_actions = trades_df.to_markdown(index=False)
    except Exception as e:
      logging.error(f"Failed to parse trades.tsv: {e}")
      tactical_actions = generate_near_term_action_plan(df)
  else:
    tactical_actions = generate_near_term_action_plan(df)

  format_args = {
      "metrics_table": metrics_table,
      "market_analysis": market_analysis,
      "quantitative_alerts": quantitative_alerts,
      "tactical_actions": tactical_actions
  }

  report_md = markdown_template
  for key, value in format_args.items():
    placeholder = f"{{{key}}}"
    if placeholder in report_md:
      report_md = report_md.replace(placeholder, value)

  out_path = os.path.join(script_dir, "REPORT.md")
  with open(out_path, "w", encoding="utf-8") as f:
    f.write(clean_md(report_md))

  # --- AI PORTFOLIO ENHANCEMENT ---
  # Only trigger if not explicitly disabled
  if os.environ.get("DISABLE_NOTEBOOKLM_UPLOAD", "0") != "1":
    try:
      logger.info(f"Synthesizing AI tactical overlay for: {out_path}...")
      curr_dir = os.path.dirname(os.path.abspath(__file__))
      notebooklm_report_path = os.path.join(curr_dir, "notebooklm_report.py")
      report_utils_path = os.path.join(curr_dir, "report_utils.py")

      notebooklm_cmd = f"python3 '{notebooklm_report_path}' --mode portfolio --dir '{out_path}'"
      os.system(notebooklm_cmd)

      logger.info(f"Re-rendering Enhanced Markdown to PDF: {out_path}...")
      render_markdown_to_pdf(out_path)
    except Exception as e:
      logger.error(
          f"Failed to generate AI tactical overlay for {script_dir}: {e}")


def build_daily_news_digest(
    market_data_dir: str,
    start_date: Optional[datetime.datetime] = None,
    target_date: Optional[datetime.datetime] = None,
    backfill_news: bool = True) -> Tuple[str, pd.DataFrame]:
  """Fetches recent news dynamically using all topics and tickers in config.py."""

  all_news = []

  # When building periodic reports spanning many days, we sample systematically
  # across the whole window. We use moderate limits to avoid exploding the context.
  topic_limit = 15 if start_date else 5
  ticker_limit = 5 if start_date else 3

  # 1. Fetch from all config.NEWS_TOPICS
  for topic in config.NEWS_TOPICS:
    df = get_recent_news(topic,
                         market_data_dir,
                         limit=topic_limit,
                         start_date=start_date,
                         end_date=target_date)

    # Retrospective Fallback: If bounded context is suspiciously sparse (< 10 items)
    # trigger an on-demand historical fetch for this topic to backfill the gap.
    if backfill_news and start_date and target_date and len(
        df) < 10 and start_date.year >= 2025:
      logger.info(
          f"Sparse news detected for {topic} ({len(df)} items). Retrospectively fetching..."
      )
      try:
        fetcher = MarketFetcher(data_dir=market_data_dir)
        fetcher.fetch_historical_topic_news(start_date.date(),
                                            target_date.date(),
                                            thorough=False)
        # Re-fetch after the backfill
        df = get_recent_news(topic,
                             market_data_dir,
                             limit=topic_limit,
                             start_date=start_date,
                             end_date=target_date)
      except Exception as e:
        logger.warning(f"Failed retrospective fetch for {topic}: {e}")

    if not df.empty:
      df['Source_Label'] = f"Topic: {topic}"
      all_news.append(df)

  # 2. Fetch from all config.SECTORS -> tickers
  for sector_name, tickers in config.SECTORS.items():
    for ticker in tickers:
      df = get_recent_ticker_news(ticker,
                                  market_data_dir,
                                  limit=ticker_limit,
                                  start_date=start_date,
                                  end_date=target_date)
      if not df.empty:
        df['Source_Label'] = f"{ticker} ({sector_name})"
        all_news.append(df)

  if not all_news:
    return "", pd.DataFrame()

  combined_df = pd.concat(all_news, ignore_index=True)
  if 'Date' not in combined_df.columns or 'Headline' not in combined_df.columns:
    return "", pd.DataFrame()

  combined_df = combined_df.sort_values('Date',
                                        ascending=False).reset_index(drop=True)

  text_blob = "MARKET NEWS DIGEST:\n\n"
  seen_headlines: List[str] = []
  seen_exact = set()

  # Optimization: if handling massive time chunks (e.g., yearly scans of 5000+ items),
  # O(N^2) fuzzy checking will freeze the program.
  use_fuzzy = len(combined_df) < 500

  for _, row in combined_df.iterrows():
    if not pd.notna(row['Date']) or not pd.notna(row['Headline']):
      continue

    headline = str(row['Headline']).strip()
    headline_lower = headline.lower()

    if headline_lower in seen_exact:
      continue

    if use_fuzzy and any(
        _is_similar(headline, seen) for seen in seen_headlines):
      continue

    seen_headlines.append(headline)
    seen_exact.add(headline_lower)

    summary_raw = ""
    if 'Summary' in row and pd.notna(row['Summary']) and len(
        str(row['Summary']).strip()) > 10:
      summary_raw = str(row['Summary']).strip()
      summary_raw = summary_raw.replace('\n', ' ').replace('\r', '')

    text_blob += f"Title: {headline}\n"
    text_blob += f"Topic/Ticker: {row.get('Source_Label', 'News')}\n"

    # Capture the link for deep fetching later
    link = str(row.get('URL', '')).strip()
    if link and link.startswith('http'):
      text_blob += f"Link: {link}\n"

    if summary_raw:
      text_blob += f"Summary: {summary_raw}\n"
    text_blob += "\n"

  # Append Shipping/Macro context to the digest
  text_blob = _append_shipping_to_digest(market_data_dir, text_blob, start_date,
                                         target_date)

  return text_blob, combined_df


def _append_shipping_to_digest(market_data_dir: str, text_blob: str,
                               start_date: Optional[datetime.datetime],
                               target_date: Optional[datetime.datetime]) -> str:
  files_to_check = [
      ("Global Congestion",
       os.path.join(market_data_dir, "shipping", "chokepoint_metrics.tsv")),
      ("Geopolitics & Tariffs",
       os.path.join(market_data_dir, "shipping", "tariffs.tsv")),
      ("Macro Constraints",
       os.path.join(market_data_dir, "shipping", "shipping_macro.tsv")),
  ]

  shipping_blob = ""
  for label, file_path in files_to_check:
    if os.path.exists(file_path):
      try:
        df = pd.read_csv(file_path, sep="\t")
        if "Date" in df.columns:
          df['ParsedDate'] = pd.to_datetime(df['Date'],
                                            utc=True).dt.tz_localize(None)
          if start_date:
            df = df[df['ParsedDate'] >= start_date]
          if target_date:
            df = df[df['ParsedDate'] <= target_date]

          # We only care about appending the recent active points so we take the top 5
          df = df.sort_values(by="ParsedDate", ascending=False).head(5)

          if not df.empty:
            shipping_blob += f"--- {label} ---\n"
            for _, row in df.iterrows():
              dt_str = row['ParsedDate'].strftime('%Y-%m-%d')
              line_items = [
                  f"{k}: {v}" for k, v in row.items()
                  if k not in ['Date', 'ParsedDate'] and pd.notna(v)
              ]
              shipping_blob += f"[{dt_str}] " + " | ".join(line_items) + "\n"
            shipping_blob += "\n"
      except Exception as e:
        logger.warning(f"Failed to append shipping context for {label}: {e}")

  if shipping_blob:
    text_blob += "\n\nADDITIONAL MACRO & SHIPPING METRICS:\n\n" + shipping_blob

  return text_blob


def get_upcoming_earnings(ticker: str, tickers_dir: str) -> str:
  """Parses earnings.tsv for a ticker and returns the next upcoming date."""
  earnings_path = os.path.join(tickers_dir, ticker, "earnings.tsv")
  if not os.path.exists(earnings_path):
    return ""
  try:
    df = pd.read_csv(earnings_path, sep="\t")
    if 'Earnings Date' not in df.columns:
      return ""

    # Convert to datetime, handle timezone offset
    df['Date_Parsed'] = pd.to_datetime(df['Earnings Date'],
                                       errors='coerce',
                                       utc=True)

    # Filter for dates after today
    today = pd.to_datetime(datetime.datetime.now().date(), utc=True)
    future_earnings = df[df['Date_Parsed'] > today].sort_values('Date_Parsed')

    if not future_earnings.empty:
      next_date = future_earnings.iloc[0]['Earnings Date']
      return next_date.split()[0]
  except Exception as e:
    logger.warning("Failed to parse earnings for %s: %s", ticker, e)
  return ""


def get_recent_earnings(ticker: str, tickers_dir: str) -> str:
  """Finds the most recent reported earnings date."""
  earnings_path = os.path.join(tickers_dir, ticker, "earnings.tsv")
  if not os.path.exists(earnings_path):
    return ""
  try:
    df = pd.read_csv(earnings_path, sep="\t")
    if 'Earnings Date' not in df.columns:
      return ""
    df['Date_Parsed'] = pd.to_datetime(df['Earnings Date'],
                                       errors='coerce',
                                       utc=True)
    today = pd.to_datetime(datetime.datetime.now().date(), utc=True)
    past_earnings = df[df['Date_Parsed'] <= today].sort_values('Date_Parsed',
                                                               ascending=False)
    if not past_earnings.empty:
      return past_earnings.iloc[0]['Earnings Date'].split()[0]
  except Exception as e:
    pass
  return ""


def plot_portfolio_allocation_bar(df: pd.DataFrame, out_path: str):
  """Generates a horizontal bar chart of the portfolio allocation."""
  if df.empty:
    return
  setup_plot_aesthetics()
  plt.figure(figsize=(10, 8))
  df_p = df.sort_values(by='Portfolio_Weight_Pct', ascending=True)
  labels = df_p['Ticker'].tolist()
  sizes = [float(s) for s in df_p['Portfolio_Weight_Pct'].tolist()]

  plt.barh(labels, sizes, color='skyblue')
  plt.xlabel('Portfolio Weight (%)')
  plt.title('Portfolio Allocation (% Relative Weight)',
            fontweight='bold',
            fontsize=14)
  plt.tight_layout()
  plt.savefig(out_path, dpi=200)
  plt.close()
  logger.info("Saved bar chart to %s", out_path)


def generate_price_volume_capitulation_plot(ticker: str, tickers_dir: str,
                                            output_path: str):
  """Generates a price vs volume capitulation plot for a ticker."""
  prices_path = os.path.join(tickers_dir, ticker, "prices.tsv")
  if not os.path.exists(prices_path):
    logger.warning("Prices file missing for %s", ticker)
    return

  try:
    df = pd.read_csv(prices_path, sep="\t")
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').tail(90)  # Last 90 days

    plt.figure(figsize=(12, 6))
    ax1 = plt.gca()
    ax2 = ax1.twinx()

    # Volume as bars
    ax2.bar(df['Date'], df['Volume'], alpha=0.3, color='blue', label='Volume')
    ax2.set_ylabel('Volume', color='blue')

    # Price as line
    ax1.plot(df['Date'],
             df['Close'],
             color='red',
             label=f'{ticker} Price',
             linewidth=2)
    ax1.set_ylabel('Price ($)', color='red')

    plt.title(f'{ticker} Price vs Volume Capitulation (Last 90 Days)',
              fontsize=14,
              fontweight='bold')
    ax1.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%m-%d'))
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    logger.info("Saved price/volume plot to %s", output_path)
  except Exception as e:
    logger.warning("Failed to generate price/volume plot for %s: %s", ticker, e)


# ==========================================
# MACRO ACCESS, RATES MATH & CROSS-ASSET HELPERS
# ==========================================
# Generic building blocks shared by macro, portfolio and fixed-income
# reports. Anything specific to a bond *portfolio* (ETF durations, yield
# proxies, scenario definitions) lives in reports/generate_bond_reports.py.

MACRO_FILENAME = "economic_indicators.tsv"

# Macro column -> tenor (years) for Treasury-curve snapshots.
DEFAULT_CURVE_TENORS: Dict[str, float] = {
    "US03M": 0.25,
    "US01Y": 1.0,
    "US02Y": 2.0,
    "US05Y": 5.0,
    "US10Y": 10.0,
    "US30Y": 30.0,
}

# Fund labels (401k trusts, mutual funds) that are bonds without a ticker.
DEFAULT_BOND_NAME_HINTS: Tuple[str, ...] = ("Tot Bd", "Bond", "Bd Mkt", "VTIFX",
                                            "VBTLX", "VBTIX")


def load_macro_frame(market_data_dir: str) -> pd.DataFrame:
  """Loads the forward-filled daily macro frame indexed by date.

  Args:
    market_data_dir (str): Path to ``market_data``.

  Returns:
    pd.DataFrame: Daily numeric frame (DatetimeIndex) of FRED series.

  Raises:
    FileNotFoundError: If the macro TSV does not exist.
  """
  path = os.path.join(market_data_dir, "macro", MACRO_FILENAME)
  if not os.path.exists(path):
    raise FileNotFoundError(f"Macro file missing: {path}")
  df = pd.read_csv(path, sep="\t")
  date_col = "DATE" if "DATE" in df.columns else df.columns[0]
  df[date_col] = pd.to_datetime(df[date_col])
  df = df.set_index(date_col).sort_index()
  return df.apply(pd.to_numeric, errors="coerce")


def macro_asof(macro: pd.DataFrame, when: Any) -> pd.Series:
  """Returns the last available macro row on or before ``when``.

  Args:
    macro (pd.DataFrame): Output of :func:`load_macro_frame`.
    when (Any): Anything ``pd.Timestamp`` accepts.

  Returns:
    pd.Series: Row of indicator values.

  Raises:
    ValueError: If no observation exists on or before ``when``.
  """
  ts = pd.Timestamp(when)
  sub = macro.loc[:ts]
  if sub.empty:
    raise ValueError(f"No macro data on or before {ts.date()}")
  return sub.iloc[-1]


def curve_snapshot(macro: pd.DataFrame,
                   dates: Dict[str, Any],
                   tenors: Optional[Dict[str, float]] = None) -> pd.DataFrame:
  """Builds a Treasury-curve table (tenor rows x snapshot-date columns).

  Args:
    macro (pd.DataFrame): Output of :func:`load_macro_frame`.
    dates (Dict[str, Any]): Label -> date mapping (e.g. {"Today": ...}).
    tenors (Optional[Dict[str, float]]): Macro column -> years; defaults
      to :data:`DEFAULT_CURVE_TENORS`.

  Returns:
    pd.DataFrame: Index = tenor label (``3M`` .. ``30Y``), one column per
    label plus ``Years`` (tenor in years).
  """
  rows = []
  for col, years in (tenors or DEFAULT_CURVE_TENORS).items():
    if col not in macro.columns:
      continue
    row: Dict[str, Any] = {
        "Tenor": col.replace("US", "").lstrip("0"),
        "Years": years
    }
    for label, when in dates.items():
      row[label] = float(macro_asof(macro, when)[col])
    rows.append(row)
  return pd.DataFrame(rows).set_index("Tenor")


def rates_change_table(macro: pd.DataFrame,
                       start: Any,
                       end: Any,
                       columns: Optional[Sequence[str]] = None) -> pd.DataFrame:
  """Tabulates start / end / change (bp) for rate-like macro series.

  Args:
    macro (pd.DataFrame): Output of :func:`load_macro_frame`.
    start (Any): Start date.
    end (Any): End date.
    columns (Optional[Sequence[str]]): Series to include; defaults to the
      policy rate, Treasury curve, real yield, breakeven, term premium and
      credit series.

  Returns:
    pd.DataFrame: Index = series, columns ``Start, End, Change_bp``.
  """
  a, b = macro_asof(macro, start), macro_asof(macro, end)
  cols = columns or [
      "FEDFUNDS_UPPER", "US03M", "US02Y", "US05Y", "US10Y", "US30Y",
      "US10Y_REAL", "BREAKEVEN_10Y", "TERM_PREMIUM_10Y", "HY_SPREAD",
      "HY_YIELD", "CORP_YIELD"
  ]
  rows = []
  for c in cols:
    if c in macro.columns:
      rows.append({
          "Series": c,
          "Start": round(float(a[c]), 2),
          "End": round(float(b[c]), 2),
          "Change_bp": round((float(b[c]) - float(a[c])) * 100, 0),
      })
  return pd.DataFrame(rows).set_index("Series")


def hike_pricing(macro_row: pd.Series) -> Dict[str, float]:
  """Reads how many 25bp moves the front end is pricing vs. the Fed.

  Conventional rough read: the 1Y/2Y yield ≈ where the market expects the
  policy rate to settle, so (yield − policy mid) / 25bp ≈ moves priced.
  Ignores term premium, so treat as an upper bound.

  Args:
    macro_row (pd.Series): A macro row (see :func:`macro_asof`).

  Returns:
    Dict[str, float]: ``policy_mid, spread_3m_bp, spread_1y_bp,
    spread_2y_bp, hikes_priced_1y, hikes_priced_2y``.
  """
  upper = float(macro_row.get("FEDFUNDS_UPPER", np.nan))
  if np.isnan(upper):
    mid = float(macro_row.get("FEDFUNDS", np.nan))
  else:
    mid = upper - 0.125
  s3 = (float(macro_row["US03M"]) - mid) * 100
  s1 = (float(macro_row["US01Y"]) - mid) * 100
  s2 = (float(macro_row["US02Y"]) - mid) * 100
  return {
      "policy_mid": mid,
      "spread_3m_bp": s3,
      "spread_1y_bp": s1,
      "spread_2y_bp": s2,
      "hikes_priced_1y": max(s1, 0) / 25,
      "hikes_priced_2y": max(s2, 0) / 25,
  }


def read_fundamental_metric(tickers_dir: str, ticker: str,
                            key: str) -> Optional[float]:
  """Reads one numeric metric from a ticker's fundamentals.tsv.

  Args:
    tickers_dir (str): ``market_data/tickers``.
    ticker (str): Ticker symbol.
    key (str): Metric name (e.g. ``yield``, ``netExpenseRatio``).

  Returns:
    Optional[float]: Value or None when missing / non-numeric.
  """
  path = os.path.join(tickers_dir, ticker, "fundamentals.tsv")
  if not os.path.exists(path):
    return None
  try:
    df = pd.read_csv(path, sep="\t")
    hit = df.loc[df["Metric"] == key, "Value"]
    if hit.empty:
      return None
    return float(hit.iloc[0])
  except (ValueError, TypeError, KeyError, pd.errors.ParserError) as e:
    logger.debug("fundamentals read failed for %s/%s: %s", ticker, key, e)
    return None


def rate_shock_return(yield_pct: float,
                      duration: float,
                      shock_bp: float,
                      convexity: Optional[float] = None,
                      spread_shock_bp: float = 0.0,
                      spread_duration: Optional[float] = None,
                      horizon_years: float = 1.0,
                      default_loss_pct: float = 0.0) -> float:
  """Approximates a bond's total return under an instantaneous shock.

  TR ≈ carry − D·Δy + ½·C·Δy² − D_s·Δs − default losses; the shock is
  applied immediately and carry accrues for ``horizon_years``.

  Args:
    yield_pct (float): Starting yield (percent).
    duration (float): Effective (rate) duration in years.
    shock_bp (float): Parallel yield shock in basis points (+ = up).
    convexity (Optional[float]): Convexity; defaults to ~1.1·D².
    spread_shock_bp (float): Credit-spread shock in bp (+ = wider).
    spread_duration (Optional[float]): Spread duration (default duration).
    horizon_years (float): Carry horizon.
    default_loss_pct (float): Realised credit losses over the horizon.

  Returns:
    float: Approximate total return in percent.
  """
  dy = shock_bp / 10000.0
  ds = spread_shock_bp / 10000.0
  conv = convexity if convexity is not None else max(duration, 0.0)**2 * 1.1
  sd = spread_duration if spread_duration is not None else duration
  price = -duration * dy + 0.5 * conv * dy * dy - sd * ds
  carry = yield_pct / 100.0 * horizon_years
  return (price + carry) * 100.0 - default_loss_pct


def rate_shock_grid(instruments: Dict[str, Tuple[float, float]],
                    shocks_bp: Sequence[int]) -> pd.DataFrame:
  """12M total-return grid for (yield, duration) instruments vs shocks.

  Args:
    instruments (Dict[str, Tuple[float, float]]): name -> (yield %,
      duration yrs).
    shocks_bp (Sequence[int]): Parallel shocks in bp.

  Returns:
    pd.DataFrame: Index = instrument, columns = ``{shock:+d}bp``.
  """
  data = {}
  for name, (y, d) in instruments.items():
    data[name] = {
        f"{s:+d}bp": round(rate_shock_return(y, d, s), 2) for s in shocks_bp
    }
  return pd.DataFrame(data).T


def synthetic_bond_total_return(yields_pct: pd.Series,
                                maturity_years: float,
                                periods_per_year: int = 12) -> pd.Series:
  """Rebuilds a constant-maturity par-bond total-return index from yields.

  Each period the investor holds a par bond, earns the coupon
  (yield/periods), marks it to the new yield with one period less to
  maturity, then rolls into a fresh par bond (Swinkels 2019 approach), so
  long histories can be studied without a paid bond index.

  Args:
    yields_pct (pd.Series): Periodic yields in percent (DatetimeIndex).
    maturity_years (float): Bond maturity in years.
    periods_per_year (int): 12 for monthly data.

  Returns:
    pd.Series: Total-return index starting at 100.
  """
  y = (yields_pct.astype(float) / 100.0).dropna()
  if len(y) < 2:
    return pd.Series(dtype=float)
  n_total = int(round(maturity_years * periods_per_year))
  idx = [100.0]
  values = y.values
  for i in range(1, len(values)):
    c = values[i - 1] / periods_per_year  # coupon set at purchase
    ynew = values[i] / periods_per_year  # new periodic yield
    n = n_total - 1  # one period elapsed
    if ynew <= 0:
      price = 1.0 + c * n
    else:
      price = c * (1 - (1 + ynew)**(-n)) / ynew + (1 + ynew)**(-n)
    idx.append(idx[-1] * (price + c))
  return pd.Series(idx, index=y.index, name=f"TR_{maturity_years:g}Y")


def cash_total_return(short_rate_pct: pd.Series,
                      periods_per_year: int = 12) -> pd.Series:
  """Total-return index from rolling a short rate (T-bill / fed funds)."""
  r = (short_rate_pct.astype(float) / 100.0).dropna()
  growth = (1.0 + r.shift(1).fillna(0) / periods_per_year).cumprod()
  return (growth * 100.0).rename("TR_cash")


def forward_annualized_return(tr_index: pd.Series,
                              horizon_years: float,
                              periods_per_year: int = 12) -> pd.Series:
  """Forward-looking annualised return (%) of any TR index over a horizon."""
  n = int(round(horizon_years * periods_per_year))
  fwd = tr_index.shift(-n) / tr_index
  return (fwd**(1.0 / horizon_years) - 1.0) * 100.0


def starting_yield_table(
    yields_pct: pd.Series,
    maturity_years: float,
    horizons: Iterable[float] = (1, 3, 5, 10),
    cash_rate_pct: Optional[pd.Series] = None) -> pd.DataFrame:
  """Builds the "starting yield vs. subsequent return" dataset.

  Args:
    yields_pct (pd.Series): Monthly constant-maturity yields (%).
    maturity_years (float): Bond maturity in years.
    horizons (Iterable[float]): Forward horizons in years.
    cash_rate_pct (Optional[pd.Series]): Monthly short rate (%) used to
      add forward cash and excess-return columns.

  Returns:
    pd.DataFrame: Index = month; ``Start_Yield`` plus ``Fwd_{h}Y`` (and
    ``Cash_{h}Y`` / ``Excess_{h}Y`` when a cash rate is given).
  """
  tr = synthetic_bond_total_return(yields_pct, maturity_years)
  out = pd.DataFrame({"Start_Yield": yields_pct.reindex(tr.index)})
  cash = None
  if cash_rate_pct is not None:
    cash = cash_total_return(cash_rate_pct.reindex(tr.index).ffill())
  for h in horizons:
    out[f"Fwd_{h:g}Y"] = forward_annualized_return(tr, h)
    if cash is not None:
      out[f"Cash_{h:g}Y"] = forward_annualized_return(cash, h)
      out[f"Excess_{h:g}Y"] = out[f"Fwd_{h:g}Y"] - out[f"Cash_{h:g}Y"]
  return out


def conditional_base_rates(
    table: pd.DataFrame,
    mask: pd.Series,
    horizons: Iterable[float] = (1, 3, 5, 10)) -> pd.DataFrame:
  """Summarises forward returns for months where ``mask`` is True.

  Args:
    table (pd.DataFrame): Output of :func:`starting_yield_table` (or any
      frame with ``Fwd_{h}Y`` / optional ``Cash_{h}Y`` / ``Excess_{h}Y``).
    mask (pd.Series): Boolean selector aligned to ``table.index``.
    horizons (Iterable[float]): Horizons present in ``table``.

  Returns:
    pd.DataFrame: Per horizon: ``N_months, Median_%, P10_%, P90_%`` and,
    when cash columns exist, ``Cash_Median_%, Excess_Median_%,
    Beat_Cash_%``.
  """
  rows = []
  sel = table[mask.reindex(table.index).fillna(False).astype(bool)]
  for h in horizons:
    col = f"Fwd_{h:g}Y"
    s = sel[col].dropna()
    row: Dict[str, Any] = {
        "Horizon": f"{h:g}Y",
        "N_months": int(len(s)),
        "Median_%": round(float(s.median()), 2) if len(s) else np.nan,
        "P10_%": round(float(s.quantile(0.1)), 2) if len(s) else np.nan,
        "P90_%": round(float(s.quantile(0.9)), 2) if len(s) else np.nan,
    }
    ccol, ecol = f"Cash_{h:g}Y", f"Excess_{h:g}Y"
    if ccol in sel.columns:
      e = sel[ecol].dropna()
      c = sel[ccol].dropna()
      row["Cash_Median_%"] = round(float(c.median()), 2) if len(c) else np.nan
      row["Excess_Median_%"] = round(float(e.median()), 2) if len(e) else np.nan
      row["Beat_Cash_%"] = round(float(
          (e > 0).mean() * 100), 0) if len(e) else np.nan
    rows.append(row)
  return pd.DataFrame(rows).set_index("Horizon")


def stock_bond_valuation(trailing_pe: float,
                         macro_row: pd.Series,
                         dividend_yield_pct: float = 0.0) -> Dict[str, float]:
  """Compares an equity index earnings yield with Treasury yields.

  Args:
    trailing_pe (float): Index trailing P/E.
    macro_row (pd.Series): A macro row with ``US10Y`` / ``US10Y_REAL``.
    dividend_yield_pct (float): Index dividend yield (%).

  Returns:
    Dict[str, float]: ``earnings_yield, us10y, us10y_real, fed_model_gap``
    (E/P − nominal 10Y), ``erp_vs_real`` (E/P − real 10Y),
    ``dividend_vs_tbill`` (dividend yield − 3M bill).
  """
  ep = 100.0 / trailing_pe
  us10 = float(macro_row["US10Y"])
  real = float(macro_row.get("US10Y_REAL", np.nan))
  bill = float(macro_row.get("US03M", np.nan))
  return {
      "earnings_yield": ep,
      "us10y": us10,
      "us10y_real": real,
      "fed_model_gap": ep - us10,
      "erp_vs_real": ep - real,
      "dividend_vs_tbill": dividend_yield_pct - bill,
  }


def after_tax_yield(yield_pct: float,
                    federal_rate: float,
                    state_rate: float = 0.0,
                    state_exempt_share: float = 0.0,
                    niit: float = 0.038) -> float:
  """After-tax yield for interest income.

  Args:
    yield_pct (float): Pre-tax yield (%).
    federal_rate (float): Marginal federal ordinary rate (0-1).
    state_rate (float): Marginal state rate (0-1).
    state_exempt_share (float): Share of income that is Treasury interest
      (state-tax exempt), 0-1.
    niit (float): Net investment income tax (0.038 above thresholds).

  Returns:
    float: After-tax yield in percent.
  """
  state_eff = state_rate * (1.0 - state_exempt_share)
  return yield_pct * (1.0 - federal_rate - niit - state_eff)


def classify_holding(
    ticker: str,
    name: str = "",
    bond_tickers: Optional[Iterable[str]] = None,
    bond_name_hints: Iterable[str] = DEFAULT_BOND_NAME_HINTS,
    employer_tickers: Iterable[str] = ("GOOG", "GOOGL")
) -> str:
  """Maps a holding to ``Employer Stock / Equity / Bond / Cash / Crypto``.

  Args:
    ticker (str): Ticker or fund label.
    name (str): Optional descriptive name.
    bond_tickers (Optional[Iterable[str]]): Tickers to treat as bonds;
      defaults to the ``Bonds & Rates`` and ``Fixed Income & Preferred``
      sectors in ``config.SECTORS``.
    bond_name_hints (Iterable[str]): Substrings marking bond funds.
    employer_tickers (Iterable[str]): Concentrated employer stock.

  Returns:
    str: Asset class label.
  """
  t = (ticker or "").upper()
  label = f"{t} {name or ''}".lower()
  if bond_tickers is None:
    bond_tickers = set(config.SECTORS.get("Bonds & Rates", [])) | set(
        config.SECTORS.get("Fixed Income & Preferred", []))
  cash_tickers = set(config.SECTORS.get("Cash & Money Market", [])) | set(
      getattr(config, "CASH_LIKE_TICKERS", ()))
  if t in employer_tickers:
    return "Employer Stock"
  if t.endswith("-USD") or t in ("BTC", "ETH", "SOL"):
    return "Crypto"
  # "CASH" is a broker placeholder row, not a fetchable ticker.
  if t == "CASH" or t in cash_tickers or "maturing" in label:
    return "Cash"
  if t in bond_tickers:
    return "Bond"
  if any(h.lower() in label for h in bond_name_hints):
    return "Bond"
  return "Equity"


def household_allocation(tsv_paths: Dict[str, str]) -> pd.DataFrame:
  """Aggregates several broker TSVs into an asset-class allocation.

  Args:
    tsv_paths (Dict[str, str]): Account label -> TSV path.

  Returns:
    pd.DataFrame: Index = account label, columns = asset classes (values
    in currency) plus ``Total``.
  """
  rows: List[Dict[str, Any]] = []
  for label, path in tsv_paths.items():
    if not os.path.exists(path):
      logger.warning("Missing account TSV: %s", path)
      continue
    df = pd.read_csv(path, sep="\t")
    if "Current_Value" not in df.columns:
      continue
    df = df[df["Current_Value"].fillna(0) > 0]
    row: Dict[str, Any] = {"Account": label}
    for _, h in df.iterrows():
      cls = classify_holding(str(h.get("Ticker", "")), str(h.get("Name", "")))
      row[cls] = row.get(cls, 0.0) + float(h["Current_Value"])
    rows.append(row)
  out = pd.DataFrame(rows).set_index("Account").fillna(0.0)
  out["Total"] = out.sum(axis=1)
  return out


# ==========================================
# PORTFOLIO CONSTRUCTION & CROSS-ASSET DIAGNOSTICS
# ==========================================
# Return-based tools for comparing a universe of funds: correlation
# clustering (no scipy needed), factor regressions ("how much of this ETF is
# just the market?"), diversification math, capture ratios, macro
# sensitivities, random-portfolio frontiers and fixed-weight backtests.


def load_close_matrix(tickers: Sequence[str],
                      tickers_dir: str,
                      start: Optional[Any] = None,
                      end: Optional[Any] = None) -> pd.DataFrame:
  """Loads a Date x Ticker matrix of (dividend-adjusted) closes.

  Args:
    tickers (Sequence[str]): Tickers with ``prices.tsv`` under tickers_dir.
    tickers_dir (str): ``market_data/tickers``.
    start (Optional[Any]): Inclusive start date.
    end (Optional[Any]): Inclusive end date.

  Returns:
    pd.DataFrame: Sorted DatetimeIndex, one float column per ticker found.
  """
  data: Dict[str, pd.Series] = {}
  for t in tickers:
    path = os.path.join(tickers_dir, t, "prices.tsv")
    if not os.path.exists(path):
      logger.warning("Price history missing for %s", t)
      continue
    df = pd.read_csv(path, sep="\t")
    if "Date" not in df.columns or "Close" not in df.columns:
      continue
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").drop_duplicates("Date").set_index("Date")
    data[t] = pd.to_numeric(df["Close"], errors="coerce")
  out = pd.DataFrame(data).sort_index()
  if start is not None:
    out = out.loc[pd.Timestamp(start):]
  if end is not None:
    out = out.loc[:pd.Timestamp(end)]
  return out


def periodic_returns(prices: pd.DataFrame, freq: str = "W-FRI") -> pd.DataFrame:
  """Simple returns at a lower frequency (last price per period).

  Args:
    prices (pd.DataFrame): Daily closes.
    freq (str): Pandas offset alias (``W-FRI``, ``ME`` …); ``D`` keeps daily.

  Returns:
    pd.DataFrame: Period returns with the first NaN row dropped.
  """
  px = prices if freq == "D" else prices.resample(freq).last()
  return px.pct_change().iloc[1:]


def perf_stats(prices: pd.Series,
               periods_per_year: int = 252,
               rf: float = 0.04) -> Dict[str, float]:
  """CAGR / vol / Sharpe / max drawdown / Calmar for a price or NAV series.

  Args:
    prices (pd.Series): Price or NAV series (DatetimeIndex).
    periods_per_year (int): 252 daily, 52 weekly, 12 monthly.
    rf (float): Annual risk-free rate used in the Sharpe ratio.

  Returns:
    Dict[str, float]: ``cagr, vol, sharpe, max_dd, calmar, total_return``
    (all in percent except sharpe/calmar).
  """
  s = prices.dropna()
  if len(s) < 2:
    return {
        k: float("nan")
        for k in ("cagr", "vol", "sharpe", "max_dd", "calmar", "total_return")
    }
  rets = s.pct_change().dropna()
  years = len(rets) / periods_per_year
  total = float(s.iloc[-1] / s.iloc[0] - 1)
  cagr = (1 + total)**(1 / years) - 1 if years > 0 else float("nan")
  vol = float(rets.std() * np.sqrt(periods_per_year))
  sharpe = (cagr - rf) / vol if vol > 0 else float("nan")
  dd = float((s / s.cummax() - 1).min())
  calmar = cagr / abs(dd) if dd < 0 else float("nan")
  return {
      "cagr": cagr * 100,
      "vol": vol * 100,
      "sharpe": sharpe,
      "max_dd": dd * 100,
      "calmar": calmar,
      "total_return": total * 100,
  }


def cluster_order(corr: pd.DataFrame) -> List[str]:
  """Orders labels by average-linkage hierarchical clustering (pure numpy).

  Distance = 1 − correlation. Clusters are merged greedily and the leaf
  order of the final tree is returned, which puts correlated assets next to
  each other in a heatmap.

  Args:
    corr (pd.DataFrame): Square correlation matrix.

  Returns:
    List[str]: Column labels in dendrogram leaf order.
  """
  labels = list(corr.columns)
  n = len(labels)
  if n <= 2:
    return labels
  dist = 1.0 - corr.values.astype(float)
  clusters: List[List[int]] = [[i] for i in range(n)]
  while len(clusters) > 1:
    best, pair = np.inf, (0, 1)
    for a, ca in enumerate(clusters):
      for b in range(a + 1, len(clusters)):
        d = dist[np.ix_(ca, clusters[b])].mean()
        if d < best:
          best, pair = d, (a, b)
    a, b = pair
    merged = clusters[a] + clusters[b]
    clusters = [c for i, c in enumerate(clusters) if i not in pair] + [merged]
  return [labels[i] for i in clusters[0]]


def factor_regression(returns: pd.DataFrame,
                      factors: pd.DataFrame,
                      periods_per_year: int = 52) -> pd.DataFrame:
  """OLS of each asset on a set of factor returns.

  Args:
    returns (pd.DataFrame): Asset returns (same frequency as factors).
    factors (pd.DataFrame): Factor returns (e.g. market, growth−value,
      semis−market). Aligned on the index.
    periods_per_year (int): For annualising alpha.

  Returns:
    pd.DataFrame: One row per asset with ``beta_<factor>`` columns,
    ``alpha_ann_%``, ``r2`` and ``unique_var_%`` (= 100·(1−R²), the share of
    variance the factors do *not* explain).
  """
  rows = []
  for col in returns.columns:
    df = pd.concat([returns[col], factors], axis=1).dropna()
    if len(df) < 20:
      continue
    y = df.iloc[:, 0].to_numpy(dtype=float)
    x = np.column_stack(
        [np.ones(len(df)), df.iloc[:, 1:].to_numpy(dtype=float)])
    coef, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ coef
    ss_res = float(((y - fitted)**2).sum())
    ss_tot = float(((y - y.mean())**2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    row: Dict[str, Any] = {"Ticker": col}
    for name, b in zip(factors.columns, coef[1:]):
      row[f"beta_{name}"] = round(float(b), 3)
    row["alpha_ann_%"] = round(float(coef[0]) * periods_per_year * 100, 2)
    row["r2"] = round(r2, 3)
    row["unique_var_%"] = round((1 - r2) * 100, 1)
    row["n"] = len(df)
    rows.append(row)
  return pd.DataFrame(rows).set_index("Ticker")


def effective_number_of_bets(weights: pd.Series, cov: pd.DataFrame) -> float:
  """Meucci effective number of bets from principal-portfolio risk shares.

  Computed on the covariance of the *held* assets only, so a single-asset
  portfolio scores exactly 1 regardless of the surrounding universe.

  Args:
    weights (pd.Series): Portfolio weights indexed like ``cov``.
    cov (pd.DataFrame): Covariance matrix of asset returns.

  Returns:
    float: Between 1 (one bet) and N (N independent equal bets).
  """
  w_full = weights.reindex(cov.index).fillna(0).astype(float)
  held = w_full[w_full.abs() > 1e-12].index
  if len(held) == 0:
    return float("nan")
  sub = cov.loc[held, held].values
  w = w_full[held].values
  eigval, eigvec = np.linalg.eigh(sub)
  eigval = np.clip(eigval, 0, None)
  pw = eigvec.T @ w
  contrib = (pw**2) * eigval
  total = contrib.sum()
  if total <= 0:
    return float("nan")
  p = contrib / total
  p = p[p > 0]
  return float(np.exp(-(p * np.log(p)).sum()))


def diversification_ratio(weights: pd.Series, cov: pd.DataFrame) -> float:
  """Weighted average vol divided by portfolio vol (1 = no diversification)."""
  w = weights.reindex(cov.index).fillna(0).values.astype(float)
  vols = np.sqrt(np.diag(cov.values))
  port_vol = float(np.sqrt(w @ cov.values @ w))
  return float((w * vols).sum() / port_vol) if port_vol > 0 else float("nan")


def marginal_diversification(returns: pd.DataFrame,
                             core: str,
                             weight: float = 0.10,
                             periods_per_year: int = 52) -> pd.DataFrame:
  """Effect of carving ``weight`` of a core holding into each other asset.

  Args:
    returns (pd.DataFrame): Periodic returns incl. the core column.
    core (str): Core ticker (e.g. ``VTI``).
    weight (float): Share moved from core into the satellite.
    periods_per_year (int): For annualising.

  Returns:
    pd.DataFrame: Per satellite: ``corr_core, beta_core, d_vol_pp,
    d_return_pp, d_sharpe`` (changes vs. 100% core) and ``d_max_dd_pp``.
  """
  core_r = returns[core].dropna()
  base_nav = (1 + core_r).cumprod()
  base = perf_stats(base_nav, periods_per_year)
  rows = []
  for col in returns.columns:
    if col == core:
      continue
    df = pd.concat([core_r, returns[col]], axis=1).dropna()
    if len(df) < 26:
      continue
    blend = (1 - weight) * df.iloc[:, 0] + weight * df.iloc[:, 1]
    b_nav = (1 + blend).cumprod()
    c_nav = (1 + df.iloc[:, 0]).cumprod()
    bs, cs = perf_stats(b_nav,
                        periods_per_year), perf_stats(c_nav, periods_per_year)
    cov = np.cov(df.iloc[:, 1], df.iloc[:, 0])
    beta = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else float("nan")
    rows.append({
        "Ticker": col,
        "corr_core": round(float(df.corr().to_numpy()[0, 1]), 3),
        "beta_core": round(float(beta), 2),
        "d_vol_pp": round(bs["vol"] - cs["vol"], 2),
        "d_return_pp": round(bs["cagr"] - cs["cagr"], 2),
        "d_sharpe": round(bs["sharpe"] - cs["sharpe"], 3),
        "d_max_dd_pp": round(bs["max_dd"] - cs["max_dd"], 2),
        "n": len(df),
    })
  out = pd.DataFrame(rows).set_index("Ticker")
  out.attrs["core_stats"] = base
  return out


def capture_ratios(returns: pd.DataFrame, bench: str) -> pd.DataFrame:
  """Up / down capture of each asset vs. a benchmark (periodic returns).

  Args:
    returns (pd.DataFrame): Periodic returns including ``bench``.
    bench (str): Benchmark column.

  Returns:
    pd.DataFrame: ``up_capture, down_capture, capture_spread`` (%), and
    ``hit_rate_down`` (% of benchmark-down periods the asset was positive).
  """
  b = returns[bench]
  up, down = b > 0, b < 0
  rows = []
  for col in returns.columns:
    if col == bench:
      continue
    a = returns[col]
    m = a.notna() & b.notna()
    if m.sum() < 20:
      continue
    uc = a[m & up].mean() / b[m & up].mean() * 100 if (m & up).any() else np.nan
    dc = a[m & down].mean() / b[m & down].mean() * 100 if (m & down).any() \
        else np.nan
    rows.append({
        "Ticker": col,
        "up_capture": round(float(uc), 1),
        "down_capture": round(float(dc), 1),
        "capture_spread": round(float(uc - dc), 1),
        "hit_rate_down": round(float((a[m & down] > 0).mean() * 100), 0),
    })
  return pd.DataFrame(rows).set_index("Ticker")


def macro_sensitivities(returns: pd.DataFrame,
                        macro: pd.DataFrame,
                        spec: Dict[str, Tuple[str, str]],
                        freq: str = "ME") -> pd.DataFrame:
  """Correlation of asset returns with macro-driver changes.

  Args:
    returns (pd.DataFrame): Periodic asset returns sampled at ``freq``.
    macro (pd.DataFrame): Daily macro frame (see :func:`load_macro_frame`).
    spec (Dict[str, Tuple[str, str]]): label -> (macro column, mode) where
      mode is ``"diff"`` (level change, for rates/spreads) or ``"pct"``
      (percent change, for prices/indices).
    freq (str): Resample alias matching ``returns`` (``ME``, ``W-FRI`` …).

  Returns:
    pd.DataFrame: Rows = assets, columns = driver labels, values = Pearson
    correlation of the asset's periodic return with the driver's change.
  """
  freq_px = macro.resample(freq).last()
  drivers = {}
  for label, (col, mode) in spec.items():
    if col not in macro.columns:
      continue
    s = freq_px[col]
    drivers[label] = s.diff() if mode == "diff" else s.pct_change()
  d = pd.DataFrame(drivers)
  out = {}
  for col in returns.columns:
    r = returns[col]
    row = {}
    for label in d.columns:
      j = pd.concat([r, d[label]], axis=1, join="inner").dropna()
      row[label] = round(float(j.corr().to_numpy()[0, 1]), 2) \
          if len(j) > 12 else np.nan
    out[col] = row
  return pd.DataFrame(out).T


def backtest_fixed_weights(prices: pd.DataFrame,
                           weights: Dict[str, float],
                           rebalance: str = "ME",
                           start: Optional[Any] = None) -> pd.Series:
  """NAV of a fixed-weight portfolio rebalanced at period ends.

  Args:
    prices (pd.DataFrame): Daily closes (columns ⊇ weights).
    weights (Dict[str, float]): Ticker -> weight (normalised internally).
    rebalance (str): Pandas offset alias for rebalance frequency.
    start (Optional[Any]): Start date (default: first date where all
      weighted tickers have data).

  Returns:
    pd.Series: NAV starting at 100.
  """
  cols = [c for c in weights if c in prices.columns]
  px = prices[cols].dropna()
  if start is not None:
    px = px.loc[pd.Timestamp(start):]
  w = np.array([weights[c] for c in cols], dtype=float)
  w = w / w.sum()
  rets = px.pct_change().fillna(0.0)
  periods = rets.groupby(pd.Grouper(freq=rebalance))
  nav_vals: List[float] = []
  nav = 100.0
  for _, grp in periods:
    if grp.empty:
      continue
    growth = (1 + grp).cumprod()
    port = (growth * w).sum(axis=1)  # within-period drift from start weights
    nav_vals.extend((nav * port).tolist())
    nav = nav * float(port.iloc[-1])
  return pd.Series(nav_vals, index=rets.index[:len(nav_vals)], name="NAV")


def random_portfolio_cloud(returns: pd.DataFrame,
                           n: int = 4000,
                           periods_per_year: int = 52,
                           seed: int = 7,
                           max_weight: float = 0.4) -> pd.DataFrame:
  """Long-only random portfolios for a return/vol frontier scatter.

  Args:
    returns (pd.DataFrame): Periodic returns (NaNs dropped row-wise).
    n (int): Number of portfolios.
    periods_per_year (int): For annualising.
    seed (int): RNG seed.
    max_weight (float): Rejection cap on any single weight.

  Returns:
    pd.DataFrame: ``vol, ret, sharpe, enb`` plus one weight column per asset.
  """
  r = returns.dropna()
  mu = r.mean().to_numpy(dtype=float) * periods_per_year
  cov = r.cov() * periods_per_year
  rng = np.random.default_rng(seed)
  rows: List[Dict[str, Any]] = []
  k = r.shape[1]
  while len(rows) < n:
    w = rng.dirichlet(np.ones(k) * 0.6)
    if w.max() > max_weight:
      continue
    vol = float(np.sqrt(w @ cov.values @ w))
    ret = float(w @ mu)
    rows.append({
        "vol": vol * 100,
        "ret": ret * 100,
        "sharpe": (ret - 0.04) / vol if vol > 0 else np.nan,
        "enb": effective_number_of_bets(pd.Series(w, index=r.columns), cov),
        **{
            f"w_{c}": wi for c, wi in zip(r.columns, w)
        },
    })
  return pd.DataFrame(rows)


def portfolio_point(returns: pd.DataFrame,
                    weights: Dict[str, float],
                    periods_per_year: int = 52) -> Dict[str, float]:
  """Annualised return / vol / Sharpe / ENB of a fixed-weight portfolio."""
  cols = [c for c in weights if c in returns.columns]
  r = returns[cols].dropna()
  w = pd.Series([weights[c] for c in cols], index=cols, dtype=float)
  w = w / w.sum()
  mu = r.mean() * periods_per_year
  cov = r.cov() * periods_per_year
  vol = float(np.sqrt(w.values @ cov.values @ w.values))
  ret = float((w * mu).sum())
  return {
      "ret": ret * 100,
      "vol": vol * 100,
      "sharpe": (ret - 0.04) / vol if vol > 0 else float("nan"),
      "enb": effective_number_of_bets(w, cov),
      "div_ratio": diversification_ratio(w, cov),
  }


if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description="Report utilities CLI")
  parser.add_argument("--render",
                      type=str,
                      help="Render a markdown file to PDF")
  parser.add_argument("--output",
                      type=str,
                      default=None,
                      help="Optional output PDF path")
  args = parser.parse_args()
  if args.render:
    pdf_out = render_markdown_to_pdf(args.render, output_path=args.output)
    print(f"Rendered PDF: {pdf_out}")
