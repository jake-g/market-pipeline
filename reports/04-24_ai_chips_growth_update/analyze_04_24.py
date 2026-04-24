#!/usr/bin/env python3
"""Generate a report for AI Chips and Growth holdings on 04-24.
Shows only percentages and no prices.
Uses existing data (no fetch).
Includes Sector Breakdown, Correlation Heatmap, Concentration Risk, and Trend Analysis.
Uses report_utils for correlation heatmap, technicals, and allocation bar chart.
Includes NotebookLM Critique.
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from tabulate import tabulate

# Load environment variables from local .env
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

# Add project root to path
PROJECT_ROOT = os.environ.get("PROJECT_ROOT")
if PROJECT_ROOT is None:
  raise ValueError("PROJECT_ROOT not set in environment")
sys.path.insert(0, PROJECT_ROOT)

import config
from market_fetcher import MarketFetcher
from reports import report_utils
from reports.notebooklm_client import MarketNewsClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
  logger.info("Starting 04-24 AI Chips and Growth Report Generation...")

  # 1. Extract Tickers and Combine

  project_root = os.environ.get("PROJECT_ROOT")
  file_1 = os.environ.get("PORTFOLIO_FILE_1")
  file_2 = os.environ.get("PORTFOLIO_FILE_2")

  path_1 = os.path.join(project_root, "portfolios", "tsvs", file_1)
  path_2 = os.path.join(project_root, "portfolios", "tsvs", file_2)

  if not os.path.exists(path_1) or not os.path.exists(path_2):
    logger.error("Portfolio files missing.")
    return

  df_1 = pd.read_csv(path_1, sep="\t")
  df_2 = pd.read_csv(path_2, sep="\t")
  df_combined = pd.concat([df_1, df_2])

  # Aggregate by Ticker
  df_agg = df_combined.groupby('Ticker').agg({
      'Name': 'first',
      'Quantity': 'sum',
      'Current_Value': 'sum',
      'Cost_Basis': 'sum'
  }).reset_index()

  # Filter out Index Funds and Cash
  INDEX_TICKERS = [
      'VTSAX', 'VIGAX', 'FAGOX', 'VUG', 'VTV', 'VTI', 'VGT', 'FASPX', 'SCHG',
      'VEA', 'VOO', 'SCHD', 'SOXQ', 'VWO', 'VDC', 'SCHH', 'FUTY', 'GLDM', 'VPU',
      'PFXF', 'PFFD', 'VDE', 'FENY', 'IBIT', 'VHT', 'CIBR', 'VIG', 'VIS', 'VYM'
  ]
  df_agg = df_agg[~df_agg['Ticker'].isin(INDEX_TICKERS) &
                  ~df_agg['Ticker'].isin(['CASH', 'VMFXX'])]

  # Calculate Weights
  total_val = df_agg['Current_Value'].sum()
  df_agg['Portfolio_Weight_Pct'] = (df_agg['Current_Value'] / total_val) * 100

  # Calculate Unrealized PnL % (Aggregate)
  df_agg['Unrealized_PnL_Pct'] = (
      (df_agg['Current_Value'] - df_agg['Cost_Basis']) /
      df_agg['Cost_Basis']) * 100

  # 2. Enrich with Technicals and Earnings
  enriched_data = []
  tickers_dir = os.path.join(PROJECT_ROOT, "market_data", "tickers")
  for _, row in df_agg.iterrows():
    ticker = row['Ticker']
    row_dict = row.to_dict()
    tech = report_utils.get_technical_indicators(ticker, tickers_dir)
    row_dict.update(tech)
    row_dict['Upcoming_Earnings'] = report_utils.get_upcoming_earnings(
        ticker, tickers_dir)
    enriched_data.append(row_dict)
  df_enriched = pd.DataFrame(enriched_data)

  # 3. Sector Mapping
  ticker_to_sector = {}
  for sector, t_list in config.SECTORS.items():
    for t in t_list:
      ticker_to_sector[t] = sector

  def map_sector(ticker):
    return ticker_to_sector.get(ticker, "Unclassified")

  df_enriched['Sector'] = df_enriched['Ticker'].apply(map_sector)

  # 4. Generate Visuals
  report_dir = os.path.join(PROJECT_ROOT, "reports",
                            "04-24_ai_chips_growth_update")
  plots_dir = os.path.join(report_dir, "plots")
  os.makedirs(plots_dir, exist_ok=True)

  # Donut Charts Side-by-Side
  df_sorted = df_enriched.sort_values(by='Portfolio_Weight_Pct',
                                      ascending=False)

  plot_df = df_sorted.copy()
  plot_df.loc[plot_df['Portfolio_Weight_Pct'] < 1.0, 'Ticker'] = 'Others'
  plot_df = plot_df.groupby(
      'Ticker')['Portfolio_Weight_Pct'].sum().reset_index()
  plot_df = plot_df.sort_values(by='Portfolio_Weight_Pct', ascending=False)

  df_sector = df_enriched.groupby(
      'Sector')['Portfolio_Weight_Pct'].sum().reset_index()
  df_sector = df_sector.sort_values(by='Portfolio_Weight_Pct', ascending=False)

  fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
  colors_ticker = sns.color_palette("hls", len(plot_df))
  colors_sector = sns.color_palette("Set3", len(df_sector))

  ax1.pie(plot_df['Portfolio_Weight_Pct'],
          labels=plot_df['Ticker'],
          autopct='%1.1f%%',
          startangle=140,
          colors=colors_ticker,
          pctdistance=0.85)
  centre_circle1 = plt.Circle((0, 0), 0.70, fc='white')
  ax1.add_artist(centre_circle1)
  ax1.set_title('Individual Stocks Allocation', fontweight='bold', fontsize=14)

  ax2.pie(df_sector['Portfolio_Weight_Pct'],
          labels=df_sector['Sector'],
          autopct='%1.1f%%',
          startangle=140,
          colors=colors_sector,
          pctdistance=0.85)
  centre_circle2 = plt.Circle((0, 0), 0.70, fc='white')
  ax2.add_artist(centre_circle2)
  ax2.set_title('Sector Breakdown', fontweight='bold', fontsize=14)

  plt.suptitle('Portfolio Overview (Individual Stocks)',
               fontweight='bold',
               fontsize=16)
  plt.tight_layout()
  plt.savefig(os.path.join(plots_dir, "allocation_combined.png"), dpi=200)
  plt.close()

  # Bar Chart for Allocation (using helper!)
  report_utils.plot_portfolio_allocation_bar(
      df_sorted, os.path.join(plots_dir, "allocation_bar.png"))

  # RSI vs 200MA Scatter Map (using helper!)
  report_utils.generate_rsi_dist200_scatter(
      df_sorted, os.path.join(plots_dir, "rsi_scatter.png"))

  # Correlation Heatmap for all individual stocks
  all_tickers = df_sorted['Ticker'].tolist()
  report_utils.plot_correlation_heatmap(all_tickers,
                                        tickers_dir,
                                        os.path.join(plots_dir,
                                                     "correlation_heatmap.png"),
                                        figsize=(24, 20))

  # 5. Performance Comparison & Metrics (YTD 2026)
  logger.info("Generating Performance Comparison...")
  df_spy = pd.read_csv(os.path.join(PROJECT_ROOT, "market_data", "tickers",
                                    "SPY", "prices.tsv"),
                       sep="\t")
  df_spy['Date'] = pd.to_datetime(df_spy['Date'])
  df_spy = df_spy.sort_values('Date')
  df_spy = df_spy[df_spy['Date'] >= '2026-01-01']

  spy_returns = df_spy['Close'] / df_spy['Close'].iloc[0]
  spy_dates = df_spy['Date']

  port_returns = pd.Series(0.0, index=None)
  first = True

  for _, row in df_sorted.iterrows():
    ticker = row['Ticker']
    weight = row['Portfolio_Weight_Pct'] / 100
    p_path = os.path.join(PROJECT_ROOT, "market_data", "tickers", ticker,
                          "prices.tsv")
    if os.path.exists(p_path):
      df_p = pd.read_csv(p_path, sep="\t")
      df_p['Date'] = pd.to_datetime(df_p['Date'])
      df_p = df_p.sort_values('Date')
      df_p = df_p[df_p['Date'] >= '2026-01-01']
      if not df_p.empty:
        rets = df_p['Close'] / df_p['Close'].iloc[0]
        rets.index = df_p['Date']
        if first:
          port_returns = rets * weight
          first = False
        else:
          port_returns = port_returns.add(rets * weight, fill_value=0)

  # Align indexes
  spy_returns.index = spy_dates
  df_compare = pd.DataFrame({
      'Portfolio': port_returns,
      'SPY': spy_returns
  }).dropna()

  # Calculate Metrics
  port_total_return = (df_compare['Portfolio'].iloc[-1] - 1) * 100
  spy_total_return = (df_compare['SPY'].iloc[-1] - 1) * 100

  port_daily_rets = df_compare['Portfolio'].pct_change().dropna()
  spy_daily_rets = df_compare['SPY'].pct_change().dropna()

  port_vol = port_daily_rets.std() * 100  # Daily vol in %
  spy_vol = spy_daily_rets.std() * 100

  port_max_dd = (df_compare['Portfolio'] / df_compare['Portfolio'].cummax() -
                 1).min() * 100
  spy_max_dd = (df_compare['SPY'] / df_compare['SPY'].cummax() - 1).min() * 100

  metrics_data = [[
      "Total Return (YTD)", f"{port_total_return:+.2f}%",
      f"{spy_total_return:+.2f}%"
  ], ["Daily Volatility", f"{port_vol:.2f}%", f"{spy_vol:.2f}%"],
                  ["Max Drawdown", f"{port_max_dd:.2f}%", f"{spy_max_dd:.2f}%"]]
  metrics_table = tabulate(metrics_data,
                           headers=["Metric", "Portfolio", "SPY"],
                           tablefmt="pipe")

  # Plot
  plt.figure(figsize=(12, 6))
  plt.plot(df_compare.index, (df_compare['Portfolio'] - 1) * 100,
           label='Portfolio',
           color='purple',
           linewidth=2.5)
  plt.plot(df_compare.index, (df_compare['SPY'] - 1) * 100,
           label='S&P 500 (SPY)',
           color='grey',
           linestyle='--')
  plt.title('YTD 2026 Performance: Portfolio vs SPY',
            fontweight='bold',
            fontsize=14)
  plt.xlabel('Date')
  plt.ylabel('Cumulative Return (%)')
  plt.legend()
  plt.grid(True, alpha=0.3)

  outperf = port_total_return - spy_total_return
  plt.text(df_compare.index[-1],
           port_total_return,
           f"  Outperformance: {outperf:+.2f}%",
           va='center',
           fontweight='bold',
           color='purple')

  plt.tight_layout()
  plt.savefig(os.path.join(plots_dir, "performance_comparison.png"), dpi=200)
  plt.close()

  # 6. Concentration Risk
  top_5_sum = df_sorted.head(5)['Portfolio_Weight_Pct'].sum()
  concentration_md = f"**Concentration Risk Note**: The top 5 holdings account for **{top_5_sum:.2f}%** of this growth portfolio."

  # 7. Non-Robotic Action Targets & Trend Analysis
  actions = []
  for _, r in df_sorted.iterrows():
    t = r['Ticker']
    rsi = r.get('RSI')
    disc = r.get('Discount_to_Intrinsic_Value_Pct')

    if pd.isna(rsi):
      continue

    if rsi >= 70:
      actions.append(
          f"- 🚨 **{t}**: Scorching momentum with an RSI of **{rsi:.1f}**. Sitting **{r['Dist_to_200MA']:.1f}%** above its 200MA. Consider trimming or using trailing stops to protect gains!"
      )
    elif rsi <= 40:
      actions.append(
          f"- 🟢 **{t}**: Technically oversold (RSI: **{rsi:.1f}**). This could be a prime accumulation zone if you believe in the long-term story."
      )
    elif isinstance(disc, (int, float)) and disc >= 30:
      actions.append(
          f"- 💎 **{t}**: Flying under the radar with a deep intrinsic discount of **{disc:.1f}%**. Momentum is neutral (RSI: {rsi:.1f}), making it a solid value play."
      )
    elif r['Dist_to_200MA'] < 5:
      actions.append(
          f"- 📉 **{t}**: Hovering just **{r['Dist_to_200MA']:.1f}%** above its 200MA. Watching for a bounce or breakdown."
      )

  actions_md = "## 🎯 Actionable Insights & Alerts\n\n" + "\n".join(actions)

  # 8. Earnings Analysis
  logger.info("Processing earnings analysis...")
  upcoming_earnings = df_sorted[df_sorted['Upcoming_Earnings'] != ""].head(10)

  earnings_md = "## 🔮 Earnings Watch\n\n"
  if not upcoming_earnings.empty:
    plt.figure(figsize=(10, 6))
    plt.bar(upcoming_earnings['Ticker'],
            upcoming_earnings['RSI'],
            color='salmon')
    plt.axhline(y=70, color='r', linestyle='--', alpha=0.5)
    plt.axhline(y=30, color='g', linestyle='--', alpha=0.5)
    plt.title('RSI for Tickers with Upcoming Earnings', fontweight='bold')
    plt.ylabel('RSI')
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "earnings_rsi.png"), dpi=200)
    plt.close()

    earnings_md += "![Earnings RSI](plots/earnings_rsi.png)\n\n"
    earnings_md += "### Upcoming Prints Speculation\n"
    for _, r in upcoming_earnings.iterrows():
      earnings_md += f"- **{r['Ticker']}** (Earnings: {r['Upcoming_Earnings']}): RSI is **{r['RSI']:.1f}**. "
      if r['RSI'] >= 70:
        earnings_md += "Priced for perfection going into the print. High risk of gap down on any miss.\n"
      elif r['RSI'] <= 40:
        earnings_md += "Sentiment is depressed. A beat could trigger a strong relief rally.\n"
      else:
        earnings_md += "Neutral momentum. Focus will be on guidance.\n"
  else:
    earnings_md += "*No upcoming earnings found in the immediate horizon.*\n"

  # 9. Generate Markdown Table (Anonymized but Detailed)
  desired_cols = [
      'Ticker', 'Name', 'Sector', 'Quantity', 'Portfolio_Weight_Pct',
      'Unrealized_PnL_Pct', 'Discount_to_Intrinsic_Value_Pct', 'RSI',
      'Dist_to_200MA', 'Upcoming_Earnings'
  ]
  actual_cols = [c for c in desired_cols if c in df_sorted.columns]
  display_df = df_sorted[actual_cols].copy()

  if 'Discount_to_Intrinsic_Value_Pct' in display_df.columns:
    display_df['Discount_to_Intrinsic_Value_Pct'] = display_df[
        'Discount_to_Intrinsic_Value_Pct'].fillna("N/A")

  display_df = display_df.fillna("-")

  if 'Portfolio_Weight_Pct' in display_df.columns:
    display_df['Portfolio_Weight_Pct'] = display_df[
        'Portfolio_Weight_Pct'].apply(lambda x: f"{x:.2f}%" if x != "-" else x)
  if 'Unrealized_PnL_Pct' in display_df.columns:
    display_df['Unrealized_PnL_Pct'] = display_df['Unrealized_PnL_Pct'].apply(
        lambda x: f"{x:+.2f}%" if x not in ["-", "0.00%"] else x)
  if 'Discount_to_Intrinsic_Value_Pct' in display_df.columns:
    display_df['Discount_to_Intrinsic_Value_Pct'] = display_df[
        'Discount_to_Intrinsic_Value_Pct'].apply(
            lambda x: f"{x:.2f}%" if x not in ["-", "N/A"] else x)

  table_md = tabulate(display_df.values.tolist(),
                      headers=display_df.columns.tolist(),
                      tablefmt="pipe")

  table_md += (
      "\n\n*Note: N/A indicates that intrinsic value could not be calculated.*")

  # 10. Write REPORT.md
  report_path = os.path.join(report_dir, "REPORT.md")

  report_md = f"""# 04-24 Chip & AI Growth Strategy Report

*Date: April 24, 2026*

This report provides an anonymized overview of the holdings in the **Chip & AI Growth Strategy**. All prices and absolute dollar values have been omitted per your request. **Index funds and cash positions have been excluded to focus solely on individual stock exposure.**

## 📊 Allocation & Sector Breakdown

![Allocation](plots/allocation_combined.png)
*💡 **Note**: Slices smaller than 1% are grouped into 'Others' for readability.*

![Allocation Bar](plots/allocation_bar.png)
*💡 **Note**: Horizontal bar chart showing relative weights of all individual holdings.*

## 🧭 Technical Extension: RSI vs 200MA Map
![RSI Map](plots/rsi_scatter.png)
*💡 **Note**: This scatter plot maps momentum (RSI on Y-axis) against trend extension (Distance to 200-day Moving Average on X-axis).*

## 📈 Performance Comparison (YTD 2026)

![Performance](plots/performance_comparison.png)

### Performance Metrics vs SPY
{metrics_table}

## 📈 Correlation Analysis

![Heatmap](plots/correlation_heatmap.png)
*💡 **Caption**: Daily returns correlation for all individual holdings (Trailing 6 Months).*

## 🔍 Concentration Risk

{concentration_md}

{actions_md}

{earnings_md}

## 📑 Holdings Table

{table_md}

---
*Report generated automatically on 2026-04-24.*
"""

  with open(report_path, "w") as f:
    f.write(report_md)

  logger.info("✅ Core report generated at %s", report_path)

  # 11. NotebookLM Critique
  logger.info("Fetching critique from NotebookLM...")
  try:
    async with MarketNewsClient(
        project_name="04-24 Growth Strategy Critique") as client:
      await client.connect()
      await client.upload_news_text(f"GENERATED REPORT:\n{report_md}",
                                    "04-24_Context")
      critique = await client.ask_question(
          "Act as a senior macroeconomic strategist. Critique the holdings, "
          "risks, and strategies for this portfolio based on the provided overview. "
          "Do not assume any price data not shown.")
      await client.delete_project()
      if critique:
        with open(report_path, "a") as f:
          f.write(
              f"\n## 🤖 NotebookLM Red-Team Critique\n<details>\n"
              f"<summary>View Critique</summary>\n\n{critique}\n\n</details>")
        logger.info("✅ Critique appended.")
  except Exception as e:
    logger.warning("NotebookLM failed: %s", e)


if __name__ == "__main__":
  asyncio.run(main())
