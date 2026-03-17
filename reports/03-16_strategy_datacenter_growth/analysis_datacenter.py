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

TICKERS = [
    "NVDA", "TSM", "MU", "STRL", "PWR", "GEV", "VRT", "LIN", "CEG", "NUE"
]


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
    dot = graphviz.Digraph(comment='Datacenter Strategy Decision Tree')
    setup_decision_tree_aesthetics(dot)

    dot.node('A',
             'Start: Datacenter Strategy (Rest of 2026)',
             fillcolor='lightblue')
    dot.node('B', 'Constraint Identifier', fillcolor='lightgray')

    # Path 1: Power & Cooling
    dot.node('C',
             'Power/Grid Deficit\\n(3yr+ Interconnection Wait)',
             fillcolor='lightyellow')
    dot.node('D', 'Nuclear/SMRs Long-term\\n(CEG, PWR)', fillcolor='lightgreen')
    dot.node('E', 'Natural Gas Bridging\\n(GEV)', fillcolor='lightcoral')
    dot.node('F', 'Thermal/PFAS Bans', fillcolor='lightyellow')
    dot.node('G', 'Synthetic/Liquid Cooling\\n(VRT)', fillcolor='lightgreen')

    # Path 2: Geopolitics & Helium
    dot.node('H',
             'Helium/Hormuz Supply Shock\\n(Iran Conflict)',
             fillcolor='lightyellow')
    dot.node('I',
             'Secure Essential Chip Foundries\\n(TSM, NVDA)',
             fillcolor='lightgreen')
    dot.node('J',
             'Trim Overextended Semis\\n(MU) -> Buy Industrial Gas (LIN)',
             fillcolor='lightcoral')

    dot.edges(['AB'])
    dot.edge('B', 'C', label=' Grid Capacity Lags')
    dot.edge('C', 'D', label=' Hyperscaler 10yr Deals')
    dot.edge('C', 'E', label=' Immediate BYOP Needs')
    dot.edge('B', 'F', label=' 100kW+ Rack Density')
    dot.edge('F', 'G', label=' EU/EPA Bans')
    dot.edge('B', 'H', label=' Ras Laffan offline > 2mo')
    dot.edge('H', 'I', label=' HBM Priority')
    dot.edge('H', 'J', label=' Shortage Spikes VIX')

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
      deep_res = load_deep_research()
      deep_res_truncated = deep_res[:
                                    2500] + "\n...(truncated context due to length)" if len(
                                        deep_res) > 2500 else deep_res
      prompt = f"""
      Review ALL the recent strategy and portfolio reports you have uploaded in this project (specifically the March 16 Drone Geopolitics Strategy, the combined geopolitics report, and the recent Vanguard portfolio updates), along with recent news reports.
      You MUST read the following Deep Research Context regarding Datacenter Growth:

      {deep_res_truncated}

      Synthesize the following across the reports:
      1. Datacenter CapEx: The $600B capex supercycle scaling to $3T by 2030, and the inference inflection.
      2. Physical Constraints: Power grid deficits moving hyperscalers to Natural Gas (GEV) and SMRs (CEG),
         and thermal liquid cooling demand (VRT).
      3. Iran/Hormuz Supply Shock: The constraint on Helium and Bromine drastically impacting memory and logic
         semiconductor supply prioritizing TSM and squeezing others like MU.

      Analyze how this Datacenter strategy interacts with or hedges against the drone warfare and geopolitical risks outlined in the other reports.
      Critique the generated plots (RSI Scatter and Decision Tree - which show extensions in Semis versus Infrastructure).
      Critique the proposed Datacenter basket (NVDA, TSM, MU, STRL, PWR, GEV, VRT, LIN, CEG, NUE).
      Produce a concise strategy synthesis on this.
      """
      res = await client.ask_question(prompt)
      return res
  except Exception as e:
    print(f"Failed to query NotebookLM: {e}")
    return "> *Failed to synthesize AI strategy. NotebookLM unavailable.*\\n\\n"


async def run_full_analysis():
  pre_fetch_data()

  allocations = {
      "NVDA": "10%",
      "TSM": "15%",
      "MU": "5%",
      "LIN": "15%",
      "GEV": "10%",
      "STRL": "10%",
      "PWR": "15%",
      "VRT": "10%",
      "CEG": "5%",
      "NUE": "5%"
  }
  rationales = {
      "NVDA":
          "Core AI Hardware; must hold but take profits if extended.",
      "TSM":
          "Dominant Foundry; defensible given priority on critical gas supplies.",
      "MU":
          "AI Memory leader; highest risk to Helium/Geopolitical shocks. Tactical trim.",
      "LIN":
          "Industrial Gas pricing power during Helium supply squeeze.",
      "GEV":
          "Natural Gas bridge solution for AI data center baseload.",
      "STRL":
          "Heavy civil engineering and site-prep for megacampuses.",
      "PWR":
          "High-voltage grid integration for new sites.",
      "VRT":
          "Thermal management and modular liquid cooling transition.",
      "CEG":
          "Nuclear baseload / SMR infrastructure.",
      "NUE":
          "Low-carbon green steel structure requirements for hyperscalers."
  }

  generate_decision_tree()
  generate_relative_performance_plot()
  generate_technical_scatter_plot()

  # Await the query for AI synthesis directly
  if os.environ.get("DISABLE_NOTEBOOKLM_UPLOAD", "0") != "1":
    ai_insights_content = await query_notebooklm_synthesis()
  else:
    ai_insights_content = "> *NotebookLM upload disabled. Synthesis skipped.*"

  report_path = os.path.join(REPORT_DIR, "REPORT.md")

  print("Compiling Strategy Report...")
  md_lines = []

  md_lines.append(
      "# Strategy Report: Datacenter Growth & The 2026 AI Infrastructure Supercycle (March 16)\n\n"
  )

  md_lines.append("## 1. Parameters & Constraints\n")
  md_lines.append(
      "*   **Target Instruments:** AI Silicon core (NVDA, TSM, MU) vs. Physical Infrastructure & Hard Assets (STRL, PWR, VRT, GEV, LIN).\n"
  )
  md_lines.append(
      "*   **Strategy:** Pivot from pure software (the \"SaaSpocalypse\") to capitalizing on the constraints in the $600B capex supercycle (HALO investing).\n"
  )
  md_lines.append("*   **Timeline:** Rest of 2026 execution window.\n\n")

  md_lines.append("---\n\n")

  md_lines.append("## 2. 🧭 Decision Architecture\n")
  md_lines.append(
      "*Flow: Macro Catalyst -> Infrastructure Bottleneck -> Tactical Allocation*\n\n"
  )
  md_lines.append("![Decision Tree](./plots/decision_tree.png)\n\n")
  md_lines.append("### Logic Walkthrough & News Triggers To Track\n")
  md_lines.append(
      "The strategy revolves around reacting to distinct physical bottlenecks preventing scaling:\n\n"
  )
  md_lines.append(
      "**🟢 High Priority BUYS (Power & Site Prep):** The grid cannot support 100+ MW hyperscale campuses. Accumulate `GEV` as hyperscalers turn to 'Bring Your Own Power' natural gas turbines. Add `STRL` and `PWR` for necessary grid/civil engineering before servers even arrive.\n"
  )
  md_lines.append(
      "*   **News to Watch For:** Headlines regarding \"Interconnection Delays\", \"Behind-the-meter generation\", \"ERCOT deregulated off-take agreements\", or hyperscalers buying retired coal plants or directly contracting with turbine manufacturers.\n\n"
  )
  md_lines.append(
      "**🔵 Strategic HOLDS (Foundries):** Keep `TSM`. In the event of a severe Helium supply shock, Tier-1 foundries will protect high-margin AI chip output at all costs, starving logic/auto nodes.\n"
  )
  md_lines.append(
      "*   **News to Watch For:** Updates on \"Ras Laffan\" facility outages, delays in \"EUV Lithography\" timelines, or foundry statements regarding rationing of industrial gases to prioritize AI accelerator yields over consumer electronics.\n\n"
  )
  md_lines.append(
      "**🟡 Conditional ROTATION (Gas & Memory):** If Iran/Hormuz tensions lock up `Ras Laffan` helium deliveries, trim overextended memory names (`MU`, `IONQ`) and buy pure-play Industrial Gas conglomerates (`LIN`) exhibiting extreme pricing power.\n"
  )
  md_lines.append(
      "*   **News to Watch For:** \"Strait of Hormuz blockade\", spot price spikes in \"Bulk Helium\" or \"Bromine\", or earnings warnings from memory manufacturers (`MU`, `SK Hynix`) citing supply chain raw material constraints.\n\n"
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

  md_lines.append("## 4. 🚨 Execution Zones & Momentum (RSI vs Trend)\n")
  md_lines.append("![5D Performance](./plots/5d_performance.png)\n\n")
  md_lines.append("![RSI vs Trend](./plots/technical_scatter.png)\n\n")

  md_lines.append("---\n\n")

  try:
    from datetime import datetime
    news_md = format_recent_news_markdown(
        topics={"ai_infrastructure": "Datacenter Capex & Grid Issues"},
        market_data_dir=MARKET_DATA_DIR,
        tickers=TICKERS,
        max_items=15,
        target_date=datetime.now())
    if news_md:
      md_lines.append("## Recent News Context\n\n")
      md_lines.append(news_md)
      md_lines.append("\n\n")
  except Exception as e:
    print(f"Failed to append news: {e}")

  md_lines.append("---\n\n")

  md_lines.append("## 5. Future Updates & Reflection\n")
  md_lines.append(
      "> *Use this section to revisit the original thesis and log actual outcomes against predictions.*\n\n"
  )
  md_lines.append("### End of Q2 Review (Target: May 15, 2026)\n")
  md_lines.append(
      "- **Actual Execution:** [Did LIN break out? Were MU and Semis successfully trimmed at the top?]\n"
  )
  md_lines.append(
      "- **Thesis Check:** [Did Hyperscalers formally announce $10B+ off-grid natural gas / SMR generation deals?]\n\n"
  )

  md_lines.append("## 6. Extracted Sources & Deep Research References\n\n")
  md_lines.append("<details>\n<summary>Click to expand</summary>\n\n")
  md_lines.append(load_deep_research())
  md_lines.append("\n\n</details>\n\n")

  md_lines.append("---\n\n")

  md_lines.append("## 7. NotebookLM AI Strategic Review\n\n")
  if ai_insights_content and "Failed to synthesize" not in ai_insights_content:
    md_lines.append(ai_insights_content.strip() + "\n\n")
  else:
    md_lines.append(
        "> *NotebookLM synthesis generated an empty response or could not extract answer (this typically happens when the prompt exceeds its context). Please check manual terminal logs.*\n\n"
    )

  with open(report_path, "w") as f:
    f.write("".join(md_lines))
  print(f"Analysis complete. Report saved to {report_path}")

  # We skip rendering here if NotebookLM is disabled to let the user review first
  if os.environ.get("DISABLE_NOTEBOOKLM_UPLOAD", "0") != "1":
    print("Rendering PDF...")
    try:
      render_markdown_to_pdf(report_path)
      print("✅ PDF rendered successfully!")
    except Exception as e:
      print(f"❌ PDF rendering failed: {e}")


if __name__ == "__main__":
  asyncio.run(run_full_analysis())
