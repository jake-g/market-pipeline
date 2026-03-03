"""Intrinsic Value Screener - Quantitative Analytical Engine.

This script scans the pre-processed fundamental data from the pipeline to compute
Graham Intrinsic Value bounds, filter out overvalued equities, and dynamically
map out a decision-tree based action plan based on current market yield and EPS.
"""

import datetime
import logging
import os
import sys

from graphviz import Digraph
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from market_fetcher import SKIP_EARNINGS
from reports.report_utils import generate_portfolio_markdown_table
from reports.report_utils import get_intrinsic_value_metrics
from reports.report_utils import setup_decision_tree_aesthetics
from reports.report_utils import setup_plot_aesthetics

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(OUTPUT_DIR, '../..'))

DATA_DIR = os.path.join(project_root, "market_data")
TICKERS_DIR = os.path.join(DATA_DIR, "tickers")

# Output layout shared with growth pipeline
PLOTS_DIR = os.path.join(OUTPUT_DIR, "plots")
REPORT_FILE = os.path.join(OUTPUT_DIR, "REPORT.md")
os.makedirs(PLOTS_DIR, exist_ok=True)

logger = logging.getLogger(__name__)


def fetch_screener_data(limit=None) -> pd.DataFrame:
  """Loads fundamental metrics (Intrinsic Value, EPS Surprise) across all downloaded tickers."""
  logger.info("Scanning local data directory for Intrinsic Value metrics...")

  if not os.path.exists(TICKERS_DIR):
    logger.error(f"Tickers directory not found at {TICKERS_DIR}")
    return pd.DataFrame()

  results = []
  count = 0

  for ticker_folder in os.listdir(TICKERS_DIR):
    ticker_path = os.path.join(TICKERS_DIR, ticker_folder)
    if not os.path.isdir(ticker_path):
      continue

    # Skip known ETFs, indices, and macro tickers that do not have intrinsic values
    if ticker_folder.upper() in SKIP_EARNINGS:
      continue

    # Get Graham Value and Discount
    metrics = get_intrinsic_value_metrics(ticker_folder, TICKERS_DIR)
    if not metrics:
      continue

    # Load Prices and Technicals
    current_price = np.nan
    try:
      pdf = pd.read_csv(os.path.join(ticker_path, "prices.tsv"), sep="\t")
      if not pdf.empty:
        current_price = float(pdf.iloc[-1]["Close"])
        pdf['Date'] = pd.to_datetime(pdf['Date'])
        pdf = pdf.sort_values('Date').reset_index(drop=True)

        from reports.report_utils import calculate_technical_metrics
        tech_metrics = calculate_technical_metrics(pdf)

        metrics["RSI"] = tech_metrics.get("RSI", np.nan)
        metrics["Dist_to_200MA"] = tech_metrics.get("Dist_to_200MA", np.nan)
        metrics["MACD"] = tech_metrics.get("MACD", np.nan)
        metrics["MA_Cross"] = tech_metrics.get("MA_Cross", "N/A")
      else:
        raise ValueError("Empty prices dataframe")
    except Exception as e:
      metrics["RSI"] = np.nan
      metrics["Dist_to_200MA"] = np.nan
      metrics["MACD"] = np.nan
      metrics["MA_Cross"] = "N/A"

    discount = metrics["Discount_to_Intrinsic_Value_Pct"]

    # Get most recent EPS Surprise (if available)
    eps_surprise = 0.0
    earnings_file = os.path.join(ticker_path, "earnings.tsv")
    if os.path.exists(earnings_file):
      try:
        edf = pd.read_csv(earnings_file, sep='\t')
        edf = edf.dropna(subset=['Surprise(%)'])
        if not edf.empty:
          # Sort to get the most recent actual earning
          edf['Earnings Date'] = pd.to_datetime(edf['Earnings Date'], utc=True)
          edf = edf.sort_values(by='Earnings Date', ascending=False)
          eps_surprise = float(edf.iloc[0]['Surprise(%)'])
      except Exception:
        pass

    metrics["Last_EPS_Surprise_Pct"] = eps_surprise

    metrics["Current_Price"] = current_price

    results.append(metrics)
    count += 1

    if limit and count >= limit:
      break

  df = pd.DataFrame(results)
  if not df.empty:
    # Sort by Discount
    df = df.sort_values(by="Discount_to_Intrinsic_Value_Pct", ascending=False)

  return df


def generate_screening_scatter(df: pd.DataFrame, output_path: str):
  """Generates the EPS Surprise vs. Intrinsic Value Discount scatter plot."""
  if df.empty:
    logger.warning("No data to plot.")
    return

  setup_plot_aesthetics()

  # Tighter outlier filtering for better zoom and readability
  plot_df = df.copy()

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

  scatter = sns.scatterplot(data=plot_df,
                            x='Last_EPS_Surprise_Pct',
                            y='Discount_to_Intrinsic_Value_Pct',
                            hue='Current_Price',
                            palette='viridis',
                            size='Current_Price',
                            sizes=(30, 300),
                            alpha=0.7,
                            edgecolor='black')

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


DATA_DIR = os.path.join(project_root, "market_data")
TICKERS_DIR = os.path.join(DATA_DIR, "tickers")
# Layout shared with the secondary sub-analysis pipelines
assets_dir = os.path.join(OUTPUT_DIR, "plots")
final_report_md = os.path.join(OUTPUT_DIR, "REPORT.md")

os.makedirs(assets_dir, exist_ok=True)

# Application logger configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def build_decision_tree(df: pd.DataFrame):
  """Generates a quantitative Graphviz decision tree mapping value actionability."""
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

  out_path = os.path.join(assets_dir, 'value_decision_tree')
  dot.render(out_path, format='png', cleanup=True)


def generate_report(df: pd.DataFrame):
  """Compiles the analytical data into the final markdown report."""
  logger.info("Generating Final Markdown Report...")

  with open(final_report_md, 'w') as f:
    f.write("# Algorithmic Value Strategy - Screener Output\n\n")

    asset_count = len(df)
    f.write("## Executive Summary\n")
    f.write(
        f"> *Analyzed **{asset_count} equities** utilizing Benjamin Graham's revised Intrinsic Value formula, substituting contemporary bond yields and trailing EPS. Objective: Identify deep-value dislocations in the market where growth estimates have not kept pace with pricing reality.*\n\n"
    )

    valid_df = df.dropna(subset=['Discount_to_Intrinsic_Value_Pct'])
    if not valid_df.empty:
      top_discount = valid_df.iloc[0]
      f.write(
          f"- **Highest Margin of Safety:** {top_discount['Ticker']} (Trading at a {top_discount['Discount_to_Intrinsic_Value_Pct']:,.1f}% discount)\n\n"
      )

    f.write("## Data Quality & Potential Issues\n")
    missing_graham = df['Graham_Value'].isna().sum()
    missing_eps = df['Last_EPS_Surprise_Pct'].isna().sum()
    missing_price = df['Current_Price'].isna().sum()

    f.write(
        f"> **Pipeline Diagnostics:** Out of `{asset_count}` tickers analyzed, there are some data gaps that may affect metric coverage:\n"
    )
    f.write(
        f"> - Missing Intrinsic Value (Often lacking Forward EPS/Growth projection): **{missing_graham}** tickers\n"
    )
    f.write(
        f"> - Missing EPS Surprise (Missing quarterly expectations): **{missing_eps}** tickers\n"
    )
    f.write(f"> - Missing Current Price data: **{missing_price}** tickers\n\n")

    f.write("## Execution Matrix\n")
    f.write(
        "Based on raw pricing efficiency against terminal growth estimates, the following dynamic decision matrix dictates capital flow.\n\n"
    )
    f.write("![Decision Tree](./plots/value_decision_tree.png)\n\n")

    # SECONDARY ANALYTICS
    f.write("---\n## Analytical Output\n\n")

    f.write("### 📉 Dislocation Curve (Value vs Earnings Surprise)\n")
    f.write(
        "The following scatter plot maps theoretical discount against actual corporate earnings execution. "
    )
    f.write(
        "Equities in the **upper-right quadrant** represent the holy grail of value investing: severely undervalued companies that are consistently beating consensus earnings.\n\n"
    )
    f.write(
        "![Intrinsic Value Scatter Plot](./plots/intrinsic_value_scatter.png)\n\n"
    )
    f.write("> [!CAUTION]\n")
    f.write(
        "> **The Value Trap:** High-discount equities residing in the *lower-left* quadrant are actively missing earnings, suggesting their 'cheap' valuation is a direct function of collapsing forward guidance rather than market inefficiency.\n\n"
    )

    f.write(f"### 🏆 Top Deep Value Targets\n")
    f.write(
        "*Filtered for positive execution (Surprise > 0) and high margin of safety (Discount > 0).*\n\n"
    )

    # Format dataframe for the markdown table generator
    valid_df = df.dropna(
        subset=['Discount_to_Intrinsic_Value_Pct', 'Last_EPS_Surprise_Pct'])
    filtered_df = valid_df[(valid_df['Discount_to_Intrinsic_Value_Pct'] > 0) &
                           (valid_df['Last_EPS_Surprise_Pct'] > 0)]
    display_df = filtered_df.head(25).copy()

    if display_df.empty:
      f.write(
          "> *No tickers currently meet the strict Deep Value criteria (Discount > 0 and EPS Surprise > 0).* \n\n"
      )
      display_df = valid_df.head(
          15).copy()  # fallback to just top 15 by discount
      f.write(f"*(Falling back to top 15 unconditional discounts)*\n\n")

    display_df['Name'] = display_df['Ticker']
    display_df['Portfolio_Weight_Pct'] = 0.0
    display_df['Unrealized_PnL_Pct'] = 0.0

    if 'Dist_to_200MA' in display_df:
      display_df['Dist_to_200MA'] = display_df['Dist_to_200MA'].fillna(0.0)
    else:
      display_df['Dist_to_200MA'] = 0.0

    if 'RSI' in display_df:
      display_df['RSI'] = display_df['RSI'].fillna(0.0)
    else:
      display_df['RSI'] = 0.0

    if 'MACD' in display_df:
      display_df['MACD'] = display_df['MACD'].fillna(0.0)
    else:
      display_df['MACD'] = 0.0

    if 'MA_Cross' in display_df:
      display_df['MA_Cross'] = display_df['MA_Cross'].fillna("N/A")
    else:
      display_df['MA_Cross'] = "N/A"

    display_df['Time_Horizon'] = "Value Hold (Years)"
    display_df['Exit_Strategy'] = "Mean Reversion to Fair Value"

    table_md = generate_portfolio_markdown_table(display_df)
    f.write(table_md)
    f.write("\n\n")

    f.write(
        "---\n*Generated algorithmically by `intrinsic_value_report.py`.*\n")


if __name__ == "__main__":
  logger.info("Starting Intrinsic Value Engine...")

  # Load all valid fundamental metrics across the entire dataset without arbitrary limit
  screener_df = fetch_screener_data(limit=None)

  if screener_df.empty:
    logger.error(
        "Loaded dataframe is empty. Ensure `./run_fetch.sh` has pulled data. Exiting."
    )
    sys.exit(1)

  logger.info("Generating Visuals...")

  # Ensure the graph dependencies load the correct path
  plot_path = os.path.join(PLOTS_DIR, "intrinsic_value_scatter.png")
  generate_screening_scatter(screener_df, plot_path)
  build_decision_tree(screener_df)

  generate_report(screener_df)

  logger.info("Execution Pipeline Complete. Check REPORT.md")
