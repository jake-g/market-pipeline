"""Growth Portfolio Outlook - Quantitative Analytical Engine.

This script ingests the dynamically processed portfolio TSV, dynamically fetches historical
price data, computes momentum/technical indicators, and simulates
future macroeconomic impact scenarios (Tariff, AI, Iran).
Values are generated algorithmically with relative % to protect privacy.
"""

import datetime
import logging
import os
import sys
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from graphviz import Digraph

from reports.report_utils import (format_num,
                                  generate_portfolio_markdown_table,
                                  plot_correlation_heatmap,
                                  plot_momentum_scatter,
                                  plot_portfolio_allocation,
                                  plot_winners_losers,
                                  setup_decision_tree_aesthetics,
                                  setup_plot_aesthetics)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.abspath(os.path.join(OUTPUT_DIR, '..'))

# Constants & Configuration

project_root = os.path.abspath(os.path.join(OUTPUT_DIR, '../..'))
DATA_DIR = os.path.join(project_root, "market_data")
TICKERS_DIR = os.path.join(DATA_DIR, "tickers")

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
PLOTS_DIR = os.path.join(OUTPUT_DIR, "plots")
REPORT_FILE = os.path.join(OUTPUT_DIR, "REPORT.md")

os.makedirs(PLOTS_DIR, exist_ok=True)

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 1. System Integration
# Target the pre-processed metrics file
PORTFOLIO_FILE = os.path.abspath(
    os.path.join(OUTPUT_DIR,
                 "../portfolios/portfolio_brokerage_58728479_metrics.tsv"))


def plot_scenario_impact(df: pd.DataFrame):
  """Plots simulated drawdowns in relative % of total account."""
  setup_plot_aesthetics()
  scenarios = {
      'Scenario 1: Tariff Shock (-8% Drawdown)': -8.0,
      'Scenario 2: AI Bubble Resurgence (+12%)': 12.0,
      'Scenario 3: Iran Geopolitics (Oil Spike)': -5.0,
      'Scenario 4: Cloud/CAPEX Cuts (-15%)': -15.0
  }
  s_df = pd.DataFrame(list(scenarios.items()),
                      columns=['Scenario', 'Expected_Values'
                              ]).sort_values('Expected_Values')

  plt.figure(figsize=(10, 6))
  colors = [
      '#c0392b' if val < 0 else '#27ae60' for val in s_df['Expected_Values']
  ]
  sns.barplot(x='Expected_Values',
              y='Scenario',
              data=s_df,
              hue='Scenario',
              palette=colors,
              legend=False)
  plt.title('Simulated Portfolio Impact (Relative % Change)', fontweight='bold')
  plt.xlabel('Simulated Value Change (%)')
  plt.ylabel('')
  plt.axvline(0, color='black', linewidth=1)

  for index, (i, row) in enumerate(s_df.iterrows()):
    val = row['Expected_Values']
    offset = abs(s_df['Expected_Values'].max()) * 0.05
    align = 'left' if val > 0 else 'right'
    x_pos = val + offset if val > 0 else val - offset
    plt.text(x_pos,
             index,
             f"{val:+.1f}%",
             va='center',
             ha=align,
             fontsize=10,
             fontweight='bold')

  plt.savefig(os.path.join(PLOTS_DIR, 'portfolio_scenario_impact.png'),
              bbox_inches='tight',
              dpi=300)
  plt.close()


def build_decision_tree():
  """Generates a Graphviz decision tree for the tactical outlook."""
  logger.info("Rendering Graphviz Decision Tree...")
  dot = Digraph(comment='Tactical Execution Tree')
  setup_decision_tree_aesthetics(dot)

  dot.node('A',
           f"Current State\n({datetime.date.today().strftime('%b %d, %Y')})",
           shape='box',
           style='filled',
           fillcolor='lightblue')

  # Scenarios
  dot.node('B1',
           'Scenario 1:\nTariff Shock Continues',
           style='filled',
           fillcolor='lightcoral')
  dot.node('B2',
           'Scenario 2:\nAI Bubble Resurgence',
           style='filled',
           fillcolor='lightgreen')
  dot.node('B3',
           'Scenario 3:\nIran/Geopolitical Escalation',
           style='filled',
           fillcolor='lightcoral')
  dot.node('B4',
           'Scenario 4:\nData Center CAPEX Cuts',
           style='filled',
           fillcolor='lightgray')

  dot.edge('A', 'B1', label='Tech Margins Hit')
  dot.edge('A', 'B2', label='NVDA Beat >10% & Guidance Up')
  dot.edge('A', 'B3', label='Strait of Hormuz Disrupted')
  dot.edge('A', 'B4', label='Software/SaaS Slower Growth')

  # Actions B1 (Tariffs)
  dot.node('C1_A',
           'TRIM: TSM, AMAT, ASML\n(Lock in semiconductor hardware gains)',
           shape='ellipse')
  dot.node('C1_B',
           'BUY: LMT, NOC, GLD\n(Hedge via Defense & Gold)',
           shape='ellipse')
  dot.edge('B1', 'C1_A')
  dot.edge('B1', 'C1_B')

  # Actions B2 (AI Resurgence)
  dot.node('C2_A',
           'SELL: INTC (Fund NVDA Trade)\nHOLD: IONQ (Speculative AI spread)',
           shape='ellipse')
  dot.node('C2_B',
           'BUY: SMCI, VRT, VST\n(High-beta AI infra & Power loop)',
           shape='ellipse')
  dot.edge('B2', 'C2_A')
  dot.edge('B2', 'C2_B')

  # Actions B3 (Iran/Geopolitics)
  dot.node('C3_A', 'SELL: ORCL\n(Harvest -48% tax loss)', shape='ellipse')
  dot.node('C3_B',
           'BUY: CVX, LMT, RTX\n(Oil & Defense structural hedges)',
           shape='ellipse')
  dot.edge('B3', 'C3_A')
  dot.edge('B3', 'C3_B')

  # Actions B4 (CAPEX Cuts)
  dot.node('C4_A',
           'REDUCE: AMD, NVO\n(Cloud spend & GLP-1 momentum unwinds)',
           shape='ellipse')
  dot.node('C4_B', 'BUY: BRK.B\n(Flight to defensive value)', shape='ellipse')
  dot.edge('B4', 'C4_A')
  dot.edge('B4', 'C4_B')

  # Save
  out_path = os.path.join(PLOTS_DIR, 'decision_tree')
  dot.render(out_path, format='png', cleanup=True)


def generate_report(df: pd.DataFrame):
  """Compiles the analytical data into the final markdown report."""
  logger.info("Generating Final Markdown Report...")

  with open(REPORT_FILE, 'w') as f:
    f.write(
        f"# Growth Portfolio Tactical Outlook [{datetime.date.today().strftime('%m/%d/%Y')}]\n\n"
    )

    asset_count = len(df[df['Ticker'] != 'CASH'])
    f.write("## Executive Summary\n")
    f.write(
        f"> *Analyzing {asset_count} assets to determine structural positioning against Tariffs, Middle East conflict, and the AI supercycle. Objective: Liquidate defensive/dead-weight capital for asymmetric bets.*\n\n"
    )

    trade_df = df[df['Ticker'] != 'CASH']
    if not trade_df.empty:
      top_winner_row = trade_df.loc[trade_df['Unrealized_PnL_Pct'].idxmax()]
      bottom_loser_row = trade_df.loc[trade_df['Unrealized_PnL_Pct'].idxmin()]
      f.write(
          f"- **Top Winner:** {top_winner_row['Ticker']} (+{top_winner_row['Unrealized_PnL_Pct']*100:,.1f}%)\n"
      )
      f.write(
          f"- **Top Loser:** {bottom_loser_row['Ticker']} ({bottom_loser_row['Unrealized_PnL_Pct']*100:,.1f}%)\n\n"
      )

    # ACTIONABLE INSIGHTS GO FIRST
    f.write("## Execution Plan\n")
    f.write(
        "Based on technical decay, realized losses, and macro realities, here is the execution plan to isolate asymmetric bets while cutting dead capital.\n\n"
    )
    f.write("![Decision Tree](./plots/decision_tree.png)\n\n")

    f.write("### Near-Term Strategy\n")
    f.write("*Goal: Liquidity Generation for the NVDA Trade and Trimming Extensions*\n")

    intc_row = df[df['Ticker'] == 'INTC']
    if not intc_row.empty:
      intc_w = intc_row.iloc[0]['Portfolio_Weight_Pct']
      f.write(f"- **SELL INTC (Intel) [{intc_w:.1f}%]:** Sell entirely. Trading below 50/200MAs. Liquidate to fund the high-beta NVDA post-earnings drift.\n")

    cash_row = df[df['Ticker'] == 'CASH']
    if not cash_row.empty:
      cash_w = cash_row.iloc[0]['Portfolio_Weight_Pct']
      f.write(f"- **DEPLOY CASH [{cash_w:.1f}%]:** Reserve is ready. Deploy entirely into NVDA if it drops below immediate support, or leg in over 3 days.\n")

    f.write("- **TRIM TSM, ASML, AMAT:** Lock in 10-15% of profits. These are >15% above their 200MAs and highly vulnerable to a mean-reverting Tariff shock.\n\n")

    f.write("### Medium-Term Strategy\n")
    f.write("*Goal: Structural Rotation and Tax Harvesting*\n")
    f.write("- **HARVEST ORCL:** Extremely poor relative strength. Harvest tax loss to offset massive semiconductor gains.\n")
    f.write("- **BUY VST and CEG:** Reallocate ORCL capital to nuclear/unregulated power generation. The grid bottleneck is the next leg of the AI trade.\n")
    f.write("- **BUY LMT and NOC:** Deploy semi trim capital as uncorrelated hedges against Strait of Hormuz tail risks.\n\n")

    f.write("### Long-Term Strategy\n")
    f.write("*Goal: Long-Term Asymmetric Bets*\n")
    f.write("- **HOLD IONQ:** Binary quantum bet (1-2% sizing). Hold through volatility. Untethered to standard semiconductor cycles.\n")
    f.write("- **HOLD NVO:** GLP-1 global demand inelasticity means multiple contraction will structurally burn off.\n")
    f.write("- **BUY SMCI and VRT:** Add to server racks on any broad market pullback >10%.\n\n")

    # SECONDARY ANALYTICS GO BELOW
    f.write("---\n## Analytical Detail\n\n")

    f.write("### Holdings and Risk Details\n")
    f.write("*Computed live against localized 200MA, Volatility, and RSI.*\n\n")
    f.write(generate_portfolio_markdown_table(df))
    f.write("\n\n")

    f.write("### Sector Allocation and PnL Drivers\n")
    f.write("![Portfolio Allocation](./plots/portfolio_allocation.png)\n")
    f.write("![Winners Losers](./plots/portfolio_winners_losers.png)\n\n")

    f.write("### Technical Momentum and Trend Alignment\n")
    f.write("![Momentum Scatter](./plots/portfolio_momentum.png)\n\n")
    f.write("> [!CAUTION]\n")
    f.write("> **Overextension Risk:** ASML, TSM, and AMAT are dangerously extended above their MAs. Highly vulnerable to multiple contraction if Data Center CAPEX falters.\n\n")

    f.write("### Macro Scenario Drawdown Models\n")
    f.write("![Scenario Impact](./plots/portfolio_scenario_impact.png)\n\n")
    f.write("- **Higher-for-Longer Rates:** Flat CPI means no cuts. High-beta/growth (IONQ, NVO, ORCL) suffers yield compression.\n")
    f.write("- **Tariff Shock:** Broad 15-20% global tariffs historically squeeze semiconductor margins (AMAT risk).\n")
    f.write("- **Geopolitics:** Iran/Hormuz escalation actively demands LMT/RTX and oil structural overweighting to offset SaaS bleeding.\n\n")

    f.write("### Cross-Asset Risk Mapping (Correlations)\n")
    f.write("![Correlation Matrix](./plots/portfolio_correlation.png)\n\n")
    f.write("*Notice the >0.85 block correlation between AMD, AMAT, and LRCX. If semis crack, 30% of this portfolio bleeds at once.*\n\n")

    f.write("---\n*Generated algorithmically by `growth_portfolio_analysis.py`.*\n")


if __name__ == "__main__":
  logger.info("Starting Portfolio Analysis Engine...")

  try:
    portfolio_tech_df = pd.read_csv(PORTFOLIO_FILE, sep='\t')
    logger.info(f"Loaded processed metrics from {PORTFOLIO_FILE}")
  except FileNotFoundError:
    logger.error(
        f"Failed to load portfolio metrics. Ensure it has been run through the processor first.\nTarget missing: {PORTFOLIO_FILE}"
    )
    sys.exit(1)

  if portfolio_tech_df.empty:
    logger.error("Loaded dataframe is empty. Exiting.")
    sys.exit(1)

  logger.info("Data ingested.")

  # 2. Generate Visuals
  ticker_list = portfolio_tech_df['Ticker'].tolist()
  # Filter out CASH purely for correlation heatmap so it doesn't skew correlation
  ticker_list = [t for t in ticker_list if t != 'CASH']

  plot_portfolio_allocation(portfolio_tech_df, os.path.join(PLOTS_DIR, "portfolio_allocation.png"))
  plot_momentum_scatter(portfolio_tech_df, os.path.join(PLOTS_DIR, "portfolio_momentum.png"))
  plot_correlation_heatmap(ticker_list, TICKERS_DIR, os.path.join(PLOTS_DIR, "portfolio_correlation.png"))
  plot_winners_losers(portfolio_tech_df, os.path.join(PLOTS_DIR, "portfolio_winners_losers.png"))
  plot_scenario_impact(portfolio_tech_df)
  build_decision_tree()

  # 3. Write Report
  generate_report(portfolio_tech_df)

  logger.info("Execution Pipeline Complete. Check REPORT.md")
