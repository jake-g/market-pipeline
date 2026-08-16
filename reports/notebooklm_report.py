#!/usr/bin/env python3
import argparse
import asyncio
from datetime import datetime
from datetime import timedelta
import glob
import logging
import os
import sys
from typing import List, Optional

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_fetcher import MarketFetcher
from reports.notebooklm_client import MarketNewsClient
from reports.report_utils import clean_md

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- NOTEBOOKLM PROMPT CONSTANTS ---

PROMPT_DAILY = """You are a sophisticated hedge fund analyst powered by NotebookLM. Write a highly actionable, detailed, and data-driven daily market intelligence report for {date}.

PRIORITIZE content from the source titled "{date} Daily Market Feed" as the absolute foundation for this report. Today's qualitative news feeds and quantitative price changes are the most important elements. Use historical context (previous reports) ONLY for continuity and tracking continuous narrative trends, DO NOT summarize them or let them drown out today's data.

STRUCTURE THE REPORT EXACTLY AS FOLLOWS:
## Top AI Thematic Insights
Write a highly structured, authoritative executive summary grouping exactly the major themes and catalysts present in TODAY'S data. Integrate context from previous reports *only* to explain the evolution of these themes. Explain the *why* behind today's moves. Include a brief, sharp **Expert Forward Projection** analyzing where these trends are likely headed in the near term. Use clean markdown (### headers for major themes and - bullet points for supporting evidence). Provide 3-4 distinct paragraphs/bullet blocks of intense insight.

## Quantitative Market Action & Specific Equities
Explicitly correlate the top stock winners/losers from TODAY'S Price Action Summary with the exact qualitative news events driving them. Focus on the 1-day change. Quantify your points and elaborate on the specific details of the catalyst (e.g., earnings beats with actual numbers, product launches, guidance revisions).
You MUST format this section using clean Markdown Tables (one for Top Winners, one for Top Losers) with columns for Ticker, Performance, and Detailed News Catalyst explaining today's move.

CRITICAL FORMATTING RULES:
1. Be concise but highly insightful. Focus tightly on today's developments. Avoid generic fluff.
2. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""

PROMPT_WEEKLY = """You are a macroeconomic analyst powered by NotebookLM. Write a highly actionable, detailed, and data-driven weekly synthesis report for the week of {start_date} to {end_date}.

FOCUS with a "zoomed out" perspective. Emphasize high-level thematic shifts, sector momentum pivots, and aggregate weekly performance over single-day noise. Rely on continuous context to show the evolution of trends.

STRUCTURE THE REPORT EXACTLY AS FOLLOWS:
## Top AI Thematic Insights
Write a highly structured, deep-dive executive summary grouping exactly the major macroeconomic themes, tech sector momentum pivots, and geopolitical risks that defined this week. Synthesize the primary narrative arc of the week. Contextualize using context from preceding uploaded reports to show the evolution of topics. Provide robust, detailed analysis on *why* these trends matter. Include a dedicated **Expert Forward Projection** section forecasting what these catalysts mean for the weeks ahead. Use clean markdown (### headers for major themes and - bullet points for supporting evidence). Aim for thorough, high-conviction insights.

## Quantitative Market Action & Specific Equities
Extract and rigorously analyze the top quantitative winners and losers provided in the Price Action Summary for the week and explain their performance strictly using the uploaded qualitative news. Rely heavily on the numbers, cite the companies directly, and provide the specific narrative behind their aggregate week move (e.g., earnings beats or guidance).
You MUST format this section using clean Markdown Tables (one for Top Winners, one for Top Losers) with columns for Ticker, Performance, and Detailed News Catalyst explaining the move.

CRITICAL FORMATTING RULES:
1. Be sharp and institutional, but provide rich detail and zoomed-out context. Avoid generic fluff.
2. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""

PROMPT_MONTHLY = """You are a macroeconomic analyst powered by NotebookLM. Write a highly detailed, insightful, and data-driven monthly synthesis report for {month_year}.

FOCUS strictly on structural economic trends, monthly narrative arcs, and major macro pivots. Tell a unified story of the month, summarizing the aggregate narrative rather than a daily log of details.

STRUCTURE THE REPORT EXACTLY AS FOLLOWS:
## Top AI Thematic Insights
Write a highly structured, deeply analytical executive summary grouping exactly the major themes and catalysts that defined this month. Highlight structural shifts or trends, drawing benchmarks against previous uploaded continuous context tracking. Break the broader market narrative and key events down chronologically into a Week-by-Week timeline here. Conclude this section with an **Expert Forward Projection**, offering institutional-level forecasts for the coming months based on the data. Provide expansive context and tell the story of the month.

## Quantitative Market Action & Specific Equities
Extract and rigorously analyze the top quantitative winners and losers provided in the Price Action Summary for the month. Correlate those specific stock returns to the uploaded qualitative news. Dig into the specific earnings reports, upgrades, or macro events driving those tickers for the month.
You MUST format this section using clean Markdown Tables (one for Top Winners, one for Top Losers) with columns for Ticker, Performance, and Detailed News Catalyst explaining the move.

CRITICAL FORMATTING RULES:
1. Provide deep, institutional-grade insights. Be highly actionable but do not sacrifice detail for brevity. Avoid generic fluff. Use terse bullet points and numerical tables for structure, but write thick paragraphs for analysis.
2. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""

PROMPT_YEARLY = """You are a macroeconomic analyst powered by NotebookLM. Write a highly detailed, data-driven yearly synthesis report for {year}.

STRUCTURE THE REPORT EXACTLY AS FOLLOWS:

## Executive Summary: The Year in Review
Write a highly structured, authoritative executive summary grouping the major overarching themes, stock market performance, and catalysts that defined the year. Highlight major structural shifts or tech trends.

## Quarterly Chronology
Break the overarching market narrative and structural economic shifts down chronologically into a Quarter-by-Quarter timeline (Q1-Q4). Summarize the defining moments, market reactions, and major geopolitical/macro events for each distinct quarter.

## Quantitative Market Action & Specific Equities
Extract and rigorously analyze the top quantitative winners and losers provided in the Price Action Summary. Correlate those specific stock returns ($, +%) to events from the qualitative news text where applicable.
You MUST format this section using clean Markdown Tables (one for Top Winners, one for Top Losers) with columns for Ticker, Performance, and News Catalyst explaining the move.

CRITICAL FORMATTING RULES:
1. Be extremely actionable and data-driven. Avoid fluff and wordiness. Use terse bullet points and numerical tables.
2. Highlight major defining moments of the year and provide concrete, numerical evidence when available.
3. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""

PROMPT_YEARLY_PROSPECTIVE = """You are a macroeconomic analyst powered by NotebookLM. Write a highly detailed, data-driven prospective synthesis report for {year}.

STRUCTURE THE REPORT EXACTLY AS FOLLOWS:

## Executive Summary: Outlook for {year}
Write a highly structured, authoritative executive summary grouping the major overarching themes, stock market forecasts, and potential catalysts expected for the year. Highlight major structural shifts or tech trends anticipated by experts.

## Key Forecasts & Major Events
Summarize the defining predictions, market expectations, and major geopolitical/macro events to watch for over the next 12 months.

## Sectors to Watch & Predictive Scenarios
Highlight which sectors or specific fields (e.g., AI, Energy) are expected to overperform or underperform and provide the rationale.
You MUST format this section cleanly, focusing on actionable insights.

CRITICAL FORMATTING RULES:
1. Be extremely actionable and data-driven. Avoid fluff and wordiness. Use terse bullet points.
2. Highlight major anticipated moments of the year and provide concrete, numerical evidence when available.
3. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""

PROMPT_PORTFOLIO = """You are an elite portfolio manager powered by NotebookLM. Review the provided tabular text data representing my exact stock holdings, their recent performance metrics, and the latest news context to answer a basic question based on the portfolio report.

Provide actionable, single-account specific trade advice (Buy/Sell/Exchange) for the Active Trading Portfolios section, categorized by High, Medium, or Low priority.

PRIORITIZE analyzing the **Active Trading Portfolios** section. This is my short-term/tactical allocation where I deploy active liquidity buffers.

Write a concise tactical summary focusing heavily on the Active portfolio's health.
Identify the top 3 most overextended names (ripe for profit-taking) and the top 3 deepest value traps in the Active section.
Identify any key portfolio concentrations within the Active holdings.
Crucially, provide actionable, single-account specific trade advice (buy/sell/hold) for this week and near term regarding the Active positions.

CRITICAL INSTRUCTIONS:
1. MAX 50 words per paragraph. NO FLUFF. Use numbers and terse bullet points.
2. Ensure strict logical consistency between your advice and the provided data tables. If a stock is up 200%, do not call it a value play.
3. 🚫 DO NOT suggest Options, Puts, Calls, or Margin trading.
4. ⚖️ Suggest trades to either deploy known liquid reserve or sell to raise more liquidity.
5. 🧭 Explicitly call back to the provided decision trees. Agree or contradict the main report's branches based on your analysis.
6. Keep the output extremely concise and format it using valid Markdown headers. Include a numbered '## References' appendix mapping inline citations (e.g., [1]) to the exact Source Headline and URL provided."""

PROMPT_EARNINGS = """You are an elite equity research analyst powered by NotebookLM. Review the provided tabular data, historical price action, Implied Volatility (IV) crush metrics, and the latest news context for this specific earnings event.

Write a HIGHLY CONCISE, zoomed-out tactical and macro analysis focused strictly on this particular ticker and its surrounding industry context.

CRITICAL INSTRUCTIONS:
1. MAX 50 words per paragraph. NO FLUFF. Use numbers and terse bullet points.
2. Provide predictive scenarios based strictly on the provided quantitative data (historical gap fades, post-earnings drift) and support them with qualitative catalysts from the news.
3. Contrast this ticker's earnings narrative with broader macroeconomic or sector-wide trends mentioned in the news to provide deeper, zoomed-out insights. Focus heavily on price trends and historical data. Do NOT mention random portfolio allocation or other tickers unless directly used to contrast the primary ticker's performance or ecosystem.
4. You MUST include a numbered '## References' appendix at the very end. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""


def build_price_analysis_blob(market_data_dir: str,
                              start_date: Optional[datetime],
                              end_date: Optional[datetime]) -> str:
  """Iterates over ticker price TSVs to calculate return profiles across the bounded date range."""
  tickers_dir = os.path.join(market_data_dir, 'tickers')
  if not os.path.exists(tickers_dir):
    return ""

  results = []
  for ticker_path in glob.glob(os.path.join(tickers_dir, '*')):
    if not os.path.isdir(ticker_path):
      continue
    ticker = os.path.basename(ticker_path)
    prices_file = os.path.join(ticker_path, 'prices.tsv')
    if not os.path.exists(prices_file):
      continue

    try:
      df = pd.read_csv(prices_file, sep='\t')
      if 'Date' not in df.columns or 'Close' not in df.columns:
        continue
      df['ParsedDate'] = pd.to_datetime(df['Date'],
                                        utc=True).dt.tz_localize(None)

      # Sort first to maintain chronological order in master list
      df = df.sort_values('ParsedDate')

      mask = pd.Series(True, index=df.index)
      if start_date:
        mask = mask & (df['ParsedDate'] >= start_date)
      if end_date:
        mask = mask & (df['ParsedDate'] <= end_date)

      df_range = df[mask]

      if df_range.empty:
        continue

      if len(df_range) == 1:
        idx = df_range.index[0]
        try:
          row_pos = df.index.get_loc(idx)
          # If we have a previous row in the fully sorted frame, use its close as the baseline
          if isinstance(row_pos, int) and row_pos > 0:
            start_price = df.iloc[row_pos - 1]['Close']
            end_price = df_range.iloc[0]['Close']
            high_price = df_range.iloc[0][
                'High'] if 'High' in df_range.columns else end_price
            low_price = df_range.iloc[0][
                'Low'] if 'Low' in df_range.columns else end_price
          else:
            continue
        except Exception:
          continue
      else:
        start_price = df_range.iloc[0]['Close']
        end_price = df_range.iloc[-1]['Close']
        high_price = df_range['High'].max(
        ) if 'High' in df_range.columns else df_range['Close'].max()
        low_price = df_range['Low'].min(
        ) if 'Low' in df_range.columns else df_range['Close'].min()

      return_pct = ((end_price - start_price) / start_price) * 100

      results.append({
          'Ticker': ticker,
          'Return_Pct': return_pct,
          'Start_Price': start_price,
          'End_Price': end_price,
          'High': high_price,
          'Low': low_price
      })
    except Exception:
      pass

  if not results:
    return ""

  res_df = pd.DataFrame(results).sort_values('Return_Pct', ascending=False)

  blob = "### QUANTITATIVE PRICE ACTION SUMMARY\n"
  blob += "Top Winners:\n"
  for _, row in res_df.head(15).iterrows():
    blob += f"- {row['Ticker']}: +{row['Return_Pct']:.2f}% (Start: ${row['Start_Price']:.2f}, End: ${row['End_Price']:.2f}, High: ${row['High']:.2f})\n"

  blob += "\n### FULL TICKER LOOKUP TABLE\n"
  try:
    from tabulate import tabulate
    display_df = res_df[['Ticker', 'Return_Pct', 'Start_Price',
                         'End_Price']].copy()
    display_df['Return_Pct'] = display_df['Return_Pct'].map(
        lambda x: f"{x:+.2f}%")
    display_df['Start_Price'] = display_df['Start_Price'].map(
        lambda x: f"${x:.2f}")
    display_df['End_Price'] = display_df['End_Price'].map(lambda x: f"${x:.2f}")
    table_text = tabulate(display_df.values.tolist(),
                          headers=['Ticker', 'Return %', 'Start', 'End'],
                          tablefmt='pipe')
    blob += table_text + "\n"
  except ImportError:
    # Fallback to simple format if tabulate is unavailable
    for _, row in res_df.iterrows():
      blob += f"- {row['Ticker']}: {row['Return_Pct']:+.2f}%\n"

  return blob


async def list_notebooklm_projects(filter_keyword: Optional[str] = None):
  """Lists NotebookLM projects and their sources, optionally filtering by project name."""
  logger.info("Connecting to NotebookLM to list projects...")
  try:
    async with MarketNewsClient(
        project_name="Market Pipeline: Daily Data") as db:
      if not db.client:
        raise ValueError("Client instantiation failed.")
      notebooks = await db.client.notebooks.list()

      print("\n=== NotebookLM Projects Overview ===")
      count = 0
      for nb in notebooks:
        if filter_keyword and filter_keyword.lower() not in nb.title.lower():
          continue
        count += 1
        sources = await db.client.sources.list(nb.id)
        print(f"\nProject Name: {nb.title}")
        print(f"Project ID:   {nb.id}")
        print(f"Source Count: {len(sources)}")
        if sources:
          print("Sources:")
          for src in sources:
            print(f"  - [{src.id}] {src.title}")
        print("-" * 50)

      print(f"\nTotal Exported Projects: {count}\n")

  except Exception as e:
    logger.error(f"Failed to list projects: {e}")


async def list_notebooklm_sources(target_project: str):
  """Prints a list of all uploaded sources for a specific project."""
  logging.basicConfig(level=logging.INFO)
  try:
    async with MarketNewsClient(project_name=target_project) as db:
      await db.connect()
      if not db.notebook_id:
        logger.error(f"Could not connect to or find project: {target_project}")
        return

      if db.client and hasattr(db.client, 'sources'):
        sources = await db.client.sources.list(db.notebook_id)
        if hasattr(sources, '__iter__'):
          source_list = list(sources)
          logger.info(f"\n{'='*50}\nProject: {target_project}\n{'='*50}")
          logger.info(f"Total Sources Found: {len(source_list)}\n")
          for idx, src in enumerate(source_list):
            title = getattr(src, 'title', 'Untitled Source')
            id_val = getattr(src, 'id', 'Unknown ID')
            logger.info(f"{idx+1}. {title} (ID: {id_val})")
        else:
          logger.error(
              f"Invalid sources structure returned for {target_project}")
      else:
        logger.error("Client or sources not available.")
  except Exception as e:
    logger.error(f"Error checking project {target_project}: {e}")


async def upload_directory_to_notebooklm(dir_path: str,
                                         project_name: str = "Market Reports"):
  """
    Uploads all relevant files from a generated report directory to NotebookLM.
    This creates an automated archive we can chat with later, with smart deduplication.
    """
  if not os.path.exists(dir_path):
    logger.error("Directory not found: %s", dir_path)
    return

  logger.info("Connecting to NotebookLM '%s' project...", project_name)
  async with MarketNewsClient(project_name=project_name) as db:
    await db.connect()

    seen_titles = set()

    # 1. Fetch current sources and deduplicate any existing stragglers in-place
    if db.client and hasattr(db.client, 'sources'):
      logger.info("Fetching and deduplicating existing sources in '%s'...",
                  project_name)
      existing_sources = await db.client.sources.list(db.notebook_id)
      for src in existing_sources:
        title = getattr(src, 'title', '')
        if not title:
          continue

        if title in seen_titles:
          logger.info("Deleting duplicate existing source: %s (ID: %s)", title,
                      src.id)
          try:
            await db.client.sources.delete(db.notebook_id, src.id)
          except Exception as e:
            logger.error("Failed to delete duplicate source %s: %s", title, e)
        else:
          seen_titles.add(title)

    # 2. Find all PDF files and sort by modification time (newest first)
    logger.info("Scanning local reports...")
    pdf_files = []
    for root, _, files in os.walk(dir_path):
      for file in files:
        if file.endswith('.pdf'):
          file_path = os.path.join(root, file)
          mtime = os.path.getmtime(file_path)
          pdf_files.append((file_path, file, mtime))

    # Sort descending by mtime (newest first)
    pdf_files.sort(key=lambda x: x[2], reverse=True)

    # Limit to latest 35 files to prevent thrashing under the 40 source limit
    limit = 35
    latest_pdfs = pdf_files[:limit]
    logger.info("Syncing latest %d reports to NotebookLM...", len(latest_pdfs))

    for file_path, file, _ in latest_pdfs:
      # NotebookLM source titles from files perfectly match the basename
      if file in seen_titles:
        logger.info("Skipping already uploaded file: %s", file)
        continue

      await db.upload_file(file_path)
      logger.info("Successfully uploaded %s", file_path)
      seen_titles.add(file)


# pylint: disable=too-many-return-statements
async def generate_report(market_data_dir: str,
                          mode: str,
                          start_date_str: Optional[str] = None,
                          end_date_str: Optional[str] = None,
                          dir_path: Optional[str] = None,
                          backfill_news: bool = True):
  """
    Unified entry point for NotebookLM report generation.
    Supports 'daily', 'weekly', 'monthly', 'yearly', 'feed_upload', and 'report_upload' modes.
    """
  urls_to_fetch: List[str] = []

  # State tracking for retrospective sweeps
  sync_file = os.path.join(
      os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs",
      ".notebooklm_last_sync.txt")
  last_sync_date = pd.to_datetime('2000-01-01').tz_localize(
      None)  # Default faraway past
  if mode == 'retrospective' and os.path.exists(sync_file):
    try:
      with open(sync_file, 'r') as f:
        date_str = f.read().strip()
        last_sync_date = pd.to_datetime(date_str).tz_localize(None)
        logger.info(f"Loaded retrospective sync state: {last_sync_date}")
    except Exception as e:
      logger.warning(f"Could not read sync state: {e}")

  if mode == 'report_upload':
    logger.info(f"Uploading rendered PDF reports to NotebookLM Market Reports")
    # Hardcode project name and target directory specifically for this mode
    rendered_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'rendered')
    if not os.path.exists(rendered_dir):
      logger.warning(f"Rendered directory does not exist: {rendered_dir}")
      return
    await upload_directory_to_notebooklm(rendered_dir, "Market Reports")
    return

  if mode == 'upload':
    if not dir_path:
      raise ValueError("Generic upload mode requires a --dir argument.")
    logger.info(f"Uploading directory to NotebookLM: {dir_path}")
    await upload_directory_to_notebooklm(dir_path)
    return

  if mode == 'daily':
    if start_date_str:
      date_obj = pd.to_datetime(start_date_str).tz_localize(None)
      date_m_d = date_obj.strftime("%m-%d")
      full_date_str = date_obj.strftime("%Y-%m-%d")
    else:
      date_obj = pd.Timestamp.now()
      date_m_d = date_obj.strftime("%m-%d")
      full_date_str = date_obj.strftime("%Y-%m-%d")

    project_name = "Market Feed"
    report_filename = f"{date_m_d}_DAILY_REPORT.md"
    prompt = PROMPT_DAILY.format(date=full_date_str)
    feed_title = f"{full_date_str} Daily Market Feed"  # Define feed_title for summary naming
  elif mode == 'weekly':
    if not start_date_str or not end_date_str:
      raise ValueError("Weekly mode requires start_date and end_date.")
    start_date = pd.to_datetime(start_date_str).tz_localize(None)
    end_date = pd.to_datetime(end_date_str).tz_localize(None)
    project_name = "Market Feed"
    report_filename = f"{end_date.strftime('%m-%d')}_WEEKLY_REPORT.md"
    prompt = PROMPT_WEEKLY.format(start_date=start_date_str,
                                  end_date=end_date_str)
  elif mode == 'monthly':
    if not start_date_str or not end_date_str:
      raise ValueError("Monthly mode requires start_date and end_date.")
    start_date = pd.to_datetime(start_date_str).tz_localize(None)
    end_date = pd.to_datetime(end_date_str).tz_localize(None)
    project_name = "Market Feed"
    report_filename = f"{start_date.strftime('%m')}_MONTHLY_REPORT.md"
    prompt = PROMPT_MONTHLY.format(month_year=start_date.strftime('%B %Y'))
  elif mode == 'yearly':
    if not start_date_str or not end_date_str:
      raise ValueError("Yearly mode requires start_date and end_date.")
    start_date = pd.to_datetime(start_date_str).tz_localize(None)
    end_date = pd.to_datetime(end_date_str).tz_localize(None)
    project_name = "Market Feed"
    report_filename = f"{start_date.strftime('%Y')}_YEARLY_REPORT.md"
    prompt = PROMPT_YEARLY.format(year=start_date.strftime('%Y'))
  elif mode == 'yearly_prospective':
    if not start_date_str or not end_date_str:
      raise ValueError(
          "Yearly prospective mode requires start_date and end_date.")
    start_date = pd.to_datetime(start_date_str).tz_localize(None)
    end_date = pd.to_datetime(end_date_str).tz_localize(None)
    project_name = "Market Feed"
    report_filename = f"{start_date.strftime('%Y')}_PROSPECTIVE_REPORT.md"
    prompt = PROMPT_YEARLY_PROSPECTIVE.format(year=start_date.strftime('%Y'))
  elif mode == 'portfolio':
    if not dir_path or not os.path.exists(dir_path):
      raise ValueError(
          "Portfolio mode requires a valid --dir pointing to the markdown report."
      )
    project_name = "Market Pipeline: Portfolio Synthesis"
    report_filename = os.path.basename(dir_path)
    prompt = PROMPT_PORTFOLIO
  elif mode == 'earnings':
    if not dir_path or not os.path.exists(dir_path):
      raise ValueError(
          "Earnings mode requires a valid --dir pointing to the markdown report."
      )
    project_name = "Market Pipeline: Earnings Synthesis"
    report_filename = os.path.basename(dir_path)
    prompt = PROMPT_EARNINGS
  elif mode == 'feed_upload':
    project_name = "Market Feed"
    report_filename = None  # No direct prompt/file output, just archiving raw data
    prompt = None
  elif mode == 'check_auth':
    project_name = "Market Reports"
    report_filename = None
    prompt = None
  else:
    raise ValueError(f"Unknown mode: {mode}")

  logger.info(
      f"Initializing NotebookLM Client: Mode={mode}, Project={project_name}")

  try:
    async with MarketNewsClient(project_name=project_name) as db:
      await db.connect()

      if mode == 'check_auth':
        logger.info("✅ NotebookLM Auth Valid")
        return

      # Clear sources only for one-off temp projects to ensure freshness
      if mode in ['portfolio', 'earnings']:
        await db.clear_sources()

      # Gather TSVs
      full_texts = []

      # Processing Logic
      if mode in ['portfolio', 'earnings']:
        if dir_path:
          # For portfolio mode, just upload the exact markdown tabular document we are targeting
          with open(dir_path, 'r') as f:
            await db.upload_news_text(
                f.read(), title=f"Raw {mode.capitalize()} Data Tables")
      elif mode in ['feed_upload', 'daily']:
        target_date_obj = pd.to_datetime(start_date_str).tz_localize(
            None) if start_date_str else datetime.now()
        feed_title = f"{target_date_obj.strftime('%Y-%m-%d')} Daily Market Feed"

        # Check if the feed already exists in the notebook
        feed_exists = False
        if db.client and hasattr(db.client, 'sources'):
          logger.info("Checking if '%s' is already in Market Feed...",
                      feed_title)
          existing_sources = await db.client.sources.list(db.notebook_id)
          for src in existing_sources:
            if getattr(src, 'title', '') == feed_title:
              logger.info("Source '%s' already exists.", feed_title)
              feed_exists = True
              break

        if not feed_exists:
          from reports.report_utils import build_daily_news_digest
          text_blob, combined_df = build_daily_news_digest(
              market_data_dir,
              target_date=target_date_obj,
              backfill_news=backfill_news)

          if not text_blob or combined_df.empty:
            logger.warning(
                f"No recent news found for {target_date_obj.strftime('%Y-%m-%d')}."
            )
          else:
            urls_to_fetch = []
            if 'URL' in combined_df.columns:
              # Sort to get the most relevant
              if 'Sentiment' in combined_df.columns:
                top_df = combined_df.sort_values(by='Sentiment',
                                                 ascending=False)
              else:
                top_df = combined_df

              urls_to_fetch = [
                  str(row.get('URL', '')).strip()
                  for _, row in top_df.iterrows()
                  if str(row.get('URL', '')).strip().startswith('http')
              ][:15]

            # Deep Fetch (Concurrent)
            logger.info(
                f"Scraping deep context for {len(urls_to_fetch)} URLs concurrently..."
            )
            tasks = [
                MarketFetcher.fetch_article_text(url, max_paragraphs=30)
                for url in urls_to_fetch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, text in enumerate(results):
              if isinstance(text, str) and text and len(text) > 100:
                full_texts.append(
                    f"FULL ARTICLE CONTEXT {idx+1}:\n{text[:3000]}\n")

            final_market_feed_doc = f"# {feed_title}\n\n{text_blob}\n\n"
            if full_texts:
              final_market_feed_doc += "====== COMBINED DEEP CONTEXT ======\n\n" + "\n\n".join(
                  full_texts)
            await db.upload_news_text(final_market_feed_doc, title=feed_title)
            logger.info("✅ Uploaded single aggregated file: %s", feed_title)

        if mode == 'feed_upload':
          return

      elif mode in ['weekly', 'monthly', 'yearly', 'yearly_prospective']:
        # Ensure strings are not None for type checker
        if not start_date_str or not end_date_str:
          raise ValueError(
              "start_date and end_date cannot be None for periodic reports")
        target_start = pd.to_datetime(start_date_str).tz_localize(None)
        target_end = pd.to_datetime(end_date_str).tz_localize(None)
        feed_title = f"{target_start.strftime('%Y-%m-%d')} to {target_end.strftime('%Y-%m-%d')} Market Synthesis"

        text_blob = None
        if mode == 'yearly_prospective':
          raw_year_file = os.path.join(
              os.path.dirname(os.path.abspath(__file__)), "news",
              f".{target_start.strftime('%Y')}_prospective_raw.md")
        else:
          raw_year_file = os.path.join(
              os.path.dirname(os.path.abspath(__file__)), "news",
              f".{target_start.strftime('%Y')}_raw.md")

        combined_df = None
        if mode in ['yearly', 'yearly_prospective'
                   ] and os.path.exists(raw_year_file):
          logger.info(f"Injecting deep raw context from: {raw_year_file}")
          with open(raw_year_file, "r") as f:
            text_blob = f.read()

          # Also append TSV data if it exists for the year (e.g. 2025+)
          if target_start.year >= 2025:
            from reports.report_utils import build_daily_news_digest
            tsv_blob, combined_df = build_daily_news_digest(
                market_data_dir,
                start_date=target_start,
                target_date=target_end,
                backfill_news=backfill_news)
            if tsv_blob:
              logger.info(
                  "Appending scraped TSV market data to deep history context")
              text_blob += f"\n\n--- ADDITIONAL SCRAPED MARKET DATA ({target_start.year}) ---\n\n{tsv_blob}\n"
        else:
          from reports.report_utils import build_daily_news_digest
          text_blob, combined_df = build_daily_news_digest(
              market_data_dir,
              start_date=target_start,
              target_date=target_end,
              backfill_news=backfill_news)

        if text_blob:
          # Deep Fetching for Periodic Reports
          urls_to_fetch = []
          full_texts = []
          if combined_df is not None and not combined_df.empty and 'URL' in combined_df.columns:
            # Sort to get the most relevant
            if 'Sentiment' in combined_df.columns:
              top_df = combined_df.sort_values(by='Sentiment', ascending=False)
            else:
              top_df = combined_df

            # Limit deep fetch differently based on period (e.g. Yearly shouldn't fetch 20 URLs, let's keep it to top 10-15)
            urls_to_fetch = [
                str(row.get('URL', '')).strip()
                for _, row in top_df.iterrows()
                if str(row.get('URL', '')).strip().startswith('http')
            ][:20]  # Expanded to 20 urls for richer deep context

            if urls_to_fetch:

              logger.info(
                  f"Scraping deep context for {len(urls_to_fetch)} top URLs...")
              for idx, url in enumerate(urls_to_fetch):
                text = await MarketFetcher.fetch_article_text(url,
                                                              max_paragraphs=30)
                if text and len(text) > 100:
                  full_texts.append(
                      f"FULL ARTICLE CONTEXT {idx+1}:\n{text[:3000]}\n")

          final_market_feed_doc = f"# {feed_title} News Digest\n\n{text_blob}\n\n"
          if full_texts:
            final_market_feed_doc += "====== COMBINED DEEP CONTEXT ======\n\n" + "\n\n".join(
                full_texts)

          if db.client and hasattr(db.client, 'sources'):
            logger.info(
                f"Deduplicating old '{feed_title}' in project '{project_name}'..."
            )
            try:
              sources = await db.client.sources.list(db.notebook_id)
              for src in sources:
                if getattr(src, 'title', '') == feed_title:
                  logger.info("Deleting old periodic feed source (ID: %s)",
                              src.id)
                  await db.client.sources.delete(db.notebook_id, src.id)
            except Exception as e:
              logger.warning(
                  f"Could not deduplicate old periodic feed source: {e}")
          await db.upload_news_text(final_market_feed_doc, title=feed_title)
          logger.info("✅ Uploaded bounded news text: %s", feed_title)

      # Final Prompting
      if prompt:

        # Build and Upload Quantitative summary for periodic reports
        if mode in [
            'daily', 'weekly', 'monthly', 'yearly', 'yearly_prospective'
        ]:
          # Use previously parsed target_start/target_end for weekly/monthly/yearly
          # Or parse anew if daily
          ts = pd.to_datetime(start_date_str).tz_localize(
              None).to_pydatetime() if start_date_str else None
          te = pd.to_datetime(end_date_str).tz_localize(
              None).to_pydatetime() if end_date_str else None

          if mode == 'daily':
            # For daily, we want 1-day return (comparison to previous close)
            if te is None:
              te = datetime.now()
            ts = te  # Single day; build_price_analysis_blob looks back 1 row

          quant_summary = build_price_analysis_blob(market_data_dir, ts, te)

          # Deduplicate Quantitative Summary
          summary_title = f"{feed_title} - Quantitative Price Action Summary" if 'feed_title' in locals(
          ) else f"Quantitative Price Action Summary {datetime.now().strftime('%Y-%m-%d')}"

          if db.client and hasattr(db.client, 'sources'):
            logger.info(
                f"Deduplicating old '{summary_title}' in project '{project_name}'..."
            )
            try:
              sources = await db.client.sources.list(db.notebook_id)
              for src in sources:
                if getattr(src, 'title', '') == summary_title:
                  logger.info("Deleting old summary (ID: %s)", src.id)
                  await db.client.sources.delete(db.notebook_id, src.id)
            except Exception as e:
              logger.warning(f"Could not deduplicate old summaries: {e}")

          if quant_summary:
            await db.upload_news_text(quant_summary, title=summary_title)

          # Inject recent historical reports to provide longitudinal context
          historical_context = ""

          if mode in ['weekly', 'monthly', 'yearly', 'yearly_prospective']:
            logger.info(
                f"Scanning for {mode} recursive sub-reports to inject as context..."
            )
            reports_dir = os.path.dirname(os.path.abspath(__file__))
            news_reports_dir = os.path.join(reports_dir, 'news')

            # Read from reports/news if it exists, otherwise fallback to reports root during transition
            scan_dirs = [news_reports_dir, reports_dir]
            recent_reports = []

            for scan_dir in scan_dirs:
              if not os.path.exists(scan_dir):
                continue
              for report_file in os.listdir(scan_dir):
                if report_file.endswith(
                    ".md") and report_file != "PORTFOLIO_REPORT.md":
                  filepath = os.path.join(scan_dir, report_file)
                  if os.path.isfile(filepath):
                    # For recursive injection, we check if the file falls within our bounds based on name or timeframe
                    # A naive approach: just inject files whose timestamp falls into the window
                    mtime_dt = datetime.fromtimestamp(
                        os.path.getmtime(filepath))

                    if target_start and target_end:
                      if target_start <= mtime_dt <= target_end:
                        recent_reports.append((filepath, report_file))
                      elif "DAILY" in report_file and mode == "weekly":
                        date_str = report_file.split("_")[0]  # MM-DD
                        year = target_start.year
                        try:
                          report_dt = datetime.strptime(f"{year}-{date_str}",
                                                        "%Y-%m-%d")
                          if target_start <= report_dt <= target_end:
                            recent_reports.append((filepath, report_file))
                        except:
                          pass
                      elif "WEEKLY" in report_file and mode == "monthly":
                        date_str = report_file.split("_")[0]  # MM-DD
                        year = target_start.year
                        try:
                          report_dt = datetime.strptime(f"{year}-{date_str}",
                                                        "%Y-%m-%d")
                          if target_start <= report_dt <= target_end:
                            recent_reports.append((filepath, report_file))
                        except:
                          pass
                      elif mode in ['yearly', 'yearly_prospective'
                                   ] and ("MONTHLY" in report_file or
                                          "WEEKLY" in report_file):
                        # Simple naive check: if the file contains the year or was modified in the year
                        if target_start.strftime(
                            "%Y"
                        ) in report_file or mtime_dt.year == target_start.year:
                          recent_reports.append((filepath, report_file))

            # Deduplicate just to be safe
            unique_reports = []
            seen_files = set()
            for rp in recent_reports:
              if rp[1] not in seen_files:
                seen_files.add(rp[1])
                unique_reports.append(rp)
            recent_reports = unique_reports

          else:
            logger.info(
                "Scanning for recent historical reports to inject as context..."
            )
            reports_dir = os.path.dirname(os.path.abspath(__file__))
            news_reports_dir = os.path.join(reports_dir, 'news')
            recent_reports = []

            scan_dirs = [news_reports_dir, reports_dir]
            for scan_dir in scan_dirs:
              if not os.path.exists(scan_dir):
                continue
              for report_file in os.listdir(scan_dir):
                if report_file.endswith(
                    ".md") and report_file != "PORTFOLIO_REPORT.md":
                  import re
                  filepath = os.path.join(scan_dir, report_file)
                  if os.path.isfile(filepath):
                    match = re.match(r"(\d{2}-\d{2})_", report_file)
                    if match:
                      file_date_str = match.group(1)
                      try:
                        target_year = te.year if te else datetime.now().year
                        file_date = datetime.strptime(
                            f"{target_year}-{file_date_str}", "%Y-%m-%d")
                        ref_date = te if te else datetime.now()
                        if file_date < ref_date and (ref_date -
                                                     file_date).days <= 7:
                          recent_reports.append((filepath, report_file))
                      except ValueError:
                        pass

          # Deduplicate before uploading
          if recent_reports:
            history_title = "Historical Context: Recent Periodic Reports"
            if db.client and hasattr(db.client, 'sources'):
              logger.info(
                  f"Deduplicating '{history_title}' in project '{project_name}'..."
              )
              try:
                sources = await db.client.sources.list(db.notebook_id)
                for src in sources:
                  if getattr(src, 'title', '') == history_title:
                    await db.client.sources.delete(db.notebook_id, src.id)
              except Exception as e:
                logger.warning(f"Could not deduplicate historical context: {e}")

            for filepath, report_file in recent_reports:
              with open(filepath, 'r') as f:
                historical_context += f"\n\n--- Content from {report_file} ---\n\n{f.read()}"

            if historical_context:
              await db.upload_news_text(historical_context, title=history_title)

        logger.info(f"Requesting LLM Synthesis for {mode}...")
        report_content = await db.ask_question(prompt)

        if mode in ['portfolio', 'earnings'] and dir_path:
          output_path: str = dir_path
        else:
          # Daily / Periodic Report output routing
          reports_dir = os.path.dirname(os.path.abspath(__file__))

          if mode in [
              'daily', 'weekly', 'monthly', 'yearly', 'yearly_prospective'
          ]:
            news_dir = os.path.join(reports_dir, 'news')
            os.makedirs(news_dir, exist_ok=True)
            output_path = os.path.join(news_dir, report_filename or "report.md")
          else:
            output_path = os.path.join(reports_dir, report_filename or
                                       "report.md")

        # For portfolios: prepend the AI summary to the existing file
        if mode in ['portfolio', 'earnings']:
          with open(output_path, 'r') as f:
            original_content = f.read()
          with open(output_path, "w") as f:
            new_content = (
                f"{original_content}\n\n---\n\n# AI Tactical Summary\n"
                f"> **[View Primary Active Reports Archive directly in NotebookLM](https://notebooklm.google.com/notebook/8bc24a30-b417-4a6e-acdf-1b5588c04bae)**\n\n"
                f"{report_content}")
            f.write(clean_md(new_content))
        else:
          # Write the generated report content directly
          raw_content = (
              f"# Market Intelligence Report\n*(Generated via NotebookLM "
              f"Integration on {datetime.now().strftime('%Y-%m-%d')})*\n"
              f"> **[View Primary Active Reports Archive directly in "
              f"NotebookLM](https://notebooklm.google.com/notebook/8bc24a30-b417-4a6e-acdf-1b5588c04bae)**\n\n"
              + report_content)
          with open(output_path, "w") as f:
            f.write(clean_md(raw_content))

        # Automatically compile the Markdown into a PDF with embedded charts
        from reports.report_utils import render_markdown_to_pdf
        pdf_path = render_markdown_to_pdf(output_path)

        logger.info(f"✅ Saved MD report to {output_path}")
        logger.info(f"✅ Rendered PDF report to {pdf_path}")
        logger.info(f"✅ Ready for bulk upload later.")

        # Clean up ONLY for portfolio and earnings (since they use temp projects)
        if mode in ['portfolio', 'earnings']:
          logger.info(f"Wiping temporary NotebookLM project: {project_name}...")
          await db.delete_project()

      elif mode == 'feed_upload':
        # Safely write the sync state after a successful run
        try:
          os.makedirs(os.path.dirname(sync_file), exist_ok=True)
          with open(sync_file, 'w') as f:
            f.write(datetime.now().isoformat())
        except Exception as e:
          logger.warning(f"Could not save sync state: {e}")
        logger.info("✅ Feed sync complete.")

  except Exception as e:
    logger.error(f"Failed to run via NotebookLM: {e}")

    # Try to safely clean up any stranded projects during a crash
    if mode in ['portfolio', 'earnings'] and 'db' in locals():
      try:
        logger.info(
            f"Attempting to wipe crashed NotebookLM project: {project_name}...")
        await db.delete_project()
      except:
        pass

    if "login" in str(e).lower() or "authentication" in str(e).lower():
      logger.error(
          "Please run `notebooklm login` from your terminal to authenticate.")
    sys.exit(1)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="NotebookLM Report Generator")
  parser.add_argument("--mode",
                      choices=[
                          'daily', 'weekly', 'monthly', 'yearly',
                          'yearly_prospective', 'feed_upload', 'report_upload',
                          'upload', 'list', 'list_sources', 'portfolio',
                          'earnings', 'check_auth'
                      ],
                      required=True,
                      help="Type of operation or 'list' to view projects")
  parser.add_argument(
      "--start", help="Start date (YYYY-MM-DD) for weekly/monthly/yearly mode")
  parser.add_argument(
      "--end", help="End date (YYYY-MM-DD) for weekly/monthly/yearly mode")
  parser.add_argument("--dir",
                      help="Directory path to upload for 'upload' mode")
  parser.add_argument("--filter-projects",
                      help="Keyword to filter projects in 'list' mode")
  parser.add_argument("--project",
                      default="Market Reports",
                      help="Target project name for 'list_sources' mode")

  args = parser.parse_args()

  if args.mode == 'list':
    asyncio.run(list_notebooklm_projects(args.filter_projects))
  elif args.mode == 'list_sources':
    asyncio.run(list_notebooklm_sources(args.project))
  else:
    root_market_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'market_data')
    asyncio.run(
        generate_report(root_market_data_dir, args.mode, args.start, args.end,
                        args.dir))
