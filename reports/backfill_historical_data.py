#!/usr/bin/env python3
# pylint: disable=duplicate-code
import argparse
import asyncio
import datetime
import json
import logging
import os
import sys
import time
from typing import List
import urllib.parse

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from market_fetcher import MarketFetcher
from reports.report_utils import get_recent_news

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.dirname(os.path.abspath(__file__))
NEWS_DIR = os.path.join(REPORTS_DIR, "news")

# ==============================================================================
# DEEP MARKDOWN SCRAPING (DuckDuckGo + Wikipedia)
# ==============================================================================


def get_ddg_links(query: str, max_results: int = 3) -> List[str]:
  """Search DuckDuckGo HTML and extract direct target URLs."""
  url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
  try:
    res = cffi_requests.get(url, impersonate="chrome", timeout=15)
    soup = BeautifulSoup(res.text, "html.parser")
    links = []
    for a in soup.find_all("a", class_="result__snippet"):
      raw_href = a.get("href")
      if raw_href and "uddg=" in raw_href:
        target_url = urllib.parse.parse_qs(
            urllib.parse.urlparse(raw_href).query).get('uddg', [''])[0]
        if target_url and target_url.startswith(
            "http") and not target_url.endswith(".pdf"):
          links.append(target_url)
      if len(links) >= max_results:
        break
    return links
  except Exception as e:
    logger.error(f"Error fetching DDG links for '{query}': {e}")
    return []


def fetch_article_text(url: str) -> str:
  """Fetches an article and extracts its readable paragraph text."""
  try:
    res = cffi_requests.get(url, impersonate="chrome", timeout=15)
    soup = BeautifulSoup(res.text, "html.parser")
    paragraphs = soup.find_all("p")
    text = "\n\n".join([
        p.get_text().strip()
        for p in paragraphs
        if len(p.get_text().strip()) > 50
    ])
    return text[:15000]
  except Exception as e:
    logger.debug(f"Failed to extract text from {url}: {e}")
    return ""


def fetch_wikipedia_page(title: str) -> str:
  """Fetches the raw text content of a Wikipedia page using the MediaWiki API."""
  url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&titles={urllib.parse.quote(title)}&format=json"
  try:
    res = cffi_requests.get(url,
                            headers={'User-Agent': 'MarketPipelineBot/1.0'})
    data = res.json()
    pages = data.get("query", {}).get("pages", {})
    for page_id, page_data in pages.items():
      if page_id == "-1":
        return ""
      return page_data.get("extract", "")[:10000]
  except Exception as e:
    pass
  return ""


def backfill_deep_md(prospective: bool):
  """
    Scrapes expansive Web/Wiki text into hidden `.YYYY_raw.md` baseline files
    for NotebookLM to synthesize deep historic and prospective reports.
    """
  os.makedirs(NEWS_DIR, exist_ok=True)

  if prospective:
    search_queries = [
        "2026 stock market forecast predictions outlook",
        "2026 technology and artificial intelligence trends forecast",
        "2026 united states economy macro outlook predictions",
        "2026 geopolitical risks and macro events forecast"
    ]

    raw_md_path = os.path.join(NEWS_DIR, ".2026_prospective_raw.md")
    logger.info(f"\n==============================================")
    logger.info(f"Building prospective forecast context for 2026")
    logger.info(f"-> {raw_md_path}")
    logger.info(f"==============================================")

    with open(raw_md_path, "w") as f:
      f.write("# Prospective Forecast Context: 2026\n\n")
      f.write(
          "This file contains highly extensive raw scraped summaries of major 2026 macroeconomic forecasts, stock market outlooks, tech advancements, and predictions.\n\n"
      )

      for query in search_queries:
        logger.info(f"  [search] Querying: '{query}'")
        links = get_ddg_links(query, max_results=4)
        if links:
          for i, link in enumerate(links):
            logger.info(f"    -> Scraping: {link[:60]}...")
            article_text = fetch_article_text(link)
            if len(article_text) > 200:
              f.write(f"## Web Article: {query} (Source {i+1})\n")
              f.write(f"URL: {link}\n\n")
              f.write(f"{article_text}\n\n---\n\n")
            time.sleep(1)
        time.sleep(2)
    logger.info(f"  Saved extensive raw prospective data for 2026.")
    return

  # Deep historical
  wiki_templates = ["{year}_in_the_United_States"]

  search_queries = [
      "{year} stock market year in review",
      "{year} top technology and artificial intelligence news recap",
      "{year} united states economy overview",
      "{year} geopolitical and macro events recap"
  ]

  for year in range(2018, 2026):
    raw_md_path = os.path.join(NEWS_DIR, f".{year}_raw.md")
    logger.info(f"\n==============================================")
    logger.info(f"Building deep historical context for {year}")
    logger.info(f"-> {raw_md_path}")
    logger.info(f"==============================================")

    with open(raw_md_path, "w") as f:
      f.write(f"# Historical Raw Context: {year}\n\n")
      f.write(
          f"This file contains highly extensive raw scraped summaries of major {year} events, tech advancements, and economic/market news.\n\n"
      )

      for template in wiki_templates:
        title = template.format(year=year)
        logger.info(f"  [wiki] Fetching baseline: {title}")
        content = fetch_wikipedia_page(title)
        if content:
          f.write(f"## Wikipedia Baseline: {title.replace('_', ' ')}\n")
          f.write(f"{content}\n\n---\n\n")

      for query_template in search_queries:
        query = query_template.format(year=year)
        logger.info(f"  [search] Querying: '{query}'")
        links = get_ddg_links(query, max_results=3)
        if links:
          for i, link in enumerate(links):
            logger.info(f"    -> Scraping: {link[:60]}...")
            article_text = fetch_article_text(link)
            if len(article_text) > 200:
              f.write(f"## Web Article: {query} (Source {i+1})\n")
              f.write(f"URL: {link}\n\n")
              f.write(f"{article_text}\n\n---\n\n")
            time.sleep(1)
        time.sleep(2)
    logger.info(f"  Saved extensive raw data for {year}.")


# ==============================================================================
# TSV / DATABASE BACKFILL LOGIC (Google News RSS)
# ==============================================================================


async def backfill_tsv():
  """
    Backfills missing structured TSV rows by crawling historical news for broader topics.
    Useful for ensuring the internal data pipelines have row-level context for past years.
    """
  logger.info("Starting historical structured TSV backfill (2024-2025)...")
  fetcher = MarketFetcher(config.MARKET_DATA_DIR)

  for year in range(2024, 2026):
    year_start = datetime.date(year, 1, 1)
    year_end = datetime.date(year, 12, 31)

    sample_topic = config.NEWS_TOPICS[0] if getattr(config, 'NEWS_TOPICS',
                                                    []) else "Macro Economy"
    df = get_recent_news(sample_topic,
                         config.MARKET_DATA_DIR,
                         limit=50,
                         start_date=datetime.datetime(year, 1, 1),
                         end_date=datetime.datetime(year, 12, 31))

    if df is not None and len(df) > 10:
      logger.info(
          f"Year {year} already has sufficient data (checked via {sample_topic}). Skipping TSV backfill."
      )
      continue

    logger.info(f"Year {year} has sparse TSV data. Running historical fetch...")
    try:
      fetcher.fetch_historical_topic_news(start_date=year_start,
                                          end_date=year_end,
                                          thorough=False)
    except Exception as e:
      logger.error(f"Failed historical TSV fetch for {year}: {e}")

  logger.info("Completed structured TSV backfill.")


# ==============================================================================
# CLI EXECUTOR
# ==============================================================================


def main():
  parser = argparse.ArgumentParser(
      description=
      "Backfill structured TSVs or Markdown contexts for the market pipeline.")
  parser.add_argument(
      '--mode',
      choices=['md', 'tsv', 'all'],
      default='all',
      help=
      "Which backfill mechanism to run: 'md' for deep web scraping to markdown, 'tsv' for structured topic RSS feeds, or 'all'."
  )
  parser.add_argument(
      '--prospective',
      action='store_true',
      help=
      "If in 'md' mode, target 2026 prospective forecasts instead of deep 2018-2025 history."
  )
  args = parser.parse_args()

  if args.mode in ['tsv', 'all']:
    asyncio.run(backfill_tsv())

  if args.mode in ['md', 'all']:
    backfill_deep_md(args.prospective)


if __name__ == "__main__":
  main()
