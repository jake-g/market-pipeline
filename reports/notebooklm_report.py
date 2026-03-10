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
Group the insights into two sections: 'Macro & Themes' and 'Specific Equities'.
CRITICAL FORMATTING RULES:
1. Be extremely concise. Avoid wordiness. Use terse bullet points and numerical tables.
2. Explicitly correlate the top stock winners/losers from the Price Action Summary with the exact qualitative news events driving them. Quantify your points.
3. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""

PROMPT_WEEKLY = """You are a macroeconomic analyst powered by NotebookLM. Write a highly actionable, data-driven weekly synthesis report for the week of {start_date} to {end_date}.
Extract and rigorously analyze the top quantitative winners and losers provided in the Price Action Summary and explain their performance strictly using the uploaded qualitative news.
Summarize the broad market narrative, key macro events, tech sector momentum, and energy/geopolitical risks.
CRITICAL FORMATTING RULES:
1. Be extremely concise. Avoid wordiness. Use terse bullet points and numerical tables.
2. Rely heavily on the numbers, cite the companies directly, and ensure the tone is institutional.
3. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""

PROMPT_MONTHLY = """You are a macroeconomic analyst powered by NotebookLM. Write a highly detailed, data-driven monthly synthesis report for {month_year}.
Extract and rigorously analyze the top quantitative winners and losers provided in the Price Action Summary. Correlate those specific stock returns ($, +%) to the uploaded qualitative news.
Break the broader market narrative and key events down chronologically into a Week-by-Week timeline.
CRITICAL FORMATTING RULES:
1. Be extremely concise. Avoid wordiness. Use terse bullet points and numerical tables.
2. Highlight major shifts or trends that characterized this month and assign explicit probabilities or data-backed weightings where possible.
3. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""

PROMPT_YEARLY = """You are a macroeconomic analyst powered by NotebookLM. Write a highly detailed, data-driven yearly synthesis report for {year}.
Extract and rigorously analyze the top quantitative winners and losers provided in the Price Action Summary. Correlate those specific stock returns ($, +%) to the uploaded qualitative news.
Break the overarching market narrative and structural economic shifts down chronologically into a Quarter-by-Quarter timeline (Q1-Q4).
CRITICAL FORMATTING RULES:
1. Be extremely concise. Avoid wordiness. Use terse bullet points and numerical tables.
2. Highlight major defining moments of the year and provide concrete, numerical evidence.
3. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""

PROMPT_PORTFOLIO = """You are an elite portfolio manager powered by NotebookLM. Review the provided tabular text data representing my exact stock holdings, their recent performance metrics (Unrealized P/L, RSI, Dist_to_200MA), and the latest news context.
Write a concise, high-level tactical summary of the portfolio's health.
Identify the top 3 most overextended names (highest RSI/Dist_to_200MA) that might be ripe for profit-taking, and the top 3 deepest value traps or long-term plays (lowest RSI/deepest drawdowns).
Identify any key portfolio concentrations (e.g., too heavily weighted in semiconductors or highly leveraged names).
Crucially, provide actionable, single-account specific trade advice (buy/sell/hold) for this week and near term. Base your trades strictly on the numerical data, structural macro vectors, and immediate catalysts.
Ensure high accuracy, sensibility, and consistency between your text recommendations and the tabular quantitative data provided.
CRITICAL FORMATTING RULES:
1. Be extremely concise. Avoid wordiness. Use terse bullet points and numerical tables.
2. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown."""


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
    from reports.report_utils import upload_directory_to_notebooklm
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
    from reports.report_utils import upload_directory_to_notebooklm
    logger.info(f"Uploading directory to NotebookLM: {dir_path}")
    await upload_directory_to_notebooklm(dir_path)
    return

  if mode == 'daily':
    if start_date_str:
      date_obj = pd.to_datetime(start_date_str).tz_localize(None)
      date_str = date_obj.strftime("%m-%d")
      target_date = date_obj
    else:
      date_str = datetime.now().strftime("%m-%d")
      target_date = None

    project_name = "Market Pipeline: Daily Data (Temp)"
    report_filename = f"{date_str}_DAILY_REPORT.md"
    prompt = PROMPT_DAILY
  elif mode == 'weekly':
    if not start_date_str or not end_date_str:
      raise ValueError("Weekly mode requires start_date and end_date.")
    start_date = pd.to_datetime(start_date_str).tz_localize(None)
    end_date = pd.to_datetime(end_date_str).tz_localize(None)
    project_name = "Market Pipeline: Historical Data (Temp)"
    report_filename = f"{end_date.strftime('%m-%d')}_WEEKLY_REPORT.md"
    prompt = PROMPT_WEEKLY.format(start_date=start_date_str,
                                  end_date=end_date_str)
  elif mode == 'monthly':
    if not start_date_str or not end_date_str:
      raise ValueError("Monthly mode requires start_date and end_date.")
    start_date = pd.to_datetime(start_date_str).tz_localize(None)
    end_date = pd.to_datetime(end_date_str).tz_localize(None)
    project_name = "Market Pipeline: Historical Data (Temp)"
    report_filename = f"{start_date.strftime('%Y-%m')}_MONTHLY_REPORT.md"
    prompt = PROMPT_MONTHLY.format(month_year=start_date.strftime('%B %Y'))
  elif mode == 'yearly':
    if not start_date_str or not end_date_str:
      raise ValueError("Yearly mode requires start_date and end_date.")
    start_date = pd.to_datetime(start_date_str).tz_localize(None)
    end_date = pd.to_datetime(end_date_str).tz_localize(None)
    project_name = "Market Pipeline: Historical Data (Temp)"
    report_filename = f"{start_date.strftime('%Y')}_YEARLY_REPORT.md"
    prompt = PROMPT_YEARLY.format(year=start_date.strftime('%Y'))
  elif mode == 'portfolio':
    if not dir_path or not os.path.exists(dir_path):
      raise ValueError(
          "Portfolio mode requires a valid --dir pointing to the markdown report."
      )
    project_name = "Market Reports"  # Re-use the clean project space for this heavy RAG
    report_filename = os.path.basename(dir_path)
    prompt = PROMPT_PORTFOLIO
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

      # Clear sources only for daily, weekly, monthly, yearly, and portfolio to ensure freshness
      if mode in ['daily', 'weekly', 'monthly', 'yearly', 'portfolio']:
        await db.clear_sources()

      # Gather TSVs
      all_tsvs = glob.glob(os.path.join(market_data_dir, '**', 'news.tsv'),
                           recursive=True)
      weekly_news_dfs = []
      unique_urls = set()

      for tsv in all_tsvs:
        try:
          df = pd.read_csv(tsv, sep='\t')

          if mode in ['daily', 'weekly', 'monthly', 'yearly'
                     ] and 'Date' in df.columns:
            # Filter logic for daily/weekly/monthly/yearly
            df['ParsedDate'] = pd.to_datetime(df['Date'],
                                              utc=True).dt.tz_localize(None)
            if mode == 'daily':
              # Basically everything in the TSV should be recent, but we can just use the unified digest logic
              pass
            elif mode in ['weekly', 'monthly', 'yearly']:
              mask = (df['ParsedDate'] >= start_date) & (df['ParsedDate']
                                                         <= end_date)
              filtered = df.loc[mask]
              if not filtered.empty:
                weekly_news_dfs.append(filtered)

          elif mode == 'feed_upload' and 'URL' in df.columns:
            if 'Date' in df.columns:
              df['ParsedDate'] = pd.to_datetime(df['Date'],
                                                utc=True).dt.tz_localize(None)
              df = df[df['ParsedDate'] > last_sync_date]

            for url in df['URL'].dropna():
              url_str = str(url).strip()
              if url_str.startswith('http'):
                unique_urls.add(url_str)
        except Exception as e:
          logger.warning(f"Error reading {tsv}: {e}")

      text_blob = ""
      full_texts = []

      # Processing Logic
      if mode == 'daily':
        # Leverage existing report utils logic for the perfect daily aggregate
        from reports.report_utils import build_daily_news_digest

        target_date_obj = pd.to_datetime(start_date_str).tz_localize(
            None) if start_date_str else None
        text_blob, combined_df = build_daily_news_digest(
            market_data_dir, target_date=target_date_obj)
        if not text_blob or combined_df.empty:
          logger.warning("No recent news found. Aborting.")
          return

        if 'Sentiment' in combined_df.columns:
          top_df = combined_df.sort_values(by='Sentiment', ascending=False)
        else:
          top_df = combined_df

        urls_to_fetch = []
        if 'URL' in top_df.columns:
          urls_to_fetch = [
              str(row.get('URL', '')).strip()
              for _, row in top_df.iterrows()
              if str(row.get('URL', '')).strip().startswith('http')
          ][:10]

      elif mode in ['weekly', 'monthly', 'yearly']:
        if not weekly_news_dfs:
          logger.warning(f"No news found for this {mode} period.")
          return
        combined_df = pd.concat(
            weekly_news_dfs,
            ignore_index=True).drop_duplicates(subset=['Headline'])
        if 'Sentiment' in combined_df.columns:
          combined_df = combined_df.sort_values(by='Sentiment', ascending=False)

        text_blob = f"{mode.upper()} DIGEST:\n\n"
        for _, row in combined_df.iterrows():
          text_blob += f"{row.get('Date')}: {row.get('Headline')} - {row.get('Summary', '')}\n"
        urls_to_fetch = []
        if 'URL' in combined_df.columns:
          urls_to_fetch = [
              str(u).strip()
              for u in combined_df['URL'].dropna()
              if str(u).strip().startswith('http')
          ][:30 if mode == 'weekly' else 60]

      elif mode == 'feed_upload':
        urls_to_fetch = list(unique_urls)[:30]  # Batch limit

      # Deep Fetch
      logger.info(f"Scraping deep context for {len(urls_to_fetch)} URLs...")
      for idx, url in enumerate(urls_to_fetch):
        text = await MarketFetcher.fetch_article_text(
            url, max_paragraphs=45 if mode != 'weekly' else 30)
        if text and len(text) > 100:
          if mode == 'feed_upload':
            title = f"Data Feed - {url.split('/')[-1][:30]}"
            await db.upload_news_text(text, title=title)
          else:
            full_texts.append(f"FULL ARTICLE CONTEXT {idx+1}:\n{text[:3000]}\n")

      # Final Prompting
      if mode in ['daily', 'weekly', 'monthly', 'yearly', 'portfolio'
                 ] and prompt:

        # Build and Upload Quantitative summary
        if mode == 'portfolio' and dir_path:
          # For portfolio mode, just upload the exact markdown tabular document we are targeting
          with open(dir_path, 'r') as f:
            await db.upload_news_text(f.read(),
                                      title="Raw Portfolio Data Tables")
        else:
          target_start = pd.to_datetime(start_date_str).tz_localize(
              None) if start_date_str else None
          target_end = pd.to_datetime(end_date_str).tz_localize(
              None) if end_date_str else None
        if mode != 'portfolio':
          if mode == 'daily':
            # Set target_start to 7 days ago if daily to give weekly momentum
            target_end = target_end or pd.Timestamp.now().tz_localize(None)
            target_start = target_start or (target_end - pd.Timedelta(days=7))

          quant_summary = build_price_analysis_blob(market_data_dir,
                                                    target_start, target_end)
          if quant_summary:
            await db.upload_news_text(
                quant_summary, title=f"Quantitative Price Action Summary")

        if mode != 'portfolio':
          await db.upload_news_text(text_blob,
                                    title=f"{mode.capitalize()} Digest")
          if full_texts:
            combined_deep_context = "====== COMBINED DEEP CONTEXT ======\n\n" + "\n\n".join(
                full_texts)
            await db.upload_news_text(combined_deep_context,
                                      title="Combined Deep Context")

        logger.info(f"Requesting LLM Synthesis for {mode}...")
        report_content = await db.ask_question(prompt)

        if mode == 'portfolio' and dir_path:
          output_path: str = dir_path
        else:
          output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     report_filename or "report.md")

        # For portfolios: prepend the AI summary to the existing file
        if mode == 'portfolio':
          with open(output_path, 'r') as f:
            original_content = f.read()
          with open(output_path, 'w') as f:
            f.write(
                f"# AI Tactical Summary\n> **[View Primary Active Reports Archive directly in NotebookLM](https://notebooklm.google.com/notebook/8bc24a30-b417-4a6e-acdf-1b5588c04bae)**\n\n{report_content}\n\n---\n\n{original_content}"
            )

        else:
          # Look for a fresh AI Thematic Summary
          thematic_content = ""
          ai_themes_path = os.path.join(
              os.path.dirname(os.path.abspath(__file__)), "rendered",
              "AI_THEMES.md")
          if os.path.exists(ai_themes_path):
            mtime = os.path.getmtime(ai_themes_path)
            if (datetime.now().timestamp() - mtime) < 86400:  # Within 24h
              with open(ai_themes_path, "r") as tf:
                # Drop the auto-generated Title from the summary so we can embed it
                theme_text = tf.read().replace("# AI Thematic Insight Report",
                                               "## Top AI Thematic Insights")
                thematic_content = f"{theme_text}\n\n---\n\n## Quantitative Portfolio & Market Action\n\n"
                logger.info(
                    "Successfully embedded AI_THEMES.md into the final report.")

          with open(output_path, "w") as f:
            f.write(
                f"# Market Intelligence Report\n*(Generated via NotebookLM Integration on {datetime.now().strftime('%Y-%m-%d')})*\n"
                "> **[View Primary Active Reports Archive directly in NotebookLM](https://notebooklm.google.com/notebook/8bc24a30-b417-4a6e-acdf-1b5588c04bae)**\n\n"
            )
            if thematic_content:
              f.write(thematic_content)

            f.write(report_content)

        # Automatically compile the Markdown into a PDF with embedded charts
        from reports.report_utils import render_markdown_to_pdf
        pdf_path = render_markdown_to_pdf(output_path)

        # Upload the beautiful PDF to our primary database, not the raw markdown
        logger.info(f"☁️ Uploading final PDF report to NotebookLM: {pdf_path}")
        await db.upload_file(pdf_path)

        logger.info(f"✅ Saved MD report to {output_path}")
        logger.info(f"✅ Rendered and Uploaded PDF report to {pdf_path}")

        # Clean up temporary generation projects
        if mode in ['daily', 'weekly', 'monthly', 'yearly']:
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
    if mode in ['daily', 'weekly', 'monthly', 'yearly'] and 'db' in locals():
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
                          'portfolio'
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
