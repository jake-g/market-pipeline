#!/usr/bin/env python3
"""Interactive CLI tool to generate bespoke, AI-analyzed portfolio reports."""

import argparse
import asyncio
from datetime import datetime
import glob
import logging
import os
import re
import sys

from graphviz import Digraph

REPORTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(REPORTS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

import config
from notebooklm_client import MarketNewsClient
from reports import report_utils
# pylint: disable=import-error,no-name-in-module
from reports.report_utils import render_markdown_to_pdf

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_interactive_decision_tree(output_path: str, portfolio_name: str,
                                     user_query: str) -> str:
  """Generates a generic tactical decision tree based on the user's query context."""
  dot = Digraph(comment=f'Decision Tree for {portfolio_name}')
  report_utils.setup_decision_tree_aesthetics(dot)

  # Entry Point
  dot.node('A',
           f'Analyze:\n{portfolio_name}',
           shape='Mdiamond',
           style='filled',
           fillcolor='gold')

  # Generic Macro/Query Evaluation
  dot.node('B',
           f'Is context bullish based on query:\n"{user_query[:50]}..."?',
           shape='box',
           style='filled',
           fillcolor='lightgrey')
  dot.edge('A', 'B')

  # Bullish Path
  dot.node('C', 'HOLD Core', style='filled', fillcolor='lightblue')
  dot.node('D',
           'TRIM Overextended (RSI > 70)',
           style='filled',
           fillcolor='lightblue')
  dot.edge('B', 'C', label='Yes (Weight: 60%)')
  dot.edge('C', 'D', label='If Tech/Semi Heavy')

  # Bearish Path
  dot.node('E',
           'ADD to Deep Value (RSI < 30)',
           style='filled',
           fillcolor='lightblue')
  dot.node('F',
           'HEDGE with Broad Market / Defensives',
           style='filled',
           fillcolor='lightblue')
  dot.edge('B', 'E', label='No (Weight: 40%)')
  dot.edge('B', 'F', label='If Volatility spikes')

  dot.render(output_path, format='png', cleanup=True)
  return output_path + '.png'


async def generate_notebooklm_synthesis(tsv_path: str, user_query: str) -> str:
  """Sends the TSV data and user query to a temporary NotebookLM project for tactical synthesis."""
  logger.info("Initializing NotebookLM Synthesis...")

  import pandas as pd
  try:
    df = pd.read_csv(tsv_path, sep="\t")
    tickers = df['Ticker'].unique().tolist()
  except Exception as e:
    logger.error(f"Failed to read TSV for tickers: {e}")
    tickers = []

  with open(tsv_path, 'r') as f:
    tsv_content = f.read()

  # Read recent market news as raw string for context injection
  recent_news = ""
  try:
    with open(
        os.path.join(PROJECT_ROOT, "reports",
                     f"{datetime.now().strftime('%m-%d')}_DAILY_REPORT.md"),
        'r') as f:
      recent_news = f.read()[:2000]  # Grab top summary
  except FileNotFoundError:
    logger.warning("Could not find today's daily report for context injection.")

  ticker_context = ""
  if tickers:
    market_data_dir = os.path.join(PROJECT_ROOT, "market_data")
    ticker_context = report_utils.build_ticker_context_markdown(
        tickers, market_data_dir)

  prompt = f"""
  You are an elite portfolio manager powered by NotebookLM. Review the provided tabular text data representing my exact stock holdings and their current metrics.

  The user has requested a tactical review. If they provided a specific query, prioritize it. Otherwise, provide a comprehensive default portfolio health check.
  User Query: "{user_query if user_query else 'Provide a robust, data-driven default portfolio analysis.'}"

  Recent Macro Market Context:
  {recent_news}

  {ticker_context}

  Write a highly actionable, data-driven Markdown summary of the portfolio's health.
  1. Identify structural risks (sector concentrations, extreme RSI).
  2. Highlight the top 3 buy/sell/trim candidates based on the technicals (RSI/200MA distance) and the detailed news/intrinsic value context provided above.
  3. Provide concrete trade execution advice for the upcoming week based on the macro context.

  Format the response strictly in professional Markdown with clear headers, bullet points, and bold text for emphasis. Do not blindly repeat the tables.
  """

  # Push to a designated temporary interaction project
  project_name = "Market Pipeline: Interactive Queries (Temp)"

  async with MarketNewsClient(project_name=project_name) as client:
    await client.connect()
    try:
      await client.upload_news_text(
          text_content=tsv_content,
          title=f"Portfolio_Data_{os.path.basename(tsv_path)}")
      logger.info("Portfolio data uploaded. Generating synthesis...")

      response = await client.ask_question(prompt)
      logger.info("NotebookLM Synthesis Complete.")

      # Clean up temp project content entirely
      await client.delete_project()

      query_display = user_query if user_query else "Default Portfolio Health Check"
      return f"> **Custom Query Context:** *{query_display}*\n\n" + response
    except Exception as e:
      logger.error(f"NotebookLM Generation failed: {e}")
      return f"**NotebookLM Synthesis Failed:** {str(e)}\n\n_Reverting to manual analysis._"


def main():
  print("=" * 60)
  print("📈 Market Pipeline: Interactive Portfolio Builder 🤖")
  print("=" * 60)

  parser = argparse.ArgumentParser()
  parser.add_argument("--portfolio",
                      type=str,
                      help="Filename of the TSV to load")
  parser.add_argument("--query",
                      type=str,
                      default="",
                      help="Custom query for the AI")
  args = parser.parse_args()

  # 1. Discover Portfolios
  portfolios_dir = os.path.join(PROJECT_ROOT, "portfolios", "tsvs")
  if not os.path.exists(portfolios_dir):
    logger.error(f"Cannot find portfolios TSV directory at {portfolios_dir}")
    return

  tsv_files = sorted(glob.glob(os.path.join(portfolios_dir, "*.tsv")))
  if not tsv_files:
    logger.error("No TSV files found in portfolios/tsvs/")
    return

  selected_tsv_path = None

  if args.portfolio:
    for f in tsv_files:
      if os.path.basename(f) == args.portfolio:
        selected_tsv_path = f
        break

  if not selected_tsv_path:
    # Format choices for standard input
    print("\nAvailable Portfolios:")
    for i, f in enumerate(tsv_files):
      base_name = os.path.basename(f)
      display_name = base_name.replace(".tsv", "").replace("_", " ").title()
      if base_name.startswith("_combined"):
        display_name = f"🌟 {display_name} (AGGREGATE)"
      print(f"  [{i}]: {display_name}")

    # 2. Prompt User
    selected_index = input(
        "\nEnter the number of the portfolio to analyze: ").strip()
    if not selected_index.isdigit() or not (0 <= int(selected_index) <
                                            len(tsv_files)):
      print("Invalid selection. Aborted.")
      return
    selected_tsv_path = tsv_files[int(selected_index)]

  user_query = args.query
  if not user_query:
    user_query = input(
        "\nEnter a specific tactical focus or query for the AI (Press Enter for general overview):\n> "
    ).strip()

  # 3. Setup Report Structure
  base_filename = os.path.basename(selected_tsv_path)
  clean_name = re.sub(r'^\d{2}-\d{2}-\d{4}_', '',
                      base_filename).replace('.tsv', '').replace('__',
                                                                 '_').strip('_')
  human_name = clean_name.replace('_', ' ').title()
  date_str = datetime.now().strftime("%m-%d")

  report_dir_name = f"{date_str}_portfolio_{clean_name}"
  report_dir_path = os.path.join(REPORTS_DIR, report_dir_name)

  logger.info(f"Targeting report directory: {report_dir_path}")

  # 4. Ask NotebookLM for context
  print("\n🧠 Connecting to NotebookLM for tactical synthesis...")
  ai_synthesis = asyncio.run(
      generate_notebooklm_synthesis(selected_tsv_path, user_query))

  # 5. Build Markdown Template
  markdown_template = f"""
# Strategic Plan: {human_name}

## 💼 Portfolio Context
*   **User Query/Focus**: {user_query if user_query else 'General Health Check'}
*   **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

## 🤖 NotebookLM Tactical Synthesis
{ai_synthesis}

## ⚡ Tactical Decision Matrix
*Autogenerated mechanical logic tree based on query constraints.*
![Decision Tree]( plots/decision_tree.png )

## 📊 Visual Evidence
### Sector Exposure Weighting
![Exposure](plots/theme_exposure.png)
### Technical Constraints (MA Distance)
![MA Distance](plots/ma200_dist.png)
### Relative PnL by Theme
![PnL](plots/theme_pnl.png)

## 🗄️ Appendix: Portfolio Data
{{metrics_table}}
"""

  print(
      f"\n⚙️  Generating visualizations and compiling report for {human_name}..."
  )

  # 6. Execute report_utils pipeline

  def tree_wrapper(output_path):
    return create_interactive_decision_tree(output_path, human_name, user_query)

  report_utils.build_standard_portfolio_report(
      script_dir=report_dir_path,
      tsv_filename=base_filename,
      title_prefix=human_name,
      tree_func=tree_wrapper,
      markdown_template=markdown_template,
      market_analysis=""  # Handled directly by NotebookLM injection above
  )

  # 7. Auto-Render to PDF
  md_path = os.path.join(report_dir_path, "REPORT.md")
  pdf_dir = os.path.join(PROJECT_ROOT, "reports", "rendered")
  os.makedirs(pdf_dir, exist_ok=True)
  pdf_out = os.path.join(pdf_dir, f"{report_dir_name}.pdf")
  print(f"\n📄 Exporting PDF to {pdf_out}...")
  render_markdown_to_pdf(md_path, pdf_out)

  # 8. Auto-upload to NotebookLM
  print(f"\n☁️  Uploading PDF to NotebookLM 'Market Reports'...")

  async def upload_pdf():
    async with MarketNewsClient(project_name="Market Reports") as db:
      await db.connect()
      await db.upload_file(pdf_out)

  asyncio.run(upload_pdf())

  print("=" * 60)
  print(f"✅ Success! Report generated at: {md_path}")
  print(f"✅ Auto-rendered PDF at: {pdf_out}")
  print("=" * 60)


if __name__ == "__main__":
  main()
