"""Market Fetcher Library"""
import datetime
import hashlib
import logging
import os
import re
import shutil
import time
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import feedparser
import joblib
import pandas as pd
import requests
import yfinance as yf
from sec_edgar_downloader import Downloader
from textblob import TextBlob
from tqdm import tqdm

import config

# Config Logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Filename Constants
PRICES_FILENAME = "prices.tsv"
NEWS_FILENAME = "news.tsv"
INSIDER_FILENAME = "insider_trading.tsv"
FUNDAMENTALS_FILENAME = "fundamentals.tsv"
EARNINGS_FILENAME = "earnings.tsv"
FINANCIALS_FILENAME = "financials_quarterly.tsv"
MACRO_FILENAME = "economic_indicators.tsv"

# Default Feeds
DEFAULT_NEWS_FEEDS: Dict[str, str] = {
    "Yahoo":
        "https://finance.yahoo.com/rss/headline?s={term}",
    "Google":
        "https://news.google.com/rss/search?q={term}&hl=en-US&gl=US&ceid=US:en",
    # "Seeking Alpha": # unused feed
    #     "https://seekingalpha.com/api/sa/syndication/topics/{term}.xml"
}

# Ticker Aliases (Map symbol from Legacy -> Current 2026)
TICKER_ALIASES: Dict[str, str] = {
    "GOOGL": "GOOG",
    "FB": "META",
}

# FRED Economic Data Series
# Maps friendly names to FRED Series IDs.
FRED_SERIES: Dict[str, str] = {
    # Supply Chain & Production
    "FREIGHT_PPI": "PCU483111483111",  # Ocean Freight
    "AIR_PPI": "PCU481112481112",  # Air Freight
    "TRUCK_PPI": "PCU484121484121",  # Long-Distance Trucking
    "WAREHOUSE_PPI": "PCU493110493110",  # Warehousing & Storage
    "MFG_CONST": "TLMFGCONS",  # US Mfg Construction (Fabs/Data Centers)
    "TECH_PULSE": "IPB53110S",  # Industrial Production: High Tech

    # Trade & Tariffs
    "CHINA_IMPORTS": "IMPCH",  # US Imports from China
    "TARIFFS": "B235RC1Q027SBEA",  # US Customs Duties

    # Growth & Labor
    "GDP": "GDP",  # Gross Domestic Product
    "UNRATE": "UNRATE",  # Unemployment Rate
    "HOUSING_STARTS": "HOUST",  # Housing Starts
    "RECESSION_PROB": "RECPROUSM156N",  # Smoothed Recession Probability

    # Inflation & Rates
    "CPI": "CPIAUCSL",  # Consumer Price Index (All Items)
    "FEDFUNDS": "FEDFUNDS",  # Federal Funds Effective Rate
    "US02Y": "DGS2",  # 2-Year Treasury Yield
    "US10Y": "DGS10",  # 10-Year Treasury Yield
}

# Tickers to skip for Earnings/Financials.
# These are typically ETFs, Indices, or Futures which do not share the same
# financial reporting structure as individual companies (e.g. no EPS/Revenue misses).
# yapf: disable
SKIP_EARNINGS: List[str] = [
    # Indices & Volatility
    "^DJI", "^GSPC", "^IXIC", "^RUT", "^TNX", "^VIX",
    "CL=F", "GC=F",

    # ETFs (Sector/Commodity)
    "BDRY", "CORN", "CURM", "ITA", "PAVE", "SMH", "SOYB", "URA", "WEAT", "XLE",

    # ADRs / Foreign Listings (Irregular Financials)
    "ASML", "BHP", "BITF", "GOLD", "HUT", "NEM", "RIO", "TSM",

    # ETFs / Commodities
    "SPY", "COPX", "NG=F", "XLU", "VIXY"
]

# Tickers to skip for Insider Trading (ETFs, Indices, OTC)
SKIP_INSIDER: List[str] = SKIP_EARNINGS + [
    "AMKBY", # OTC/Foreign often lacks CIK mapping
    "PAVE", "ITA", "SMH", "URA", "XLE", # Sector ETFs
    # Foreign / ADRs (No Form 4)
    "ARM", "BMNR", "BP", "CCJ", "CNI", "CP", "PAAS", "SHEL", "TTE", "ZIM"
]
# yapf: enable

# CIK Overrides for tickers where automatic mapping fails.
# The SEC Edgar Downloader sometimes fails to map tickers to CIKs
# This map forces a specific CIK (Central Index Key) for these tickers.
CIK_OVERRIDES: Dict[str, str] = {
    "LLY": "0000059478",
    "LMT": "0000060410",
    "MATX": "0000003453",
    "SMCI": "0001006507",
    "SO": "0000092122",
    "UPS": "0001090727",
    "VRT": "0001804791",
}


class MarketFetcher:

  def __init__(self,
               data_dir: Optional[Union[str, Path]] = None,
               cache_dir: Optional[str] = None) -> None:
    self.data_dir = Path(data_dir) if data_dir else Path(config.DATA_DIR)
    self.cache_dir = Path(cache_dir) if cache_dir else Path(config.CACHE_DIR)
    self.data_dir.mkdir(parents=True, exist_ok=True)
    self.cache_dir.mkdir(parents=True, exist_ok=True)
    self.logger = logging.getLogger(__name__)
    self.aliases = TICKER_ALIASES
    self._av_keys = config.ALPHA_VANTAGE_KEYS
    self._current_key_idx = 0

  def _get_next_api_key(self) -> Optional[str]:
    """Rotates to the next available API key."""
    if not self._av_keys:
      return None
    self._current_key_idx = (self._current_key_idx + 1) % len(self._av_keys)
    return self._av_keys[self._current_key_idx]

  def _get_current_api_key(self) -> Optional[str]:
    if not self._av_keys:
      return None
    return self._av_keys[self._current_key_idx]

  @staticmethod
  def get_sentiment_score(text: str) -> float:
    """Returns a sentiment polarity score between -1.0 and 1.0."""
    try:
      return TextBlob(text).sentiment.polarity
    except Exception:
      return 0.0

  def _get_cache_path(self, key: str) -> Path:
    safe_key = re.sub(r'[^a-zA-Z0-9]', '_', key)
    return self.cache_dir / f"{safe_key}.pkl"

  def _load_cache(self, key: str, expiry_seconds: int = 3600) -> Optional[Any]:
    path = self._get_cache_path(key)
    if path.exists():
      timestamp = path.stat().st_mtime
      if time.time() - timestamp < expiry_seconds:
        try:
          return joblib.load(path)
        except Exception as e:
          self.logger.warning(f"Cache load failed for {key}: {e}")
          return None
    return None

  def _save_cache(self, key: str, data: Any) -> None:
    path = self._get_cache_path(key)
    joblib.dump(data, path)

  def _fetch_rss_content(self, url: str, source: str,
                         ticker: str) -> Optional[str]:
    """Fetches raw RSS content with caching."""
    # Cache based on source and ticker (URL might change slightly but usually source+ticker is unique enough for feed)
    # We use a hashing of URL to be safe if multiple URLs per source
    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_key = f"rss_raw_{source}_{ticker}_{url_hash}"

    content = self._load_cache(cache_key,
                               expiry_seconds=config.CACHE_EXPIRY_NEWS)
    if content:
      return content

    try:
      # Use a proper User-Agent
      headers = {'User-Agent': config.HTTP_USER_AGENT}
      r = requests.get(url, headers=headers, timeout=10)
      if r.status_code == 200:
        content = r.text
        self._save_cache(cache_key, content)
        return content
    except Exception as e:
      self.logger.warning(f"Failed to fetch RSS {source} for {ticker}: {e}")

    return None

  def get_ticker_path(self, ticker: str) -> Path:
    """Returns the directory path for a ticker or topic."""
    # Resolve alias if exists
    ticker = self.aliases.get(ticker, ticker)

    # Sanitize ticker for filesystem (e.g. ^GSPC -> GSPC, CL=F -> CL_F)
    # safe_ticker = ticker.replace('^', '').replace('=', '_')
    safe_ticker = ticker

    if ticker in config.NEWS_TOPICS:
      path = self.data_dir / "topics" / safe_ticker
    else:
      path = self.data_dir / "tickers" / safe_ticker

    path.mkdir(parents=True, exist_ok=True)
    return path

  def update_prices(self,
                    tickers: List[str],
                    start_date: str = config.DEFAULT_START_DATE) -> None:
    """Updates price history for tickers (TSV). Uses Yahoo Finance by default."""
    self.logger.info(
        f"Updating prices for {len(tickers)} tickers (Start: {start_date})...")

    for ticker in tqdm(tickers, desc="Prices"):
      ticker_path = self.get_ticker_path(ticker)
      prices_file = ticker_path / PRICES_FILENAME

      current_start = start_date
      existing_df = pd.DataFrame()
      fetch_needed = True

      if prices_file.exists():
        try:
          existing_df = pd.read_csv(prices_file,
                                    sep='\t',
                                    index_col=0,
                                    parse_dates=True)
          if not existing_df.empty:
            existing_min = existing_df.index.min()
            existing_max = existing_df.index.max()

            # Check if we need to backfill older data
            req_start_dt = pd.to_datetime(start_date)

            if existing_min > req_start_dt:
              self.logger.debug(
                  f"{ticker}: Existing data starts {existing_min.date()}, requested {req_start_dt.date()}. Refetching full history."
              )
              current_start = start_date
            elif existing_max >= (pd.Timestamp.now().normalize() -
                                  pd.Timedelta(days=1)):
              fetch_needed = False
            else:
              current_start = (existing_max +
                               datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        except Exception as e:
          self.logger.error(f"Error reading {ticker} prices: {e}")

      if not fetch_needed:
        continue

      # Optional: Alpha Vantage Implementation
      # if config.ALPHA_VANTAGE_KEY:
      #   url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={ticker}&outputsize=full&apikey={config.ALPHA_VANTAGE_KEY}&datatype=csv"
      #   try:
      #     av_df = pd.read_csv(url)
      #   except Exception as e:
      #     self.logger.warning(f"AlphaVantage fetch failed: {e}")

      cache_key = f"prices_{ticker}_{current_start}"
      new_data = self._load_cache(cache_key,
                                  expiry_seconds=config.CACHE_EXPIRY_PRICES)

      if new_data is None:
        try:
          df = yf.download(ticker,
                           start=current_start,
                           progress=False,
                           auto_adjust=False,
                           threads=False)

          if df.empty:
            self._save_cache(cache_key, pd.DataFrame())
            continue

          if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)

          if 'Adj Close' in df.columns:
            df['Close'] = df['Adj Close']

          cols = ['Open', 'High', 'Low', 'Close', 'Volume']
          cols = [c for c in cols if c in df.columns]
          new_data = df[cols]
          self._save_cache(cache_key, new_data)

        except Exception as e:
          self.logger.error(f"Failed to fetch {ticker}: {e}")
          continue

      if new_data is not None and not new_data.empty:
        new_data = new_data.round(2)
        if not existing_df.empty:
          combined = pd.concat([existing_df, new_data])
          combined = combined[~combined.index.duplicated(keep='last')]
          combined.sort_index(inplace=True)
        else:
          combined = new_data

        combined.to_csv(prices_file, sep='\t')
        # self.logger.info(f"Updated {ticker} (+{len(new_data)} rows)")

  def _extract_xml(self, filepath: Path) -> Optional[str]:
    """Extracts XML content from a full submission text file."""
    try:
      with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
      start = content.find('<?xml')
      end = content.rfind('</ownershipDocument>') + len('</ownershipDocument>')
      return content[start:end] if start != -1 and end != -1 else None
    except Exception as e:
      self.logger.warning(f"XML extraction failed for {filepath}: {e}")
      return None

  def _parse_f4(self, xml_str: str) -> List[tuple]:
    """Parses Form 4 XML for non-derivative transactions (P/S)."""
    try:
      root = ET.fromstring(xml_str)
    except Exception as e:
      self.logger.warning(f"XML parsing failed: {e}")
      return []

    ns = {'ns': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
    data = []

    for txn in root.findall('.//nonDerivativeTransaction', ns):
      try:
        code_elem = txn.find('.//transactionCoding/transactionCode', ns)
        if code_elem is None:
          continue
        code = code_elem.text.upper()
        if code not in ['P', 'S']:
          continue

        buy_flag = 1 if code == 'P' else 0
        date = txn.find('.//transactionDate/value', ns).text
        shares_elem = txn.find('.//transactionShares/value', ns)
        price_elem = txn.find('.//transactionPricePerShare/value', ns)

        shares = round(float(shares_elem.text),
                       2) if shares_elem is not None else 0.0
        price = round(float(price_elem.text),
                      4) if price_elem is not None else 0.0
        amount = round(shares * price, 2)

        data.append((date, shares, amount, buy_flag))
      except Exception:
        continue
    return data

  def update_insider_trading(self, tickers: List[str], limit: int = 10) -> None:
    """Updates Insider Trading data using SEC Edgar (Form 4)."""
    self.logger.info(f"Updating Insider Trading for {len(tickers)} tickers...")

    for ticker in tqdm(tickers, desc="Insider"):
      if ticker in config.SECTORS.get(
          "Macro Indices",
          []) or ticker in config.NEWS_TOPICS or ticker in SKIP_INSIDER:
        continue

      ticker_path = self.get_ticker_path(ticker)
      insider_file = ticker_path / INSIDER_FILENAME

      # Check Cache to avoid hitting SEC Edgar unnecessarily
      cache_key = f"insider_meta_{ticker}"
      if self._load_cache(cache_key,
                          expiry_seconds=config.CACHE_EXPIRY_INSIDER):
        continue

      # We download to a temp cache dir
      sec_cache = self.cache_dir / "sec_downloads"
      sec_cache.mkdir(exist_ok=True)

      # Initialize with download folder
      dl = Downloader(config.ALIAS, config.HTTP_USER_AGENT, sec_cache)

      try:
        # Check for CIK override
        query_lookup = CIK_OVERRIDES.get(ticker, ticker)

        # Fetch limited filings to be safe/polite
        dl.get("4", query_lookup, limit=limit, download_details=True)

        full_path = sec_cache / "sec-edgar-filings" / query_lookup / "4"
        all_tx = []

        if full_path.exists():
          for filing_dir in full_path.iterdir():
            # We look for full-submission.txt
            txt_path = filing_dir / "full-submission.txt"
            if txt_path.exists():
              xml = self._extract_xml(txt_path)
              if xml:
                all_tx.extend(self._parse_f4(xml))

        # Aggregate by day
        daily = {}
        for date, shares, amount, flag in all_tx:
          key = (date, flag)
          if key not in daily:
            daily[key] = {"shares": 0.0, "amount": 0.0}
          daily[key]["shares"] += shares
          daily[key]["amount"] += amount

        rows = sorted([
            (d, s["shares"], s["amount"], b) for (d, b), s in daily.items()
        ])

        if rows:
          new_df = pd.DataFrame(rows,
                                columns=["Date", "Shares", "Amount", "BuyFlag"])
          if insider_file.exists():
            try:
              old_df = pd.read_csv(insider_file, sep='\t')
              combined = pd.concat(
                  [old_df, new_df]).drop_duplicates(subset=["Date", "BuyFlag"])
              combined.sort_values(by=["Date", "BuyFlag"], inplace=True)
              combined.to_csv(insider_file, sep='\t', index=False)
            except:
              new_df.to_csv(insider_file, sep='\t', index=False)
          else:
            new_df.to_csv(insider_file, sep='\t', index=False)

          # Mark as cached/updated
          self._save_cache(cache_key, True)

      except Exception as e:
        self.logger.warning(f"Failed to fetch Insider for {ticker}: {e}")

  def _fetch_alphavantage_news(self,
                               ticker: str,
                               limit: int = 50) -> List[Dict[str, Any]]:
    """Fetches News Sentiment using AlphaVantage (Rich Metadata). Returns list of items."""
    if ticker in config.SECTORS.get("Macro Indices",
                                    []) or ticker in config.NEWS_TOPICS:
      return []

    try:
      url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&limit={limit}&apikey={config.ALPHA_VANTAGE_KEY}"

      # Cache First
      cache_key = f"av_news_{ticker}"
      data = self._load_cache(cache_key,
                              expiry_seconds=config.CACHE_EXPIRY_NEWS)

      if data is None:
        r = requests.get(url)
        if r.status_code == 200:
          data = r.json()
          self._save_cache(cache_key, data)

      if not data or "feed" not in data:
        return []

      items = []
      for article in data['feed']:
        # Create a rich item
        date_str = article.get("time_published", "")
        if not date_str:
          continue

        # Parse date strictly if possible, or just use string slicing as fallback if format is fixed
        # AV format: YYYYMMDDThhmmss
        try:
          dt = datetime.datetime.strptime(date_str, "%Y%m%dT%H%M%S")
        except ValueError:
          continue

        items.append({
            "date":
                dt,
            "date_str":
                dt.strftime('%Y-%m-%d'),
            "source":
                article.get("source", ""),
            "title":
                article.get("title", "").replace("\t", " ").replace("\n", " "),
            "link":
                article.get("url", ""),
            "sentiment":
                float(article.get("overall_sentiment_score", 0.0)),
            "summary":
                article.get("summary",
                            "").replace("\t", " ").replace("\n", " ")[:500],
            # "author": ",".join(article.get("authors", [])),
            # "tags": ",".join([t.get("topic", "") for t in article.get("topics", [])])
        })
      return items

    except Exception as e:
      self.logger.error(f"AlphaVantage Sentiment failed for {ticker}: {e}")
      return []

  def fetch_historical_news_premium(self,
                                    ticker: str,
                                    start_date: datetime.date,
                                    end_date: datetime.date,
                                    include_alphavantage: bool = False) -> int:
    """
      Fetches historical news for a ticker in weekly chunks to maximize coverage.
      Returns number of items added.
      """
    if not (include_alphavantage and self._av_keys):
      return 0

    self.logger.info(
        f"Backfilling news for {ticker} from {start_date} to {end_date}...")
    total_added = 0
    current_end = end_date

    # We iterate BACKWARDS from end_date to start_date
    while current_end > start_date:
      current_start = max(start_date, current_end - datetime.timedelta(days=7))

      # Format for API (YYYYMMDDTHHMM)
      time_from = current_start.strftime("%Y%m%dT0000")
      time_to = current_end.strftime("%Y%m%dT2359")

      # Retry logic for Rate Limits / Key Rotation
      max_retries = len(self._av_keys) if self._av_keys else 1
      if max_retries < 1:
        max_retries = 1
      if max_retries > 50:
        max_retries = 50

      success = False
      data = None

      # 1. Check Cache
      cache_key = f"av_news_hist_{ticker}_{time_from}_{time_to}"
      data = self._load_cache(cache_key, expiry_seconds=86400 * 30)

      if data and "feed" in data:
        success = True

      # 2. Fetch if not in cache
      if not success:
        for attempt in range(max_retries):
          api_key = self._get_current_api_key()
          if not api_key:
            self.logger.warning("No AlphaVantage API Keys available.")
            return total_added

          url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&time_from={time_from}&time_to={time_to}&limit=1000&apikey={api_key}"

          try:
            r = requests.get(url, timeout=15)
            data = r.json()

            # Check for Rate Limit / Error
            if "Information" in data and "rate limit" in data[
                "Information"].lower():
              self.logger.warning(
                  f"Key {api_key[:5]}... hit rate limit. Rotating...")
              self._get_next_api_key()
              time.sleep(1)  # Brief pause
              continue

            if "Error Message" in data:
              self.logger.warning(
                  f"API Error for {ticker} ({time_from}-{time_to}): {data['Error Message']}"
              )
              data = None
              # If error is permanent (bad ticker), maybe break? But here we skip chunk.
              break

            if "feed" in data:
              self._save_cache(cache_key, data)
              success = True
              break
          except Exception as e:
            self.logger.warning(f"Request failed for {ticker}: {e}")
            time.sleep(1)

      # 3. Process Data
      if success and data and "feed" in data:
        items = []
        for article in data['feed']:
          date_str = article.get("time_published", "")
          if not date_str:
            continue
          try:
            dt = datetime.datetime.strptime(date_str, "%Y%m%dT%H%M%S")
          except ValueError:
            continue

          items.append({
              "date":
                  dt,
              "date_str":
                  dt.strftime('%Y-%m-%d'),
              "source":
                  article.get("source", "") + " (AV-Hist)",
              "title":
                  article.get("title", "").replace("\t",
                                                   " ").replace("\n", " "),
              "link":
                  article.get("url", ""),
              "sentiment":
                  float(article.get("overall_sentiment_score", 0.0)),
              "summary":
                  article.get("summary",
                              "").replace("\t", " ").replace("\n", " ")[:500],
          })

        if items:
          self._save_news_tsv(ticker, items)
          total_added += len(items)
          self.logger.info(
              f"  + {len(items)} items for {current_start} - {current_end}")

      if not success:
        self.logger.error(
            f"Failed to fetch chunk {current_start} - {current_end} after {max_retries} attempts."
        )

      # Move Window Backwards
      current_end = current_start

    self.update_daily_sentiment([ticker])
    return total_added

  def update_news(self,
                  tickers: List[str],
                  feeds: Optional[Dict[str, str]] = None,
                  limit: int = config.DEFAULT_NEWS_LIMIT,
                  days_back: int = config.DEFAULT_NEWS_DAYS,
                  include_alphavantage: bool = False) -> None:
    """Updates news log (TSV, Newest on Top)"""
    self.logger.info(f"Updating news for {len(tickers)} tickers...")
    if feeds is None:
      feeds = DEFAULT_NEWS_FEEDS

    for ticker in tqdm(tickers, desc="RSS News"):
      ticker_path = self.get_ticker_path(ticker)

      # Scrape Benzinga explicitly (Disabled by default / Stubbed)
      bz_items: List[Dict[str, Any]] = []

      # Read all existing entries
      seen_links: Set[str] = set()
      tsv_file = ticker_path / NEWS_FILENAME

      if tsv_file.exists():
        try:
          existing_df = pd.read_csv(tsv_file, sep='\t')
          if 'URL' in existing_df.columns:
            seen_links = set(existing_df['URL'].astype(str))
        except Exception as e:
          self.logger.warning(f"Error reading existing news for {ticker}: {e}")

      # Fetch New
      cached_fresh = []

      cutoff = datetime.datetime.now() - datetime.timedelta(days=days_back)

      for src_name, url_template in feeds.items():
        try:
          safe_term = requests.utils.quote(ticker)
          url = url_template.format(term=safe_term)

          # Fetch Raw (Cached)
          raw_content = self._fetch_rss_content(url, src_name, ticker)
          if not raw_content:
            continue

          # Parse with feedparser (it handles raw strings too)
          feed = feedparser.parse(raw_content)

          for entry in feed.entries[:limit]:
            pub_dt = datetime.datetime.now()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
              pub_dt = datetime.datetime(*entry.published_parsed[:6])

            if pub_dt < cutoff:
              continue

            # Robust field extraction
            content = getattr(entry, 'summary', '') or getattr(
                entry, 'description', '')

            # Cleaning
            summary_text = getattr(entry, 'summary', '').replace('\n',
                                                                 ' ').strip()

            if src_name == "Google":
              summary_text = ""
            else:
              summary_text = re.sub(r'<[^>]+>', '', summary_text).strip()[:500]

            # Calculate Sentiment
            # Combine title + summary for coverage
            text_for_sentiment = entry.title + " " + summary_text
            sentiment_score = self.get_sentiment_score(text_for_sentiment)

            # Optional: Extract full content (often in 'content' or 'summary_detail')
            # full_content = ""
            # if hasattr(entry, 'content'):
            #     # entry.content is a list of dicts, e.g. [{'type': 'text/html', 'value': '...'}]
            #     full_content = "\n".join([c.get('value', '') for c in entry.content])

            # Optional: Extract Author (RSS feeds rarely provide this structured)
            # author = getattr(entry, 'author', '')

            # Optional: Extract Tags (RSS feeds rarely provide this structured)
            # tags = [t.term for t in getattr(entry, 'tags', [])]

            cached_fresh.append({
                'date': pub_dt,
                'date_str': pub_dt.strftime('%Y-%m-%d'),
                'source': src_name,
                'title': entry.title.replace('\n', ' ').strip(),
                'link': entry.link,
                'sentiment': sentiment_score,
                'summary': summary_text,
                # 'author': author,
                # 'tags': ",".join(tags),
                # 'content': full_content, # Too large/noisy for effective TSV storage
            })

        except Exception as e:
          self.logger.warning(
              f"Error processing feed {src_name} for {ticker}: {e}")
          continue

      # Optional: Fetch AlphaVantage
      if include_alphavantage and self._av_keys:
        av_items = self._fetch_alphavantage_news(ticker, limit)
        if av_items:
          cached_fresh.extend(av_items)

      # Merge New Unique
      new_unique = []
      for item in cached_fresh:
        # Legacy/New key mapping if needed
        link = item.get('link') or item.get('URL')
        if link not in seen_links:
          seen_links.add(link)
          new_unique.append(item)

      if not new_unique:
        continue

      # Sort everything by Date Descending
      # Handle mixed types for sorting if mostly datetime objects
      try:
        new_unique.sort(key=lambda x: x.get('date', datetime.datetime.min),
                        reverse=True)
      except Exception as e:
        self.logger.warning(f"Error sorting news items for {ticker}: {e}")

      # Save to TSV
      # Ensure sentiment and summary exist and keys match standard
      for item in new_unique:
        if 'sentiment' not in item:
          # Use Title + Summary for score
          text_for_score = item.get('title', '')
          if item.get('summary'):
            text_for_score += " " + item.get('summary')
          item['sentiment'] = self.get_sentiment_score(text_for_score)
        if 'summary' not in item:
          item['summary'] = ''

      self._save_news_tsv(ticker, new_unique)

    # Finally, update daily sentiment aggregation
    self.update_daily_sentiment(tickers)

  def update_daily_sentiment(self, tickers: List[str]) -> None:
    """Updates news_sentiment.tsv (Daily Mean Sentiment & Volume) from news.tsv"""
    self.logger.info(
        f"Aggregating Daily Sentiment for {len(tickers)} tickers...")

    for ticker in tqdm(tickers, desc="Daily Sentiment"):
      ticker_path = self.get_ticker_path(ticker)
      news_file = ticker_path / NEWS_FILENAME
      sentiment_file = ticker_path / "news_sentiment.tsv"

      if not news_file.exists():
        continue

      try:
        # Read News
        df = pd.read_csv(news_file, sep='\t')
        if df.empty or 'Date' not in df.columns or 'Sentiment' not in df.columns:
          continue

        # Parse Date
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df.dropna(subset=['Date'], inplace=True)

        # Group by Date
        daily_stats = df.groupby('Date').agg(
            Sentiment_Daily=('Sentiment', 'mean'),
            News_Volume=('Sentiment', 'count')).sort_index()

        # Round
        daily_stats['Sentiment_Daily'] = daily_stats['Sentiment_Daily'].round(4)

        # Load existing to preserve history (if any backfill exists)
        if sentiment_file.exists():
          existing = pd.read_csv(sentiment_file,
                                 sep='\t',
                                 index_col='Date',
                                 parse_dates=True)
          # Update existing with new values (overwrite overlaps)
          # Modified to prioritize EXISTING data to prevent overwriting verified/recent data during backfills
          final_df = existing.combine_first(daily_stats)
        else:
          final_df = daily_stats

        # Sort and Save
        final_df.sort_index(ascending=True, inplace=True)
        final_df.reset_index(inplace=True)
        final_df.to_csv(sentiment_file,
                        sep='\t',
                        index=False,
                        float_format='%.4f')

      except Exception as e:
        self.logger.error(
            f"Error aggregating daily sentiment for {ticker}: {e}")

  def update_financials(self,
                        tickers: List[str],
                        include_alphavantage: bool = False) -> None:
    """
    Updates Quarterly Financials (Income, Balance, Cash Flow).
    Saves to financials_quarterly.tsv in a Row-Based format (Index=Date).
    """
    self.logger.info(
        f"Updating Financials for {len(tickers)} tickers (AlphaVantage={include_alphavantage})..."
    )

    for ticker in tqdm(tickers, desc="Financials"):
      if ticker in config.SECTORS.get(
          "Macro Indices",
          []) or ticker in config.NEWS_TOPICS or ticker in SKIP_EARNINGS:
        continue

      ticker_path = self.get_ticker_path(ticker)
      fin_file = ticker_path / FINANCIALS_FILENAME

      combined_frames = []

      # 1. Fetch Yahoo Finance (Primary)
      try:
        yf_ticker = yf.Ticker(ticker)

        # Helper to fetch with caching
        def get_yf_df(attr_name: str) -> pd.DataFrame:
          cache_key = f"yf_{attr_name}_{ticker}"
          data = self._load_cache(
              cache_key, expiry_seconds=config.CACHE_EXPIRY_FUNDAMENTALS)
          if data is None:
            try:
              data = getattr(yf_ticker, attr_name)
              if data is not None and not data.empty:
                self._save_cache(cache_key, data)
            except Exception:
              return pd.DataFrame()
          return data if data is not None else pd.DataFrame()

        # Yahoo returns (Metrics x Date), we want (Date x Metrics) so we Transpose (.T)
        inc = get_yf_df("quarterly_financials").T
        if not inc.empty:
          combined_frames.append(inc)

        bal = get_yf_df("quarterly_balance_sheet").T
        if not bal.empty:
          combined_frames.append(bal)

        cf = get_yf_df("quarterly_cashflow").T
        if not cf.empty:
          combined_frames.append(cf)

      except Exception as e:
        self.logger.warning(f"Yahoo financials failed for {ticker}: {e}")

      # 2. AlphaVantage (Optional Backfill)
      # (Logic adapted from previous version but integrated here)
      if include_alphavantage and self._av_keys:
        endpoints = {
            "INCOME_STATEMENT": ["quarterlyReports", "fiscalDateEnding"],
            "BALANCE_SHEET": ["quarterlyReports", "fiscalDateEnding"],
            "CASH_FLOW": ["quarterlyReports", "fiscalDateEnding"],
            "EARNINGS": ["quarterlyEarnings", "fiscalDateEnding"]
        }

        for func, paths in endpoints.items():
          list_key, date_key = paths

          # Simple retry/fetch logic
          max_retries = len(self._av_keys) if self._av_keys else 1
          if max_retries > 5:
            max_retries = 5

          data = None
          for _ in range(max_retries):
            api_key = self._get_current_api_key()
            if not api_key:
              break
            try:
              url = f"https://www.alphavantage.co/query?function={func}&symbol={ticker}&apikey={api_key}"
              r = requests.get(url, timeout=10)
              resp = r.json()
              if "Information" in resp and "rate limit" in resp[
                  "Information"].lower():
                self._get_next_api_key()
                time.sleep(1)
                continue
              if list_key in resp:
                data = resp[list_key]
                break
              break
            except:
              self._get_next_api_key()
              time.sleep(1)

          if data:
            # Convert to DF
            df = pd.DataFrame(data)
            if date_key in df.columns:
              df[date_key] = pd.to_datetime(df[date_key], errors='coerce')
              df.set_index(date_key, inplace=True)
              # Convert numerics
              for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
              combined_frames.append(df)

      # 3. Merge and Save
      if not combined_frames:
        continue

      full_df = pd.DataFrame()
      for df in combined_frames:
        if not isinstance(df.index, pd.DatetimeIndex):
          try:
            df.index = pd.to_datetime(df.index)
          except:
            continue

        # Combine
        if full_df.empty:
          full_df = df
        else:
          full_df = full_df.combine_first(df)

      if not full_df.empty:
        full_df.sort_index(ascending=False, inplace=True)
        full_df.to_csv(fin_file, sep='\t')

  def _save_news_tsv(self, ticker: str, items: List[Dict[str, Any]]) -> None:
    """Saves news items to a TSV file (Deduplicated & Sorted)."""
    ticker_path = self.get_ticker_path(ticker)
    tsv_file = ticker_path / NEWS_FILENAME

    # Convert items to DataFrame
    new_df = pd.DataFrame(items)
    if new_df.empty:
      return

    # Standardize columns
    if 'date_str' in new_df.columns:
      new_df = new_df.rename(columns={'date_str': 'Date'})
    elif 'date' in new_df.columns:
      new_df.rename(columns={'date': 'Date'}, inplace=True)

    # Rename lower case keys if needed
    new_df = new_df.rename(
        columns={
            'source': 'Source',
            'title': 'Headline',
            'link': 'URL',
            'sentiment': 'Sentiment',
            'sentiment': 'Sentiment',
            'summary': 'Summary',
            'author': 'Author',
            'tags': 'Tags'
        })

    # Ensure only these columns exist (and handle missing ones)
    # Removed 'Author', 'Tags' as RSS feeds typically don't provide them and they were mostly empty.
    final_cols = ['Date', 'Source', 'Sentiment', 'Headline', 'Summary', 'URL']
    for c in final_cols:
      if c not in new_df.columns:
        new_df[c] = ''

    new_df = new_df[final_cols]

    # Clean string fields for TSV (remove tabs/newlines)
    for col in ['Source', 'Headline', 'URL', 'Summary']:
      new_df[col] = new_df[col].astype(str).str.replace('\t', ' ').str.replace(
          '\n', ' ')

    # Load existing if available
    if tsv_file.exists():
      try:
        existing_df = pd.read_csv(tsv_file, sep='\t')
        # Ensure columns match
        for c in final_cols:
          if c not in existing_df.columns:
            existing_df[c] = ''
        existing_df = existing_df[final_cols]
        # Concat
        combined = pd.concat([existing_df, new_df])
      except Exception as e:
        self.logger.warning(
            f"Error processing existing TSV for {ticker}, overwriting: {e}")
        combined = new_df
    else:
      combined = new_df

    # Deduplicate by URL
    combined.drop_duplicates(subset=['URL'], keep='last', inplace=True)

    # Sort by Date Descending, then Sentiment Descending (Deterministic)
    try:
      combined['Date'] = pd.to_datetime(combined['Date'], errors='coerce')
      combined.dropna(subset=['Date'], inplace=True)

      # Round Sentiment to 3 decimals to reduce diff noise
      if 'Sentiment' in combined.columns:
        combined['Sentiment'] = pd.to_numeric(
            combined['Sentiment'], errors='coerce').fillna(0.0).round(3)

      # Deterministic Sort: Date (Desc) -> Sentiment (Desc) -> Headline (Asc)
      sort_cols = ['Date', 'Headline']
      sort_asc = [False, True]

      if 'Sentiment' in combined.columns:
        sort_cols.insert(1, 'Sentiment')
        sort_asc.insert(1, False)

      combined.sort_values(by=sort_cols, ascending=sort_asc, inplace=True)

      # Convert back to string YYYY-MM-DD
      combined['Date'] = combined['Date'].dt.strftime('%Y-%m-%d')

      # Round Sentiment to 3 decimals to reduce diff noise
      if 'Sentiment' in combined.columns:
        combined['Sentiment'] = combined['Sentiment'].astype(float).round(3)

      # 2. Fuzzy Deduplication (Windowed)
      combined = self._fuzzy_deduplicate(combined, threshold=0.90)

    except Exception as e:
      self.logger.error(f"Error in _save_news_tsv for {ticker}: {e}")

    combined.to_csv(tsv_file, sep='\t', index=False)

  def _fuzzy_deduplicate(
      self,
      df: pd.DataFrame,
      threshold: float = config.FUZZY_DEDUPE_THRESHOLD) -> pd.DataFrame:
    """Deduplicates rows based on fuzzy Headline matching, prioritizing higher quality items."""
    if df.empty or len(df) < 2:
      return df

    # Helper to calculate quality score
    def calc_quality(row):
      score = 0
      source = str(row.get('Source', ''))

      # Penalize Google News significantly because it lacks summaries (-1000)
      if 'Google' in source:
        score -= 1000

      # Prefer non-zero sentiment (+1000)
      if abs(row.get('Sentiment', 0.0)) > 0:
        score += 1000

      # Prefer known good sources (+500)
      if any(x in source
             for x in ['AlphaVantage', 'Yahoo', 'Reuters', 'Bloomberg', 'WSJ']):
        score += 500

      # Prefer longer summaries (1 point per character)
      score += len(str(row.get('Summary', '')))
      return score

    # Pre-calculate quality scores
    df['Quality'] = df.apply(calc_quality, axis=1)

    # Normalize headlines for comparison
    headlines = df['Headline'].astype(str).str.lower().str.strip().tolist()
    qualities = df['Quality'].tolist()

    # We iterate through the list. Since we want to check for duplicates that might be
    # slightly apart in time, we assume the DF is somewhat sorted by date (or we sort it).
    # The caller `_save_news_tsv` sorts by Date Descending before this.

    to_drop = set()
    num_rows = len(df)
    window_size = 50  # Increased window size for broader detection

    for i in range(num_rows):
      if i in to_drop:
        continue

      # Look ahead
      for j in range(i + 1, min(i + window_size, num_rows)):
        if j in to_drop:
          continue

        # Compare headlines
        ratio = SequenceMatcher(None, headlines[i], headlines[j]).ratio()
        if ratio > threshold:
          # Duplicate found. Keep the one with higher quality.
          if qualities[i] >= qualities[j]:
            to_drop.add(j)
          else:
            to_drop.add(i)
            break  # Stop checking i, it's marked for dropping

    # Drop the identified duplicates
    if to_drop:
      dropped_indices = list(to_drop)
      dropped_df = df.iloc[dropped_indices]
      self.logger.debug(
          f"Fuzzy Dedupe: Dropped {len(dropped_df)} items for {df.iloc[0]['Headline'][:20]}..."
      )
      self.logger.debug(
          f"Dropped Sources: {dropped_df['Source'].value_counts().to_dict()}")
      df = df.drop(df.index[dropped_indices])

    # Cleanup temporary column
    return df.drop(columns=['Quality'], errors='ignore')

  def update_fundamentals(self,
                          tickers: List[str],
                          include_alphavantage: bool = False) -> None:
    """Updates fundamentals (TSV Key-Value) & Earnings (TSV). Optional AlphaVantage Overview merge."""
    self.logger.info(
        f"Updating fundamentals (AlphaVantage={include_alphavantage})...")

    for ticker in tqdm(tickers, desc="Fundamentals"):
      ticker_path = self.get_ticker_path(ticker)

      # 1. Info / Stats
      cache_key = f"fund_{ticker}"
      info = self._load_cache(cache_key,
                              expiry_seconds=config.CACHE_EXPIRY_FUNDAMENTALS)

      if info is None:
        try:
          stock = yf.Ticker(ticker)
          info = stock.info
          self._save_cache(cache_key, info)
        except Exception as e:
          self.logger.warning(f"Failed to fetch info for {ticker}: {e}")
          continue

      # 1b. Preserve existing keys (e.g. pegRatio) if missing from fresh fetch
      fund_path = ticker_path / FUNDAMENTALS_FILENAME
      if fund_path.exists():
        try:
          existing_df = pd.read_csv(fund_path,
                                    sep='\t',
                                    names=['Metric', 'Value'],
                                    header=0)
          for _, row in existing_df.iterrows():
            k, v = row['Metric'], row['Value']
            if k not in info and pd.notna(v) and str(v).lower() != 'none':
              try:
                if '.' in str(v):
                  v = float(v)
                else:
                  v = int(v)
              except (ValueError, TypeError):
                pass  # Not numeric, keep as string
              info[k] = v
        except Exception as e:
          self.logger.warning(
              f"Failed to read existing fundamentals for {ticker}: {e}")

      if info:
        # Refined Logic: Only use syntheticPEG if pegRatio is MISSING.
        # If pegRatio exists, remove syntheticPEG to avoid redundancy.
        if info.get("pegRatio"):
          info.pop("syntheticPEG", None)
        else:
          peg_calc = None
          try:
            pe = info.get("forwardPE") or info.get("trailingPE")
            gr = info.get("earningsGrowth") or info.get("revenueGrowth")
            if pe and gr:
              peg_calc = pe / (gr * 100)
          except Exception as e:
            self.logger.warning(
                f"Failed to calculate syntheticPEG for {ticker}: {e}")

          if peg_calc:
            info['syntheticPEG'] = peg_calc

        # Merge Alpha Vantage Overview if enabled
        if include_alphavantage and self._av_keys:
          try:
            # Basic retry logic for AV
            max_retries = len(self._av_keys) if self._av_keys else 1
            if max_retries > 3:
              max_retries = 3

            overview = None
            for _ in range(max_retries):
              api_key = self._get_current_api_key()
              if not api_key:
                break
              try:
                url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={api_key}"
                r = requests.get(url, timeout=10)
                data = r.json()
                if "Information" in data and "rate limit" in data[
                    "Information"].lower():
                  self._get_next_api_key()
                  time.sleep(1)
                  continue
                if "Symbol" in data:
                  overview = data
                  break
                break
              except:
                self._get_next_api_key()
                time.sleep(1)

            if overview:
              # Map interesting AV fields to info dict
              av_fields = {
                  "MarketCapitalization": "marketCap",
                  "PERatio": "trailingPE",
                  "PEGRatio": "pegRatio",
                  "BookValue": "bookValue",
                  "DividendPerShare": "dividendRate",
                  "EPS": "trailingEps",
                  "ProfitMargin": "profitMargins",
                  "OperatingMarginTTM": "operatingMargins",
                  "ReturnOnAssetsTTM": "returnOnAssets",
                  "ReturnOnEquityTTM": "returnOnEquity",
                  "Beta": "beta",
                  "52WeekHigh": "fiftyTwoWeekHigh",
                  "52WeekLow": "fiftyTwoWeekLow",
                  # Additional fields common in AV:
                  "ForwardPE": "forwardPE",
                  "PriceToSalesRatioTTM": "priceToSalesTrailing12Months",
                  "PriceToBookRatio": "priceToBook",
                  "EVToRevenue": "enterpriseToRevenue",
                  "EVToEBITDA": "enterpriseToEbitda"
              }

              for av_k, yf_k in av_fields.items():
                val = overview.get(av_k)
                if val and val != "None":
                  try:
                    v_float = float(val)
                  except:
                    v_float = val

                  # Backfill from AV (No Prefix as requested) if missing in Yahoo
                  if yf_k not in info or info[yf_k] in [None, "None", 0, 0.0]:
                    info[yf_k] = v_float
          except Exception as e:
            self.logger.warning(f"AV Fundamentals failed for {ticker}: {e}")

        sorted_keys = sorted(info.keys())
        with open(ticker_path / FUNDAMENTALS_FILENAME, 'w',
                  encoding='utf-8') as f:
          f.write("Metric\tValue\n")
          for k in sorted_keys:
            val = str(info[k]).replace('\t', ' ').replace('\n', ' ')
            f.write(f"{k}\t{val}\n")

      # 2. Earnings & 3. Financials
      if ticker in SKIP_EARNINGS:
        continue

      stock = yf.Ticker(ticker)
      try:
        earn_key = f"earn_{ticker}"
        earnings = self._load_cache(
            earn_key, expiry_seconds=config.CACHE_EXPIRY_FUNDAMENTALS)
        if earnings is None:
          earnings = stock.earnings_dates
          if earnings is not None:
            self._save_cache(earn_key, earnings)

        if earnings is not None and not earnings.empty:
          earnings.to_csv(ticker_path / EARNINGS_FILENAME, sep='\t')
      except Exception as e:
        self.logger.warning(f"Earnings fetch failed for {ticker}: {e}")

  def update_macro(self, fred_years: int = 5) -> None:
    """Updates Macro Data (FRED)"""
    self.logger.info("Updating Macro/FRED data...")
    # Structured macro data
    macro_dir = self.data_dir / "macro"
    macro_dir.mkdir(parents=True, exist_ok=True)
    macro_file = macro_dir / MACRO_FILENAME

    combined_fred = pd.DataFrame()

    for name, series_id in FRED_SERIES.items():
      cache_key = f"fred_{name}_{series_id}"
      series = self._load_cache(cache_key,
                                expiry_seconds=config.CACHE_EXPIRY_MACRO)

      if series is None:
        try:
          url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
          series = pd.read_csv(url, index_col=0, parse_dates=True)
          self._save_cache(cache_key, series)
        except Exception as e:
          self.logger.warning(f"Failed to fetch FRED {name}: {e}")
          continue

      if series is not None and not series.empty:
        series = series.rename(columns={series_id: name})
        if combined_fred.empty:
          combined_fred = series
        else:
          combined_fred = combined_fred.join(series, how='outer')

    if not combined_fred.empty:
      combined_fred = combined_fred.sort_index().round(4)
      combined_fred.to_csv(macro_file, sep='\t')
      self.logger.info("FRED data updated.")

  def generate_data_stats(self) -> None:
    """Generates a markdown report of data health."""
    self.logger.info("Generating data validation audit (Stats Report)...")

    ticker_dir = self.data_dir / "tickers"
    topic_dir = self.data_dir / "topics"

    report = []
    report.append("# Data Stats Report")
    report.append(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")

    # 1. Global Metrics
    total_tickers = 0
    if ticker_dir.exists():
      total_tickers = len([x for x in ticker_dir.iterdir() if x.is_dir()])

    total_topics = 0
    if topic_dir.exists():
      total_topics = len([x for x in topic_dir.iterdir() if x.is_dir()])

    # Count total news
    total_news = 0
    # Scan tickers
    if ticker_dir.exists():
      for t in ticker_dir.iterdir():
        if (t / NEWS_FILENAME).exists():
          try:
            df = pd.read_csv(t / NEWS_FILENAME, sep='\t')
            total_news += len(df)
          except:
            pass
    # Scan topics
    if topic_dir.exists():
      for t in topic_dir.iterdir():
        if (t / NEWS_FILENAME).exists():
          try:
            df = pd.read_csv(t / NEWS_FILENAME, sep='\t')
            total_news += len(df)
          except:
            pass

    report.append("## 1. Global Metrics")
    report.append(f"- **Total Tickers**: {total_tickers}")
    report.append(f"- **Total Topics**: {total_topics}")
    report.append(f"- **Total News Items**: {total_news}")
    report.append("")

    # 2. Ticker Data
    report.append("## 2. Ticker Data")
    report.append(
        "| Ticker | Price Range | News | Insider | NaNs | Missing Files |")
    report.append("|---|---|---|---|---|---|")

    missing_files = {}

    if ticker_dir.exists():
      tickers = sorted([t.name for t in ticker_dir.iterdir() if t.is_dir()])
      for ticker in tickers:
        t_path = ticker_dir / ticker
        prices_file = t_path / PRICES_FILENAME
        news_file = t_path / NEWS_FILENAME

        # Check prices
        price_range = "Missing"
        nan_count = 0
        if prices_file.exists():
          try:
            df = pd.read_csv(prices_file, sep='\t')
            if not df.empty and 'Date' in df.columns:
              dates = pd.to_datetime(df['Date'])
              price_range = f"{dates.min().date()} to {dates.max().date()}"
              nan_count = df.isna().sum().sum()
          except:
            price_range = "Error"
        else:
          if ticker not in missing_files:
            missing_files[ticker] = []
          missing_files[ticker].append(PRICES_FILENAME)

        # Check news (RSS)
        news_count = 0
        if news_file.exists():
          try:
            ndf = pd.read_csv(news_file, sep='\t')
            news_count = len(ndf)
          except:
            pass

        # Check Insider
        ins_count = 0
        if (t_path / INSIDER_FILENAME).exists():
          try:
            ndf = pd.read_csv(t_path / INSIDER_FILENAME, sep='\t')
            ins_count = len(ndf)
          except:
            pass

        # Check Missing Files
        expected_files = [PRICES_FILENAME, NEWS_FILENAME, FUNDAMENTALS_FILENAME]

        # Add conditional files
        if ticker not in SKIP_EARNINGS:
          expected_files.append(EARNINGS_FILENAME)
          expected_files.append(FINANCIALS_FILENAME)

        if ticker not in SKIP_INSIDER:
          expected_files.append(INSIDER_FILENAME)

        files_missing_list = []
        for fname in expected_files:
          if not (t_path / fname).exists():
            files_missing_list.append(fname)
            # Add to global missing list for summary
            if ticker not in missing_files:
              missing_files[ticker] = []
            if fname not in missing_files[ticker]:
              missing_files[ticker].append(fname)

        missing_str = " ".join(
            files_missing_list) if files_missing_list else "None"

        report.append(
            f"| {ticker} | {price_range} | {news_count} | {ins_count} | {nan_count} | {missing_str} |"
        )

    report.append("")

    # 3. Topic Data
    report.append("## 3. Topic Data (News Only)")
    report.append("| Topic | News Count | Start Date | End Date |")
    report.append("|---|---|---|---|")

    if topic_dir.exists():
      topics = sorted([t.name for t in topic_dir.iterdir() if t.is_dir()])
      for topic in topics:
        t_path = topic_dir / topic
        news_file = t_path / NEWS_FILENAME

        count = 0
        start = "-"
        end = "-"

        if news_file.exists():
          try:
            df = pd.read_csv(news_file, sep='\t')
            count = len(df)
            if not df.empty and 'Date' in df.columns:
              dates = pd.to_datetime(df['Date'])
              start = dates.min().date()
              end = dates.max().date()
          except:
            pass

        report.append(f"| {topic} | {count} | {start} | {end} |")

    report.append("")

    # 4. Macro Data
    macro_file = self.data_dir / "macro" / MACRO_FILENAME
    if macro_file.exists():
      try:
        df_macro = pd.read_csv(macro_file, sep='\t')
        report.append(f"## 4. Macro Data")
        report.append(f"- **File**: `market_data/macro/{MACRO_FILENAME}`")
        report.append(f"- **Total Rows**: {len(df_macro)}")
        report.append("")
        report.append(f"### Health Check")
        report.append(
            f"| Indicator | Valid Rows | Start Date | End Date | Status |")
        report.append(f"|---|---|---|---|---|")

        for col in df_macro.columns:
          if col == "observation_date":
            continue
          valid = df_macro[col].dropna()
          count = len(valid)
          if count == 0:
            status = "Empty"
            start = "N/A"
            end = "N/A"
          elif count > len(df_macro) * 0.9:
            status = "Daily"
          elif count > len(df_macro) * 0.04:
            status = "Monthly"
          elif count > len(df_macro) * 0.01:
            status = "Quarterly"
          else:
            status = "Sparse"

          if 'observation_date' in df_macro.columns:
            dates = df_macro.loc[valid.index, 'observation_date']
            start = dates.min()
            end = dates.max()
          else:
            start = "?"
            end = "?"

          report.append(f"| {col} | {count} | {start} | {end} | {status} |")

      except Exception as e:
        report.append(f"- **Error reading macro data**: {e}")
    else:
      report.append("## 4. Macro Data")
      report.append(f"- **Status**: Missing `{MACRO_FILENAME}`")

    report.append("")
    report.append("## 5. Missing Files / Anomalies")
    if missing_files:
      for name, files in missing_files.items():
        report.append(f"- **{name}**: Missing {', '.join(files)}")
    else:
      report.append("No missing core files detected.")

    # Save to market_data/STATS.md
    audit_file = self.data_dir / "STATS.md"
    with open(audit_file, "w") as f:
      f.write("\n".join(report))
    self.logger.info(f"Created {audit_file}")

  def generate_data_schema(self) -> None:
    """Generates DATA_SCHEMA.md based on current data files."""
    self.logger.info("Generating data schema report...")
    report = []
    report.append("# Data Schema Report")
    report.append("")
    report.append(
        "This report documents the file structures and column data types used in `market_data/`."
    )
    report.append("")

    ticker_dir = self.data_dir / "tickers"
    if ticker_dir.exists():
      example_ticker = None
      for t in ticker_dir.iterdir():
        if t.is_dir() and (t / "prices.tsv").exists():
          example_ticker = t
          break

      if example_ticker:
        report.append(f"## 1. Ticker Files (Example: `{example_ticker.name}`)")

        files_to_scan = [
            (PRICES_FILENAME, "Daily OHLCV Prices"),
            (FUNDAMENTALS_FILENAME, "Key Statistics (Key-Value)"),
            (EARNINGS_FILENAME, "Earnings Dates & Estimates"),
            (FINANCIALS_FILENAME, "Quarterly Financials"),
            (NEWS_FILENAME, "News Data (RSS + AlphaVantage Sentiment)"),
            # ("news_av.tsv", "News Data (AlphaVantage Sentiment)"), # Merged
            (INSIDER_FILENAME, "Insider Trading Data")
        ]

        for fname, desc in files_to_scan:
          fpath = example_ticker / fname
          if not fpath.exists():
            continue

          report.append(f"### `{fname}` - {desc}")

          # News Sentiment (Backfill/Daily)
          if fname == "news_sentiment.tsv":
            sent_path = example_ticker / "news_sentiment.tsv"
            if sent_path.exists():
              try:
                sdf = pd.read_csv(sent_path, sep='\t')
                report.append(
                    f"### `news_sentiment.tsv` - Daily Sentiment & Volume")
                report.append(f"| Column | Type | Example |")
                report.append(f"|---|---|---|")
                for col in sdf.columns:
                  dtype = str(sdf[col].dtype)
                  example = "N/A"
                  valid = sdf[col].dropna()
                  if not valid.empty:
                    example = str(valid.iloc[0])
                  report.append(f"| {col} | {dtype} | {example} |")
                report.append("")

                # Add specific stats
                n_rows = len(sdf)
                n_nans = sdf['Sentiment_Daily'].isna().sum()
                report.append(
                    f"> **Stats**: {n_rows} rows. {n_nans} NaNs in Sentiment_Daily ({(n_nans/n_rows)*100:.1f}%)."
                )
                report.append("")
              except Exception as e:
                report.append(f"> Error reading news_sentiment.tsv: {e}")
            continue

          if fname.endswith('.tsv') or fname.endswith('.csv'):
            sep = '\t' if fname.endswith('.tsv') else ','
            try:
              df = pd.read_csv(fpath, sep=sep)
              report.append(f"| Column | Type | Example |")
              report.append(f"|---|---|---|")
              for col in df.columns[:10]:
                dtype = str(df[col].dtype)

                # Find first non-null example
                example = "N/A (Empty)"
                valid_rows = df[col].dropna()
                if not valid_rows.empty:
                  example = str(valid_rows.iloc[0])

                if len(example) > 50:
                  example = example[:47] + "..."
                report.append(f"| {col} | {dtype} | {example} |")
              if len(df.columns) > 10:
                report.append(f"| ... ({len(df.columns)-10} more) | | |")
            except Exception as e:
              report.append(f"> Error reading schema: {e}")

          report.append("")

    # Topic Files (Example)
    topic_dir = self.data_dir / "topics"
    if topic_dir.exists():
      example_topic = None
      for t in topic_dir.iterdir():
        if t.is_dir() and (t / NEWS_FILENAME).exists():
          example_topic = t
          break

      if example_topic:
        report.append(f"## 2. Topic Files (Example: `{example_topic.name}`)")
        report.append(f"### `{NEWS_FILENAME}` - Topic News")
        try:
          df = pd.read_csv(example_topic / NEWS_FILENAME, sep='\t')
          report.append(f"| Column | Type | Example |")
          report.append(f"|---|---|---|")
          for col in df.columns[:10]:
            dtype = str(df[col].dtype)
            example = "N/A"
            if not df[col].empty:
              example = str(df[col].iloc[0])
            if len(example) > 50:
              example = example[:47] + "..."
            report.append(f"| {col} | {dtype} | {example} |")
        except Exception as e:
          report.append(f"> Error reading schema: {e}")
        report.append("")

    # Macro Files (Flat)
    macro_file = self.data_dir / "macro" / MACRO_FILENAME
    if macro_file.exists():
      report.append("## 2. Macro Files")
      report.append(
          f"### `market_data/macro/{MACRO_FILENAME}` - Economic Indicators")
      try:
        df = pd.read_csv(macro_file, sep='\t', index_col=0)
        report.append(f"| Indicator (Column) | Type | Example |")
        report.append(f"|---|---|---|")
        for col in df.columns:
          dtype = str(df[col].dtype)
          example = "N/A (Empty)"
          valid_rows = df[col].dropna()
          if not valid_rows.empty:
            example = str(valid_rows.iloc[0])

          if len(example) > 50:
            example = example[:47] + "..."
          report.append(f"| {col} | {dtype} | {example} |")
      except Exception as e:
        report.append(f"> Error reading schema: {e}")

    # Save to market_data/SCHEMA.md
    schema_file = self.data_dir / "SCHEMA.md"
    with open(schema_file, "w", encoding="utf-8") as f:
      f.write("\n".join(report))
    self.logger.info(f"Created {schema_file}")


def main():
  logging.basicConfig(
      level=logging.INFO,
      format='%(message)s'  # Keep it simple for user output
  )

  print("🚀 Starting Market Data Fetcher...")

  # Initialize
  fetcher = MarketFetcher()

  # Collect All Tickers
  all_tickers = set()
  for sector, tickers in config.SECTORS.items():
    print(f"   Loaded {len(tickers)} from {sector}")
    all_tickers.update(tickers)

  sorted_tickers = sorted(list(all_tickers))
  print(f"📋 Total Tickers: {len(sorted_tickers)}")

  # Argument Parsing
  import argparse
  parser = argparse.ArgumentParser(description="Run Market Fetcher")
  parser.add_argument("--limit-tickers",
                      type=int,
                      help="Limit number of tickers to fetch")
  parser.add_argument("--limit-topics",
                      type=int,
                      help="Limit number of news topics to fetch")
  parser.add_argument("--news-days",
                      type=int,
                      default=config.DEFAULT_NEWS_DAYS,
                      help="Days of news to fetch")
  parser.add_argument("--news-limit",
                      type=int,
                      default=config.DEFAULT_NEWS_LIMIT,
                      help="Max news items per ticker")
  parser.add_argument(
      "--insider-limit",
      type=int,
      default=10,
      help="Max insider filings to fetch (increase for backfill)")
  args = parser.parse_args()

  # Apply Limits
  if args.limit_tickers:
    print(f"⚠️ LIMITING TICKERS: {args.limit_tickers} (Top alphabetically)")
    sorted_tickers = sorted_tickers[:args.limit_tickers]

  # Pipeline
  # 1. Macro
  fetcher.update_macro()

  # 2. Prices
  fetcher.update_prices(sorted_tickers, start_date=config.DEFAULT_START_DATE)

  # 3. Fundamentals & Earnings
  fetcher.update_fundamentals(sorted_tickers,
                              include_alphavantage=config.ENABLE_ALPHA_VANTAGE)

  # 4. Financials (Row-Based)
  fetcher.update_financials(sorted_tickers,
                            include_alphavantage=config.ENABLE_ALPHA_VANTAGE)

  # 5. Insider Trading (SEC)
  fetcher.update_insider_trading(sorted_tickers, limit=args.insider_limit)

  # 6. News & Sentiment (Optional Topic Limits)
  if args.limit_topics:
    print(f"⚠️ LIMITING TOPICS: {args.limit_topics}")
    config.NEWS_TOPICS = config.NEWS_TOPICS[:args.limit_topics]
  elif args.limit_tickers and args.limit_tickers <= 5:
    # Auto-limit topics if heavily restricted (heuristic for 'test mode')
    print(f"⚠️ LIMITING TOPICS: 1 (Test Mode Heuristic)")
    config.NEWS_TOPICS = config.NEWS_TOPICS[:1]

  print(f"📰 Updating News (Tickers + {len(config.NEWS_TOPICS)} Topics)...")

  all_news_targets = sorted_tickers + config.NEWS_TOPICS

  fetcher.update_news(all_news_targets,
                      limit=args.news_limit,
                      days_back=args.news_days,
                      include_alphavantage=config.ENABLE_ALPHA_VANTAGE)

  print("\n✅ All updates complete.")
  print(f"📁 Database: {os.path.abspath(fetcher.data_dir)}")

  # 7. Schema & Stats Report
  fetcher.generate_data_schema()
  fetcher.generate_data_stats()


if __name__ == "__main__":
  main()
