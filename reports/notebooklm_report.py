#!/usr/bin/env python3
import argparse
import asyncio
from datetime import datetime
import glob
import logging
import os
import sys
from typing import List, Optional

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_fetcher import MarketFetcher
from notebooklm_client import MarketNewsClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- NOTEBOOKLM PROMPT CONSTANTS ---

PROMPT_DAILY = """You are a sophisticated hedge fund analyst powered by NotebookLM. Write a highly actionable, data-driven daily market intelligence report synthesizing the uploaded qualitative news and quantitative price action.

STRUCTURE THE REPORT EXACTLY AS FOLLOWS:
## Top AI Thematic Insights
Write a highly structured, authoritative executive summary grouping exactly the major themes and catalysts present in the data. Highlight geopolitical shifts, tech leaps, and energy constraints. Use clean markdown (### headers for major themes and - bullet points for supporting evidence).

## Quantitative Market Action & Specific Equities
Explicitly correlate the top stock winners/losers from the Price Action Summary with the exact qualitative news events driving them. Quantify your points.
You MUST format this section using clean Markdown Tables (one for Top Winners, one for Top Losers) with columns for Ticker, Performance, and News Catalyst explaining the move.

CRITICAL FORMATTING RULES:
1. Be extremely concise. Avoid wordiness.
2. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""

PROMPT_WEEKLY = """You are a macroeconomic analyst powered by NotebookLM. Write a highly actionable, data-driven weekly synthesis report for the week of {start_date} to {end_date}.

STRUCTURE THE REPORT EXACTLY AS FOLLOWS:
## Top AI Thematic Insights
Write a highly structured, authoritative executive summary grouping exactly the major macroeconomic themes, tech sector momentum pivots, and geopolitical risks that defined this week. Use clean markdown (### headers for major themes and - bullet points for supporting evidence).

## Quantitative Market Action & Specific Equities
Extract and rigorously analyze the top quantitative winners and losers provided in the Price Action Summary and explain their performance strictly using the uploaded qualitative news. Rely heavily on the numbers and cite the companies directly.
You MUST format this section using clean Markdown Tables (one for Top Winners, one for Top Losers) with columns for Ticker, Performance, and News Catalyst explaining the move.

CRITICAL FORMATTING RULES:
1. Be extremely concise. Avoid wordiness. Ensure the tone is institutional.
2. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""

PROMPT_MONTHLY = """You are a macroeconomic analyst powered by NotebookLM. Write a highly detailed, data-driven monthly synthesis report for {month_year}.

STRUCTURE THE REPORT EXACTLY AS FOLLOWS:
## Top AI Thematic Insights
Write a highly structured, authoritative executive summary grouping exactly the major themes and catalysts that defined this month. Highlight major shifts or trends and assign explicit probabilities or data-backed weightings where possible. Break the broader market narrative and key events down chronologically into a Week-by-Week timeline here if necessary.

## Quantitative Market Action & Specific Equities
Extract and rigorously analyze the top quantitative winners and losers provided in the Price Action Summary. Correlate those specific stock returns ($, +%) to the uploaded qualitative news.
You MUST format this section using clean Markdown Tables (one for Top Winners, one for Top Losers) with columns for Ticker, Performance, and News Catalyst explaining the move.

CRITICAL FORMATTING RULES:
1. Be extremely concise. Avoid wordiness. Use terse bullet points and numerical tables.
2. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""

PROMPT_YEARLY = """You are a macroeconomic analyst powered by NotebookLM. Write a highly detailed, data-driven yearly synthesis report for {year}.
Extract and rigorously analyze the top quantitative winners and losers provided in the Price Action Summary. Correlate those specific stock returns ($, +%) to the uploaded qualitative news.
Break the overarching market narrative and structural economic shifts down chronologically into a Quarter-by-Quarter timeline (Q1-Q4).
CRITICAL FORMATTING RULES:
1. Be extremely concise. Avoid wordiness. Use terse bullet points and numerical tables.
2. Highlight major defining moments of the year and provide concrete, numerical evidence.
3. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""

PROMPT_PORTFOLIO = """You are an elite portfolio manager powered by NotebookLM. Review the provided tabular text data representing my exact stock holdings, their recent performance metrics, and the latest news context.

Write a HIGHLY CONCISE tactical summary of the portfolio's health.
Identify the top 3 most overextended names that might be ripe for profit-taking, and the top 3 deepest value traps or long-term plays.
Identify any key portfolio concentrations.
Crucially, provide actionable, single-account specific trade advice (buy/sell/hold) for this week and near term.

CRITICAL INSTRUCTIONS:
1. MAX 50 words per paragraph. NO FLUFl. NO EXPLANATIONS. Use numbers and terse bullet points.
2. Ensure strict logical consistency between your advice and the provided data tables. If a stock is up 200%, do not call it a value play.
3. You MUST include a numbered '## References' appendix at the very end. Map every single inline citation (e.g., [1]) to the exact Source Headline and URL provided. Format as Markdown."""

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

      if start_date:
        df = df[df['ParsedDate'] >= start_date]
      if end_date:
        df = df[df['ParsedDate'] <= end_date]

      if df.empty or len(df) < 2:
        continue

      df = df.sort_values('ParsedDate')
      start_price = df.iloc[0]['Close']
      end_price = df.iloc[-1]['Close']
      high_price = df['High'].max(
      ) if 'High' in df.columns else df['Close'].max()
      low_price = df['Low'].min() if 'Low' in df.columns else df['Close'].min()

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

  blob += "\nTop Losers:\n"
  for _, row in res_df.tail(15).iterrows():
    blob += f"- {row['Ticker']}: {row['Return_Pct']:.2f}% (Start: ${row['Start_Price']:.2f}, End: ${row['End_Price']:.2f}, Low: ${row['Low']:.2f})\n"

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

    # 2. Recursively find and upload new PDF files
    logger.info("Syncing local reports to NotebookLM...")
    for root, _, files in os.walk(dir_path):
      for file in files:
        if file.endswith('.pdf'):
          # NotebookLM source titles from files perfectly match the basename
          if file in seen_titles:
            logger.info("Skipping already uploaded file: %s", file)
            continue

          file_path = os.path.join(root, file)
          await db.upload_file(file_path)
          logger.info("Successfully uploaded %s", file_path)
          seen_titles.add(file)


async def generate_report(market_data_dir: str,
                          mode: str,
                          start_date_str: Optional[str] = None,
                          end_date_str: Optional[str] = None,
                          dir_path: Optional[str] = None):
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
      date_str = date_obj.strftime("%m-%d")
    else:
      date_str = datetime.now().strftime("%m-%d")

    project_name = "Market Feed"
    report_filename = f"{date_str}_DAILY_REPORT.md"
    prompt = PROMPT_DAILY
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
    report_filename = f"{start_date.strftime('%Y-%m')}_MONTHLY_REPORT.md"
    prompt = PROMPT_MONTHLY.format(month_year=start_date.strftime('%B %Y'))
  elif mode == 'yearly':
    if not start_date_str or not end_date_str:
      raise ValueError("Yearly mode requires start_date and end_date.")
    start_date = pd.to_datetime(start_date_str).tz_localize(None)
    end_date = pd.to_datetime(end_date_str).tz_localize(None)
    project_name = "Market Feed"
    report_filename = f"{start_date.strftime('%Y')}_YEARLY_REPORT.md"
    prompt = PROMPT_YEARLY.format(year=start_date.strftime('%Y'))
  elif mode == 'portfolio':
    if not dir_path or not os.path.exists(dir_path):
      raise ValueError(
          "Portfolio mode requires a valid --dir pointing to the markdown report."
      )
    project_name = "Market Pipeline: Portfolio Synthesis (Temp)"
    report_filename = os.path.basename(dir_path)
    prompt = PROMPT_PORTFOLIO
  elif mode == 'earnings':
    if not dir_path or not os.path.exists(dir_path):
      raise ValueError(
          "Earnings mode requires a valid --dir pointing to the markdown report."
      )
    project_name = "Market Pipeline: Earnings Synthesis (Temp)"
    report_filename = os.path.basename(dir_path)
    prompt = PROMPT_EARNINGS
  elif mode == 'feed_upload':
    project_name = "Market Feed"
    report_filename = None  # No direct prompt/file output, just archiving raw data
    prompt = None
  else:
    raise ValueError(f"Unknown mode: {mode}")

  logger.info(
      f"Initializing NotebookLM Client: Mode={mode}, Project={project_name}")

  try:
    async with MarketNewsClient(project_name=project_name) as db:
      await db.connect()

      # Clear sources only for one-off portfolio/earnings to ensure freshness
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
      elif mode == 'feed_upload':
        target_date_obj = pd.to_datetime(start_date_str).tz_localize(
            None) if start_date_str else datetime.now()
        feed_title = f"{target_date_obj.strftime('%Y-%m-%d')} Daily Market Feed"

        # Deduplication check
        if db.client and hasattr(db.client, 'sources'):
          logger.info("Checking if '%s' is already in Market Feed...",
                      feed_title)
          existing_sources = await db.client.sources.list(db.notebook_id)
          for src in existing_sources:
            if getattr(src, 'title', '') == feed_title:
              logger.info("Source '%s' already exists. Skipping.", feed_title)
              return

        from reports.report_utils import build_daily_news_digest
        text_blob, combined_df = build_daily_news_digest(
            market_data_dir, target_date=target_date_obj)

        if not text_blob or combined_df.empty:
          logger.warning(
              f"No recent news found for {target_date_obj.strftime('%Y-%m-%d')}. Aborting."
          )
          return

        urls_to_fetch = []
        if 'URL' in combined_df.columns:
          # Sort to get the most relevant
          if 'Sentiment' in combined_df.columns:
            top_df = combined_df.sort_values(by='Sentiment', ascending=False)
          else:
            top_df = combined_df

          urls_to_fetch = [
              str(row.get('URL', '')).strip()
              for _, row in top_df.iterrows()
              if str(row.get('URL', '')).strip().startswith('http')
          ][:15]

        # Deep Fetch
        logger.info(f"Scraping deep context for {len(urls_to_fetch)} URLs...")
        for idx, url in enumerate(urls_to_fetch):
          text = await MarketFetcher.fetch_article_text(url, max_paragraphs=30)
          if text and len(text) > 100:
            full_texts.append(f"FULL ARTICLE CONTEXT {idx+1}:\n{text[:3000]}\n")

        final_market_feed_doc = f"# {feed_title}\n\n{text_blob}\n\n"
        if full_texts:
          final_market_feed_doc += "====== COMBINED DEEP CONTEXT ======\n\n" + "\n\n".join(
              full_texts)
        await db.upload_news_text(final_market_feed_doc, title=feed_title)
        logger.info("✅ Uploaded single aggregated file: %s", feed_title)
        return

      # Final Prompting
      if prompt:

        # Build and Upload Quantitative summary for periodic reports
        if mode in ['daily', 'weekly', 'monthly', 'yearly']:
          target_start = pd.to_datetime(start_date_str).tz_localize(
              None) if start_date_str else None
          target_end = pd.to_datetime(end_date_str).tz_localize(
              None) if end_date_str else None

          if mode == 'daily':
            # Set target_start to 7 days ago if daily to give weekly momentum
            target_end = target_end or pd.Timestamp.now().tz_localize(None)
            target_start = target_start or (target_end - pd.Timedelta(days=7))

          quant_summary = build_price_analysis_blob(market_data_dir,
                                                    target_start, target_end)

          # Deduplicate Quantitative Summary
          summary_title = "Quantitative Price Action Summary"
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
          logger.info(
              "Scanning for recent historical reports to inject as context...")
          reports_dir = os.path.dirname(os.path.abspath(__file__))
          recent_reports = []
          for report_file in os.listdir(reports_dir):
            if report_file.endswith(
                ".md") and report_file != "PORTFOLIO_REPORT.md":
              # Only grab recent reports (last 7 days approx based on file mtime)
              filepath = os.path.join(reports_dir, report_file)
              if os.path.isfile(filepath):
                mtime = os.path.getmtime(filepath)
                if (datetime.now().timestamp() - mtime) < (7 * 86400):
                  recent_reports.append((filepath, report_file))

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
          output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     report_filename or "report.md")

        # For portfolios: prepend the AI summary to the existing file
        if mode in ['portfolio', 'earnings']:
          with open(output_path, 'r') as f:
            original_content = f.read()
          with open(output_path, "w") as f:
            new_content = (
                f"{original_content}\n\n---\n\n# AI Tactical Summary\n"
                f"> **[View Primary Active Reports Archive directly in NotebookLM](https://notebooklm.google.com/notebook/8bc24a30-b417-4a6e-acdf-1b5588c04bae)**\n\n"
                f"{report_content}")
            f.write(new_content)
        else:
          # Write the generated report content directly
          with open(output_path, "w") as f:
            f.write(
                f"# Market Intelligence Report\n*(Generated via NotebookLM Integration on {datetime.now().strftime('%Y-%m-%d')})*\n"
                "> **[View Primary Active Reports Archive directly in NotebookLM](https://notebooklm.google.com/notebook/8bc24a30-b417-4a6e-acdf-1b5588c04bae)**\n\n"
            )
            f.write(report_content)

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


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="NotebookLM Report Generator")
  parser.add_argument("--mode",
                      choices=[
                          'daily', 'weekly', 'monthly', 'yearly', 'feed_upload',
                          'report_upload', 'upload', 'list', 'list_sources',
                          'portfolio', 'earnings'
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
