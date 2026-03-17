# pylint: disable=duplicate-code
import asyncio
import os
import sys

import graphviz
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(PROJECT_ROOT)

MARKET_DATA_DIR = os.path.join(PROJECT_ROOT, "market_data")
REPORT_DIR = os.path.dirname(__file__)
PLOTS_DIR = os.path.join(REPORT_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

from market_fetcher import MarketFetcher
from reports.notebooklm_client import MarketNewsClient
from reports.report_utils import format_recent_news_markdown
from reports.report_utils import generate_rsi_dist200_scatter
from reports.report_utils import get_intrinsic_value_metrics
from reports.report_utils import get_technical_indicators
from reports.report_utils import render_markdown_to_pdf
from reports.report_utils import setup_decision_tree_aesthetics
from reports.report_utils import setup_plot_aesthetics

TICKERS = ["STM", "TTDKY", "TXN", "AVAV", "CVX", "XYL"]


def pre_fetch_data():
  print("Pre-fetching latest market data for the Strategy Ecosystem...")
  fetcher = MarketFetcher(cache_dir=os.path.join(MARKET_DATA_DIR, ".cache"))
  fetcher.update_prices(TICKERS)
  fetcher.update_news(TICKERS)
  fetcher.update_fundamentals(TICKERS)
  print("Data fetch complete.")


def generate_decision_tree():
  print("Generating Decision Tree...")
  try:
    dot = graphviz.Digraph(comment='Strategy Decision Tree')
    setup_decision_tree_aesthetics(dot)

    dot.node('A',
             'Start: Strategy Execution (Mar-Apr 2026)',
             fillcolor='lightblue')
    dot.node('B', 'Geopolitical Catalyst', fillcolor='lightgray')

    # Branch 1: Drone Component Enablers
    dot.node('C',
             'Attritable Mass Scaling\\n(Sting/LUCAS Demand)',
             fillcolor='lightyellow')
    dot.node('D',
             'Buy COTS Intel/Hardware\\n(STM, TTDKY, TXN)',
             fillcolor='lightgreen')
    dot.node('E',
             'Trim hardware on supply shocks\\nor extreme RSI (>70)',
             fillcolor='lightcoral')

    # Branch 2: Broad Iran / Hormuz Shock
    dot.node('F',
             'Energy/Logistics Disruption\\n(Hormuz Closure Risk)',
             fillcolor='lightyellow')
    dot.node('G',
             'Hold/Accumulate Energy Hedges\\n(CVX)',
             fillcolor='lightblue')
    dot.node('H',
             'Rotate to Water/Logistics if CVX > $170\\n(XYL)',
             fillcolor='lightgreen')

    dot.edges(['AB'])
    dot.edge('B', 'C', label=' "Liberty Ship" DoW Policy')
    dot.edge('B', 'F', label=' Regional Escalation > April')
    dot.edge('C', 'D', label=' US/Ukraine scale-up')
    dot.edge('D', 'E', label=' Semiconductor Shortages')
    dot.edge('F', 'G', label=' Oil approaches $100')
    dot.edge('G', 'H', label=' Take Profits on Energy Spike')

    out_path = os.path.join(PLOTS_DIR, "decision_tree")
    dot.render(out_path, format='png', cleanup=True)
  except Exception as e:
    print(f"Failed to generate decision tree: {e}")


def generate_relative_performance_plot():
  print("Generating Relative Performance Plot...")
  try:
    data = []
    for ticker in TICKERS:
      tech = get_technical_indicators(ticker,
                                      os.path.join(MARKET_DATA_DIR, "tickers"))
      ret = tech.get("Trailing_5D_Ret")
      if pd.notna(ret):
        data.append({"Ticker": ticker, "5-Day Return (%)": float(ret)})

    if not data:
      return

    df = pd.DataFrame(data)
    setup_plot_aesthetics()
    plt.figure(figsize=(10, 6))

    colors = ['red' if x < 0 else 'green' for x in df['5-Day Return (%)']]
    sns.barplot(x='Ticker',
                y='5-Day Return (%)',
                data=df,
                palette=colors,
                hue='Ticker',
                legend=False)

    plt.axhline(0, color='black', linewidth=1)
    plt.title("Ecosystem: 5-Day Relative Performance",
              fontweight='bold',
              fontsize=14)
    plt.ylabel("Return (%)")
    plt.xlabel("Ticker")
    plt.tight_layout()

    out_path = os.path.join(PLOTS_DIR, "5d_performance.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
  except Exception as e:
    print(f"Failed to generate performance plot: {e}")


def generate_technical_scatter_plot():
  print("Generating Technical Scatter Plot...")
  try:
    data = []
    for ticker in TICKERS:
      tech = get_technical_indicators(ticker,
                                      os.path.join(MARKET_DATA_DIR, "tickers"))
      data.append({
          "Ticker": ticker,
          "RSI": tech.get("RSI"),
          "Dist_to_200MA": tech.get("Dist_to_200MA"),
          "Current_Value": 5000
      })
    df = pd.DataFrame(data)
    out_path = os.path.join(PLOTS_DIR, "technical_scatter.png")
    generate_rsi_dist200_scatter(df, out_path)
  except Exception as e:
    print(f"Failed to generate technical scatter plot: {e}")


def generate_portfolio_allocation_plot(allocations):
  print("Generating Portfolio Allocation Plot...")
  try:
    labels = list(allocations.keys())
    sizes = [float(allocations[ticker].strip('%')) for ticker in labels]

    setup_plot_aesthetics()
    plt.figure(figsize=(8, 8))
    colors = sns.color_palette("viridis", len(labels))

    plt.pie(sizes,
            labels=labels,
            colors=colors,
            autopct='%1.1f%%',
            startangle=140,
            textprops={
                'fontsize': 12,
                'fontweight': 'bold',
                'color': 'black'
            })
    plt.title("Target Allocation",
              fontweight='bold',
              fontsize=14,
              color='black')

    out_path = os.path.join(PLOTS_DIR, "portfolio_allocation.png")
    plt.savefig(out_path,
                dpi=300,
                transparent=False,
                facecolor='white',
                bbox_inches='tight')
    plt.close()
  except Exception as e:
    print(f"Failed to generate allocation plot: {e}")


def load_deep_research():
  """Loads the original deep research document to append or extract."""
  research_path = os.path.join(REPORT_DIR, ".DEEP_RESEARCH.md")
  if os.path.exists(research_path):
    with open(research_path, "r") as f:
      return f.read().strip()
  return "> *.DEEP_RESEARCH.md not found.*"


async def query_notebooklm_synthesis():
  """Queries NotebookLM for synthesizing the strategy report dynamically."""
  print("Querying NotebookLM for synthesis...")
  try:
    async with MarketNewsClient(project_name="Market Reports") as client:
      await client.connect()
      prompt = f"""
      Review the recent portfolio reports (from March 11 and March 16), along with recent news reports.
      You MUST read the following Deep Research Context:

      {load_deep_research()}

      Synthesize the following:
      1. The Sting Drone Paradigm Shift: The deployment of $2,000 interceptors to destroy $30,000 Shahed drones.
         Focus on the COTS components (microcontrollers and IMUs like STM, TTDKY, TXN).
      2. The Broad Iran / Hormuz Shock: The escalating conflict driving the "$100 Oil Paradigm".

      Analyze the generated plots (RSI Scatter and Decision Tree - which show CVX is overextended and STM/TTDKY/TXN are potential deep value or momentum areas).
      Critique the proposed hybrid basket (STM, TTDKY, TXN, AVAV, CVX, XYL).
      Critique the recent news flow related to CVX's vulnerability in the Middle East and STM's current tech support trajectory.
      Produce a concise strategy synthesis on this.
      """
      res = await client.ask_question(prompt)
      return res
  except Exception as e:
    print(f"Failed to query NotebookLM: {e}")
    return "> *Failed to synthesize AI strategy. NotebookLM unavailable.*\\n\\n"


async def run_full_analysis():
  # pre_fetch_data() # Assume data is fetched for speed

  allocations = {
      "STM": "20%",
      "TTDKY": "20%",
      "TXN": "20%",
      "AVAV": "10%",
      "CVX": "15%",
      "XYL": "15%"
  }
  rationales = {
      "STM": "Key microcontrollers for logic processing in Sting drones.",
      "TTDKY": "Inertial Measurement Units (IMUs) critical for stability.",
      "TXN": "Silicon provider for volume logic boards.",
      "AVAV": "Direct exposure to tactical drone mass (LASSO program).",
      "CVX": "Geo-hedge against Hormuz blockade and oil supply risk.",
      "XYL": "Water infra and desal resilience against regional instability."
  }

  generate_decision_tree()
  generate_relative_performance_plot()
  generate_technical_scatter_plot()
  generate_portfolio_allocation_plot(allocations)

  # Await the query for AI synthesis directly
  if os.environ.get("DISABLE_NOTEBOOKLM_UPLOAD", "0") != "1":
    ai_insights_content = await query_notebooklm_synthesis()
  else:
    ai_insights_content = "> *NotebookLM upload disabled. Synthesis skipped.*"

  report_path = os.path.join(REPORT_DIR, "REPORT.md")

  print("Compiling Strategy Report...")
  md_lines = []

  md_lines.append(
      "# Strategy Report: Sting Drone & Broad Geopolitics (March 16)\n\n")

  md_lines.append("## 1. Parameters & Constraints\n")
  md_lines.append(
      "*   **Target Instruments:** Asymmetric warfare enablers (STM, TTDKY, TXN, AVAV) vs Macro Energy/Infrastructure Hedges (CVX, XYL).\n"
  )
  md_lines.append(
      "*   **Strategy:** Combine the $2k Sting Drone hardware logic with the $100 Oil Paradigm generated by Hormuz tensions.\n"
  )
  md_lines.append("*   **Timeline:** March - April 2026 execution window.\n\n")

  md_lines.append("---\n\n")

  md_lines.append("## 2. 🧭 Decision Architecture\n")
  md_lines.append(
      "*Flow: Scaling Attritable Mass -> Energy Hedge Rotation*\n\n")
  md_lines.append("![Decision Tree](./plots/decision_tree.png)\n\n")
  md_lines.append("### Logic Walkthrough\n")
  md_lines.append(
      "The overarching strategy bifurcates into hardware scaling (Left Branch) vs. macro hedging (Right Branch). \n\n"
  )
  md_lines.append(
      "**🟢 High Priority BUYS:** Components necessary to build mass quantities of the $2,000 Sting Drone (STM, TXN, TTDKY). These processors and inertial sensors are agnostic to which airframe prime wins the DoD contracts.\n\n"
  )
  md_lines.append(
      "**🔵 Strategic HOLDS:** CVX provides an essential macro hedge. The Strait of Hormuz conflict introduces a severe risk premium to global oil. If WTI eclipses $100 and CVX RSI goes critical, this will be rotated.\n\n"
  )
  md_lines.append(
      "**🟡 Conditional ROTATION:** If CVX peaks ($170+), we trim to capture the shock value, and rotate proceeds defensively into domestic Water Infrastructure (XYL) to play the secondary effects of MENA energy-grid deterioration.\n\n"
  )

  md_lines.append("---\n\n")

  md_lines.append("## 3. Quantitative Portfolio Setup\n")
  md_lines.append(
      "*Caption: Target percentage allocation focusing strictly on mission-critical components vs. broad energy hedges.*\n\n"
  )

  screener_results = []
  for ticker in TICKERS:
    tech = get_technical_indicators(ticker,
                                    os.path.join(MARKET_DATA_DIR, "tickers"))
    val = get_intrinsic_value_metrics(ticker,
                                      os.path.join(MARKET_DATA_DIR, "tickers"))

    weight_str = allocations.get(ticker, "0%")
    price = tech.get("Close")

    if not (isinstance(price, (int, float)) and pd.notna(price) and price > 0):
      price = "N/A"

    row = {
        "Asset": f"**{ticker}**",
        "Weight": weight_str,
        "Role & Rationale": rationales.get(ticker, "N/A"),
        "Current Price": f"${price:.2f}" if isinstance(price, float) else "N/A",
        "RSI": tech.get("RSI", "N/A"),
        "Dist 200MA": f"{tech.get('Dist_to_200MA', 'N/A')}%",
        "Discount": f"{val.get('Discount_to_Intrinsic_Value_Pct', 'N/A')}%"
    }
    screener_results.append(row)

  df_screener = pd.DataFrame(screener_results)
  md_lines.append(df_screener.to_markdown(index=False) + "\n\n")
  md_lines.append(
      "![Portfolio Allocation](./plots/portfolio_allocation.png)\n\n")

  md_lines.append("## 4. 🚨 Execution Zones & Momentum (RSI vs Trend)\n")
  md_lines.append("![5D Performance](./plots/5d_performance.png)\n\n")
  md_lines.append("![RSI vs Trend](./plots/technical_scatter.png)\n\n")

  md_lines.append("---\n\n")

  try:
    from datetime import datetime
    news_md = format_recent_news_markdown(
        topics={"geopolitics": "Macro Geopolitics"},
        market_data_dir=MARKET_DATA_DIR,
        tickers=TICKERS,
        max_items=15,
        target_date=datetime.now())
    if news_md:
      md_lines.append("\\n## Recent News Context\\n\\n")
      md_lines.append(news_md)
      md_lines.append("\\n\\n")
  except Exception as e:
    print(f"Failed to append news: {e}")

  md_lines.append("---\\n\\n")

  md_lines.append("## 5. Future Updates & Reflection\\n")
  md_lines.append(
      "> *Use this section to revisit the original thesis and log actual outcomes against predictions.*\\n\\n"
  )
  md_lines.append("### 1-Week Review (Target: March 23, 2026)\\n")
  md_lines.append(
      "- **Actual Execution:** [Did STM/TXN dip below RSI 40? Did CVX run up past 75 RSI?]\\n"
  )
  md_lines.append(
      "- **Thesis Check:** [Is the Strait of Hormuz conflict still intact? Did CVX reach target sell zones?]\\n\\n"
  )
  md_lines.append("### 1-Month Review (Target: April 16, 2026)\\n")
  md_lines.append(
      "- **Portfolio Performance:** [Insert basket return % vs SPY baseline]\\n"
  )
  md_lines.append(
      "- **Strategic Adjustments:** [What needs to be re-weighted based on new intelligence?]\\n\\n"
  )

  if ai_insights_content:
    md_lines.append(ai_insights_content.strip() + "\\n\\n")

  md_lines.append("---\\n\\n")
  md_lines.append("## 7. Extracted Sources & Deep Research References\\n\\n")
  md_lines.append(load_deep_research())
  md_lines.append("\\n")

  with open(report_path, "w") as f:
    f.write("".join(md_lines))
  print(f"Analysis complete. Report saved to {report_path}")

  print("Rendering PDF...")
  try:
    render_markdown_to_pdf(report_path)
    print("✅ PDF rendered successfully!")
  except Exception as e:
    print(f"❌ PDF rendering failed: {e}")


if __name__ == "__main__":
  asyncio.run(run_full_analysis())
