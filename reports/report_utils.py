# pylint: disable=duplicate-code
import datetime
import difflib
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

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


def generate_rsi_dist200_scatter(df: pd.DataFrame, output_path: str):
  """
  Plot RSI vs Distance to 200MA.
  Identifies overextended vs oversold conditions for rotation timing.
  """
  if df.empty or 'RSI' not in df or 'Dist_to_200MA' not in df:
    logger.warning("No RSI/200MA data to plot scatter.")
    return

  plot_df = df.dropna(subset=['RSI', 'Dist_to_200MA']).copy()
  if plot_df.empty:
    return

  logger.info("Generating RSI vs 200MA Scatter plot...")
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

  plt.title('Technical Extension: RSI vs Distance to 200MA',
            fontweight='bold',
            fontsize=14)
  plt.xlabel('RSI (Momentum)', fontweight='bold')
  plt.ylabel('Distance to 200MA (%) (Trend Extension)', fontweight='bold')

  plt.tight_layout()
  plt.savefig(output_path, bbox_inches='tight', dpi=300)
  plt.close()
  logger.info(f"Generated RSI Scatter at {output_path}")


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
    max_items: int = 5,
    target_date: Optional[datetime.datetime] = None) -> str:
  """
    Takes a dict of {topic_dir_name: Display Label} and/or a list of tickers,
    aggregates, deduplicates via fuzzy matching, and returns a formatted Markdown string.
    Prioritizes detailed summaries if available (like from Alpha Vantage).
    """
  all_news = []
  tickers = tickers or []

  for topic, label in topics.items():
    df = get_recent_news(topic.lower(), market_data_dir, end_date=target_date)
    if df.empty:
      df = get_recent_news(topic, market_data_dir, end_date=target_date)
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

  for _, row in combined_df.iterrows():
    if not pd.notna(row['Date']) or not pd.notna(row['Headline']):
      continue

    headline = str(row['Headline']).strip()

    # Check similarity
    if any(_is_similar(headline, seen) for seen in seen_headlines):
      continue

    seen_headlines.append(headline)
    label = row.get('Source_Label', 'News')

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
    return "\n".join(news_items) + "\\n\\n"
  return ""


def build_ticker_context_markdown(tickers: List[str],
                                  market_data_dir: str) -> str:
  """Builds a dense Markdown string containing Intrinsic Value and Recent News for a specific list of tickers.
  Useful for injecting bespoke context into LLM prompts.
  """
  if not tickers:
    return ""

  context = "### Detailed Portfolio Context (News & Intrinsic Value)\\n"
  for t in tickers:
    # Fetch Intrinsic Value
    metrics = get_intrinsic_value_metrics(
        t, os.path.join(market_data_dir, "tickers"))
    if metrics:
      discount = metrics.get('Graham_Discount_Pct', 'N/A')
      context += f"- **{t}**: Intrinsic Discount: {discount}%\\n"

    # Fetch Ticker News
    news_df = get_recent_ticker_news(t, market_data_dir, limit=3)
    if not news_df.empty:
      context += f"  - Recent News for {t}:\\n"
      for _, r in news_df.iterrows():
        headline = r.get('Headline', '')[:100]
        if headline:
          context += f"    - {headline}...\\n"
  return context + "\\n"


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
      render_cmd = f"python3 '{report_utils_path}' --render '{out_path}'"
      os.system(render_cmd)
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
