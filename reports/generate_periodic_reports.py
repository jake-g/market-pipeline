#!/usr/bin/env python3
import argparse
import asyncio
import datetime
import logging
import os
import subprocess
import sys
from typing import Optional

from dateutil.relativedelta import relativedelta
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from notebooklm_client import MarketNewsClient
from reports.report_utils import get_recent_news

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "rendered")


def is_report_missing(filename: str) -> bool:
  """Checks if the corresponding .pdf or .md file is missing from the reports structure."""
  pdf_path = os.path.join(REPORTS_DIR, filename.replace('.md', '.pdf'))
  md_path = os.path.join(os.path.dirname(REPORTS_DIR), filename)
  return not (os.path.exists(pdf_path) and os.path.exists(md_path))


def generate_monthly_reports(start_year: int = 2026):
  """Generates missing monthly reports from the start year up to the LAST completed month."""
  today = datetime.date.today()
  # Only consider fully completed months
  first_day_of_current_month = datetime.date(today.year, today.month, 1)

  current = datetime.date(start_year, 1, 1)
  while current < first_day_of_current_month:
    next_month = current + relativedelta(months=1)
    last_day_of_month = next_month - relativedelta(days=1)

    filename = f"{current.strftime('%Y-%m')}_MONTHLY_REPORT.md"
    if is_report_missing(filename):
      logger.info(f"Missing Monthly Report found: {filename}")
      # Pre-generate the context-aware thematic summary
      generate_thematic_summary(end_date=last_day_of_month)

      cmd = [
          "python3", "reports/notebooklm_report.py", "--mode", "monthly",
          "--start",
          current.strftime("%Y-%m-%d"), "--end",
          last_day_of_month.strftime("%Y-%m-%d")
      ]
      logger.info(f"Executing: {' '.join(cmd)}")
      subprocess.run(cmd, check=True)
    else:
      logger.debug(f"Monthly report present: {filename}")

    current = next_month


def generate_weekly_reports(start_year: int = 2026, start_month: int = 3):
  """
  Generates missing weekly reports starting from the specified year/month
  up to the LAST completed week (Sunday to Saturday).
  """
  today = datetime.date.today()

  # Start at the provided year/month
  current_date = datetime.date(start_year, start_month, 1)

  # Find the first Sunday of this month to start the weekly boundary correctly
  while current_date.weekday() != 6:  # 6 is Sunday
    current_date += datetime.timedelta(days=1)

  # Iterate week by week until we hit the current week
  while True:
    week_end = current_date + datetime.timedelta(days=6)  # Saturday

    # If the end of this week is in the future, the week isn't "over" yet
    if week_end >= today:
      break

    filename = f"{week_end.strftime('%m-%d')}_WEEKLY_REPORT.md"
    if is_report_missing(filename):
      logger.info(f"Missing Weekly Report found: {filename}")
      # Pre-generate context-aware thematic summary
      generate_thematic_summary(end_date=week_end)

      cmd = [
          "--start",
          current_date.strftime("%Y-%m-%d"), "--end",
          week_end.strftime("%Y-%m-%d")
      ]
      logger.info(f"Executing: {' '.join(cmd)}")
      subprocess.run(cmd, check=True)
    else:
      logger.debug(f"Weekly report present: {filename}")

    current_date += datetime.timedelta(days=7)


def generate_daily_report():
  """Generates the standard daily report for the current day."""
  logger.info("Generating Daily Report...")
  generate_thematic_summary(end_date=datetime.date.today())

  cmd = ["python3", "reports/notebooklm_report.py", "--mode", "daily"]
  logger.info(f"Executing: {' '.join(cmd)}")
  subprocess.run(cmd, check=True)


async def async_generate_thematic_summary(output_dir: str,
                                          end_date: Optional[
                                              datetime.date] = None):
  """
  Collects recent news from all config topics, pushes them to a temporary NotebookLM project,
  asks for a structured thematic summary, and saves the output to a markdown file.
  """
  logger.info(
      f"Gathering news for thematic AI summary (bounded to {end_date or 'latest'})..."
  )

  # 1. Gather all news content by Topic
  topic_news_streams = {}
  for topic in config.NEWS_TOPICS:
    target_dt = pd.to_datetime(end_date).tz_localize(None) if end_date else None
    df = get_recent_news(topic,
                         config.MARKET_DATA_DIR,
                         limit=5,
                         end_date=target_dt)
    if not df.empty:
      text_dump = ""
      for _, row in df.iterrows():
        text_dump += f"HEADLINE: {row['Headline']}\nSUMMARY: {row.get('Summary', '')}\nDEEP TEXT: {row.get('Article_Text', '')}\n\n"

      if text_dump.strip():
        topic_news_streams[f"Topic: {topic}"] = text_dump

  if not topic_news_streams:
    logger.warning("No recent topical news found. Skipping thematic summary.")
    return None

  # 2. Upload to temporary NotebookLM project
  project_name = "TEMP: Topic Thematic Summarizer"
  logger.info(f"Connecting to NotebookLM [{project_name}]...")

  try:
    async with MarketNewsClient(project_name=project_name) as db:
      await db.connect()
      await db.clear_sources()  # Ensure clean slate

      # Combine all topics into a single upload to save API calls
      combined_text = ""
      for title, content in topic_news_streams.items():
        if content.strip():
          combined_text += f"====== {title} ======\n{content}\n"

      if combined_text:
        logger.info("Uploading combined topical news stream to NotebookLM...")
        await db.upload_news_text(text_content=combined_text,
                                  title="Aggregated Topical News")

      # 3. Generate Summary
      prompt = (
          "You are an expert macro-economic analyst and tech strategist. Review the provided topical news streams. "
          "Write a highly structured, authoritative executive summary grouping exactly the major themes and catalysts present in the data. "
          "Highlight geopolitical shifts, tech leaps, and energy constraints. "
          "Format strictly as clean markdown. Use ## headers for major themes and - bullet points for supporting evidence."
      )

      logger.info("Requesting thematic summary...")
      markdown_summary = await db.summarize_sources(custom_prompt=prompt)

      # Clean up the temporary project so it doesn't clutter the NotebookLM interface
      logger.info("Wiping temporary thematic NotebookLM project...")
      await db.delete_project()

      # 4. Save to disk
      if markdown_summary:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "AI_THEMES.md")
        # Prepend a header
        final_content = f"# AI Thematic Insight Report\n_Generated {datetime.datetime.now().strftime('%Y-%m-%d')}_\n\n{markdown_summary}"

        with open(output_path, "w") as f:
          f.write(final_content)

        logger.info(f"Thematic summary saved to {output_path}")
        return output_path

      logger.error("Failed to generate thematic summary from NotebookLM.")

  except Exception as e:
    logger.error(f"Error generating thematic summary: {e}")
    return None


def generate_thematic_summary(end_date: Optional[datetime.date] = None):
  """Generates the holistic AI thematic summary encompassing all topics."""
  output_directory = os.path.join(REPORTS_DIR)
  asyncio.run(async_generate_thematic_summary(output_directory, end_date))


def main():
  parser = argparse.ArgumentParser(
      description="Auto-generate missing historical NotebookLM reports.")
  parser.add_argument(
      "--monthly-start-year",
      type=int,
      default=2026,
      help="Year to begin checking for missing monthly reports.")
  parser.add_argument(
      "--weekly-start-month",
      type=str,
      default="2026-03",
      help="YYYY-MM to begin checking for missing weekly reports.")
  parser.add_argument("--dry-run",
                      action="store_true",
                      help="Print what would be generated without executing.")

  args = parser.parse_args()

  logger.info("==========================================")
  logger.info("Scanning for missing Historical NotebookLM Reports...")
  logger.info("==========================================\n")

  # 2. Backfill any missing historical scopes
  generate_monthly_reports(start_year=args.monthly_start_year)

  parts = args.weekly_start_month.split('-')
  generate_weekly_reports(start_year=int(parts[0]), start_month=int(parts[1]))

  # 3. Generate the daily rollout
  generate_daily_report()

  logger.info("\n✅ Periodic report generation sweep complete.")


if __name__ == "__main__":
  main()
