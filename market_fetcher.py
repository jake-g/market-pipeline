"""Market Fetcher Library"""
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
import datetime
from difflib import SequenceMatcher
import hashlib
import logging
import os
from pathlib import Path
import random
import re
import shutil
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import urllib.parse
import xml.etree.ElementTree as ET

from curl_cffi import requests as cffi_requests
import feedparser
import joblib
from lxml import html
import numpy as np
import pandas as pd
import requests
from sec_edgar_downloader import Downloader
from textblob import TextBlob
from tqdm import tqdm
import yfinance as yf

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

# Search terms for short or dictionary-word tickers to prevent non-financial noise (e.g. pet cat news for CAT)
TICKER_SEARCH_TERMS: Dict[str, str] = {
    "ON":
        "ON Semiconductor stock",
    "MS":
        "Morgan Stanley stock",
    "V":
        "Visa stock",
    "BP":
        "BP stock",
    "HD":
        "Home Depot stock",
    "GE":
        "General Electric stock",
    "CP":
        "Canadian Pacific stock",
    "GS":
        "Goldman Sachs stock",
    "KO":
        "Coca-Cola stock",
    "MU":
        "Micron Technology stock",
    "PG":
        "Procter & Gamble stock",
    "TM":
        "Toyota stock",
    "ZS":
        "Zscaler stock",
    "BX":
        "Blackstone stock",
    "GD":
        "General Dynamics stock",
    "CF":
        "CF Industries stock",
    "COP":
        "ConocoPhillips stock",
    "CAT":
        "Caterpillar stock",
    "COST":
        "Costco stock",
    "PAVE":
        "PAVE ETF stock",
    "AMT":
        "American Tower stock",
    "SO":
        "Southern Company stock",
    "BA":
        "Boeing stock",
    "COIN":
        "Coinbase stock",
    "MA":
        "Mastercard stock",
    "DE":
        "Deere stock",
    "GOLD":
        "Barrick Gold stock",
    "ITA":
        "ITA ETF stock",
    "UPS":
        "UPS stock",
    "VALE":
        "Vale stock",
    "ES":
        "Eversource Energy stock",
    "DD":
        "DuPont stock",
    "F":
        "Ford stock",
    "O":
        "Realty Income stock",
    "A":
        "Agilent stock",
    "NOW":
        "ServiceNow stock",
    "BE":
        "Bloom Energy stock",
    "FAST":
        "Fastenal stock",
    "KEYS":
        "Keysight stock",
    "PLUG":
        "Plug Power stock",
    "NET":
        "Cloudflare stock",
    "PAAS":
        "Pan American Silver stock",
    "APP":
        "AppLovin stock",
    "ALL":
        "Allstate stock",
    "LOW":
        "Lowe's stock",
    "WM":
        "Waste Management stock",
    "D":
        "Dominion Energy stock",
    "HAL":
        "Halliburton stock",

    # News Topic Search Overrides to prevent generic noise in Google News
    "AI":
        '"AI market" OR "Artificial Intelligence industry"',
    "Energy":
        '"Energy sector" OR "Power generation" OR "Electricity grid"',
    "Oil":
        '"Crude oil" OR "Oil prices" OR "Oil market"',
    "Shipping":
        '"Ocean freight shipping" OR "Maritime logistics" OR "Container rates"',
    "Logistics":
        '"Supply chain logistics" OR "Freight logistics"',
    "War":
        '"Military conflict geopolitics" OR "War economy"',
    "Technology":
        '"Tech industry" OR "Big Tech news" OR "Technology stocks"',
    "Iran":
        '"Iran geopolitics" OR "Iran sanctions" OR "Iran oil"',
    "Russia":
        '"Russia geopolitics" OR "Russia sanctions" OR "Russia Ukraine War"',
    "Ukraine":
        '"Ukraine war" OR "Ukraine conflict"',
    "China":
        '"China geopolitics" OR "China economy" OR "China trade"',
    "Taiwan":
        '"Taiwan geopolitics" OR "Taiwan Strait" OR "Taiwan Semiconductor"',
    "United States":
        '"US economy" OR "US macro" OR "United States policy"',
    "Canada":
        '"Canada economy" OR "Canada trade"',
    "Mexico":
        '"Mexico economy" OR "Mexico nearshoring"',
    "Israel":
        '"Israel conflict" OR "Israel geopolitics"',
    "Middle East":
        '"Middle East conflict" OR "Middle East geopolitics"',
    "India":
        '"India economy" OR "India growth" OR "India markets"',
    "Pakistan":
        '"Pakistan economy" OR "Pakistan geopolitics"',
    "Venezuela":
        '"Venezuela oil" OR "Venezuela sanctions"',
    "Drones":
        '"Military drones" OR "Defense drone technology"',
    "Hormuz":
        '"Strait of Hormuz shipping" OR "Hormuz geopolitics"',
    "OPEC":
        '"OPEC oil policy" OR "OPEC+ production"',
    "Uranium":
        '"Uranium prices" OR "Uranium mining"',
    "Natural Gas":
        '"Natural gas prices" OR "LNG exports"',
    "Lithium":
        '"Lithium battery" OR "Lithium prices" OR "Lithium mining"',
    "Rare Earths":
        '"Rare earth metals" OR "Rare earth supply chain"',
    "GDP":
        '"GDP growth" OR "GDP economy"',
    "Recession":
        '"Recession risk" OR "Economic recession"',
    "Inflation":
        '"CPI inflation" OR "Inflation rates"',
    "Interest Rates":
        '"Fed interest rates" OR "Central bank rates"',
    "Tariffs":
        '"Customs tariffs" OR "Trade tariffs"'
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

    # Foreign Exchange & Global Currencies
    "USD_INDEX": "DTWEXBGS",  # U.S. Dollar Broad Index
    "USD_CNY": "DEXCHUS",  # Chinese Yuan to USD Rate
    "USD_EUR": "DEXUSEU",  # USD to Euro Rate
    "USD_JPY": "DEXJPUS",  # Japanese Yen to USD Rate

    # Agriculture, Food Inflation & Commodities
    "FOOD_CPI": "CPIUFDNS",  # CPI for Food & Groceries
    "CORN_PRICE": "PMAIZMTUSDM",  # Global Corn & Grain Price
    "WHEAT_PRICE": "PWHEAMTUSDM",  # Global Wheat Price
    "SUGAR_PRICE": "PSUGAISAUSDM",  # Global Sugar Price

    # Energy Transition & Power Grid Output
    "WTI_CRUDE": "DCOILWTICO",  # Crude Oil Spot Price (WTI)
    "NAT_GAS_PRICE":
        "PNGASUSUSDM",  # US Natural Gas Spot Price (Data Centers/Power)
    "COPPER_PRICE": "PCOPPUSDM",  # Global Copper Price (Grid & Semi Infra)
    "ELECTRIC_POWER_INDEX":
        "IPG22112S",  # Electric Power Generation & Grid Output Index

    # Science, Technology & R&D Innovation
    "RD_INVESTMENT": "Y006RC1Q027SBEA",  # Gross Domestic Investment in R&D

    # Demographics, Health & Population Trends
    "US_BIRTH_RATE": "SPDYNCBRTINUSA",  # Crude Birth Rate (per 1,000 people)
    "LIFE_EXPECTANCY": "SPDYNLE00INUSA",  # Life Expectancy at Birth (Years)
    "US_POPULATION": "POP",  # Total U.S. Population (Thousands)

    # Prosperity, Wealth & Household Financial Health
    "DISPOSABLE_INCOME": "DSPIC96",  # Real Disposable Personal Income
    "HOUSEHOLD_NET_WORTH": "TNWBSHNO",  # U.S. Household & Nonprofit Net Worth
    "CREDIT_CARD_DELINQUENCY":
        "DRCLACBS",  # Credit Card Loan Delinquency Rate (%)

    # Growth, Labor & Consumer Sentiment
    "GDP": "GDP",  # Gross Domestic Product
    "REAL_GDP": "GDPC1",  # Real Gross Domestic Product (Inflation-Adjusted)
    "UNRATE": "UNRATE",  # Unemployment Rate
    "HOUSING_STARTS": "HOUST",  # Housing Starts
    "RECESSION_PROB": "RECPROUSM156N",  # Smoothed Recession Probability
    "UMICH_SENTIMENT": "UMCSENT",  # U. Michigan Consumer Sentiment (From 1952)
    "SAVINGS_RATE": "PSAVERT",  # Personal Saving Rate % (From 1959)

    # Liquidity, Money Supply & Federal Reserve
    "M2_MONEY": "M2SL",  # M2 Money Supply (From 1959)
    "M2_VELOCITY": "M2V",  # Velocity of M2 Money Stock (From 1959)
    "FED_ASSETS": "WALCL",  # Fed Total Assets / Balance Sheet (QE/QT)

    # Inflation, Rates & Long-Term Credit Spreads
    "CPI": "CPIAUCSL",  # Consumer Price Index (All Items)
    "FEDFUNDS": "FEDFUNDS",  # Federal Funds Effective Rate
    "US02Y": "DGS2",  # 2-Year Treasury Yield
    "US10Y": "DGS10",  # 10-Year Treasury Yield
    "US30Y": "DGS30",  # 30-Year Treasury Yield
    "HY_SPREAD": "BAMLH0A0HYM2",  # High Yield Credit Market Stress Spread
    "CORP_SPREAD": "BAMLC0A0CM",  # Corporate Investment Grade Credit Spread
    "BAA_SPREAD": "BAA10Y",  # Moody's Baa Corporate Spread over 10Y (From 1986)
    "AAA_SPREAD": "AAA10Y",  # Moody's Aaa Corporate Spread over 10Y (From 1983)

    # Political Chaos, Geopolitical Risk & Systemic Stress Indices
    "US_POLICY_UNCERTAINTY":
        "USEPUINDXD",  # Daily US Economic Policy & Political Uncertainty
    "EUROPE_POLICY_UNCERTAINTY":
        "EUEPUINDXM",  # European Policy Uncertainty Index
    "GLOBAL_POLICY_UNCERTAINTY":
        "GEPUCURRENT",  # Global Policy & Trade Chaos Index
    "ST_LOUIS_FIN_STRESS":
        "STLFSI4",  # St. Louis Fed Financial Market Stress Index
    "KANSAS_CITY_FIN_STRESS": "KCFSI",  # Kansas City Financial Stress Index
    "CHICAGO_FED_ACTIVITY":
        "CFNAI",  # Chicago Fed Coincident Prosperity/Activity Index
}


def fetch_fred_series(series_id: str,
                      logger: logging.Logger,
                      start_date: Optional[str] = None,
                      limit: Optional[int] = None) -> Optional[pd.DataFrame]:
  """
    Fetches observations for a FRED series using the JSON API if available,
    otherwise falls back to parsing the CSV graph.

    Args:
        series_id: The FRED series ID to query (e.g. 'PCU483111483111').
        logger: A logger instance for warnings and errors.
        start_date: Minimum date to retrieve (YYYY-MM-DD). Used only in JSON API.
        limit: Max observations to retrieve. Used only in JSON API.

    Returns:
        A pandas DataFrame indexed by Date with a single column (series_id) of float values,
        or None if fetching fails completely.
    """
  if config.FRED_API_KEY:
    try:
      url = "https://api.stlouisfed.org/fred/series/observations"
      params: Dict[str, Union[str, int]] = {
          "series_id": series_id,
          "api_key": config.FRED_API_KEY,
          "file_type": "json",
          "sort_order": "asc",
      }
      if start_date:
        params["observation_start"] = start_date
      if limit:
        params["limit"] = limit

      res = requests.get(url, params=params, timeout=15)
      if res.status_code == 200:
        data = res.json().get("observations", [])
        rows = []
        for obs in data:
          val = obs.get("value")
          if val and val != ".":
            try:
              rows.append({
                  "DATE": pd.to_datetime(obs["date"]),
                  series_id: float(val)
              })
            except ValueError:
              pass
        if rows:
          return pd.DataFrame(rows).set_index("DATE")
      else:
        logger.warning(
            f"FRED API error for {series_id}: HTTP {res.status_code} - {res.text}"
        )
    except Exception as e:
      logger.warning(f"Failed to fetch JSON FRED for {series_id}: {e}")

  # Fallback to anonymous CSV scrape if API key missing or failed
  try:
    logger.info(f"Attempting CSV scrape fallback for FRED series: {series_id}")
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    series_df = pd.read_csv(url, index_col=0, parse_dates=True)
    # Note: CSV scrape ignores start_date and limit, it just returns everything.
    if not series_df.empty:
      series_df.index.name = "DATE"
      return series_df
  except Exception as e:
    logger.error(f"Failed to fetch CSV FRED for {series_id}: {e}")

  return None


# Tickers to skip for Earnings/Financials.
# These are typically ETFs, Indices, or Futures which do not share the same
# financial reporting structure as individual companies (e.g. no EPS/Revenue misses).
# yapf: disable
SKIP_EARNINGS: List[str] = [
    # Indices & Volatility
    "^DJI", "^GSPC", "^IXIC", "^RUT", "^TNX", "^VIX", "VIXY",

    # Commodities & Futures
    "CL=F", "GC=F", "NG=F", "CORN", "CURN", "SOYB", "WEAT",

    # Crypto (No SEC Filings)
    "BTC-USD", "ETH-USD", "SOL-USD",

    # Core Vanguard/Broad ETFs
    "VTI", "VOO", "SPY", "VTSAX", "VUG", "VTV", "VEA", "VWO", "VIGAX",
    "SCHD", "SCHG", "SCHV", "VGT", "QQQ", "DIA", "IWM", "EFA", "EEM",
    "URTH", "TLT", "AIPO", "VIG", "VYM", "VIS", "VAW", "VXUS",


    # Vanguard Mutual Funds (Institutional/Admiral Shares - No Form 4)
    "VEMRX", "VFTAX", "VIGIX", "VIIIX", "VMFXX", "VTIFX",

    # Sector & Thematic ETFs
    "SMH", "SOXQ", "IBIT", "GLDM", "PAVE", "ITA", "URA", "NLR", "XLE",
    "VDE", "FENY", "VPU", "FUTY", "VHT", "VDC", "SCHH", "CIBR", "PPH",
    "SOXX", "XSD", "MUZ", "SPCX", "OZEM", "SMHX", "EWY", "FXI", "KWEB",


    # Fixed Income & Preferred
    "PFFD", "PFXF", "FAGOX", "FASPX", "VBIL", "VUSB",

    # Industry-Specific or Foreign Alternatives
    "BDRY", "COPX", "XLU",

    # ADRs / Foreign Listings (Irregular Financials)
    "ASML", "BHP", "GOLD", "HUT", "NEM", "RIO", "TSM",

    # Corporate Exclusions (Missing/Empty Financials)
    "AWX", "BAH", "BB", "NUE", "STRL", "VSAT"
]

# Tickers to skip for Insider Trading (ETFs, Indices, OTC)
SKIP_INSIDER: List[str] = SKIP_EARNINGS + [
    "AMKBY", # OTC/Foreign often lacks CIK mapping
    "PAVE", "ITA", "SMH", "URA", "XLE", "CIBR", "VIG", "VIS", "VYM", # Sector ETFs
    # Foreign / ADRs (No Form 4)
    "ARM", "BMNR", "BP", "CCJ", "CNI", "CP", "PAAS", "SHEL", "TCEHY", "TTE", "TTDKY", "ZIM",
    # Specific Corporate Exclusions (Missing/404 on SEC Edgar or no CIK mapping)
    # Note: Even with CIK overrides, some of these may fail depending on SEC database availability
    "ALB", "AMGN", "AWK", "BSX", "CORZ", "CWCO", "DD", "ESLT", "FLNC", "FRO",
    "LDOS", "LLY", "LMT", "MA", "MATX", "MNDY", "O", "PFE", "PLD", "SMCI", "SO",
    "SQM", "UPS", "V", "VRT", "XYL"
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

  @staticmethod
  async def unwrap_google_news_url(url: str) -> str:
    """Uses curl_cffi to unwrap a Google News RSS URL to the actual destination."""
    if "news.google.com/rss/articles" in url:
      try:
        response = cffi_requests.get(
            url,
            impersonate="chrome",
            timeout=10,
            allow_redirects=True,
            headers={
                "User-Agent":
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            })

        final_url = response.url

        # Google News sometimes uses a client-side JS redirect or meta refresh
        # If the fetched URL is still google.com, parse the HTML
        if "google.com" in final_url:
          try:
            tree = html.fromstring(response.content)
            urls = tree.xpath('//a/@href')
            for u in urls:
              if u.startswith('http') and 'google.com' not in u:
                return u

            # Look for JS redirect
            content_str = response.content.decode('utf-8')
            match = re.search(r'data-n-au="([^"]+)"', content_str)
            if match:
              return match.group(1)
          except Exception:
            pass

        return final_url

      except Exception as e:
        logging.warning("Failed to unwrap Google News URL %s: %s", url, e)
    return url

  @staticmethod
  async def fetch_article_text(url: str,
                               max_paragraphs: int = 20) -> Optional[str]:
    """
    Fetches the content of a URL (unwrapping Google News links if needed) using
    curl_cffi to bypass basic anti-bot protections, and extracts the main paragraph text using lxml.
    """
    actual_url = await MarketFetcher.unwrap_google_news_url(url)
    try:
      response = cffi_requests.get(
          actual_url,
          impersonate="chrome",
          timeout=10,
          headers={
              "User-Agent":
                  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
          })

      if response.status_code != 200:
        return None

      tree = html.fromstring(response.content)
      for bad_element in tree.xpath(
          '//script | //style | //nav | //footer | //header'):
        bad_element.getparent().remove(bad_element)

      paragraphs = tree.xpath('//p/text() | //p/*/text()')
      cleaned_paragraphs = []
      for p in paragraphs:
        text = str(p).strip()
        if text and len(text) > 40:
          cleaned_paragraphs.append(text)

      if not cleaned_paragraphs:
        return None

      return " ".join(cleaned_paragraphs[:max_paragraphs])

    except Exception:
      return None

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

  def _fetch_rss_content(self,
                         url: str,
                         source: str,
                         ticker: str,
                         expiry_seconds: Optional[int] = None) -> Optional[str]:
    """Fetches raw RSS content with caching."""
    # Cache based on source and ticker (URL might change slightly but usually source+ticker is unique enough for feed)
    # We use a hashing of URL to be safe if multiple URLs per source
    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_key = f"rss_raw_{source}_{ticker}_{url_hash}"

    # Use explicit expiry if passed, otherwise default to config
    actual_expiry = expiry_seconds if expiry_seconds is not None else config.CACHE_EXPIRY_NEWS

    content = self._load_cache(cache_key, expiry_seconds=actual_expiry)
    if content:
      return content

    # Add a small random jitter to stagger requests and avoid IP bans
    time.sleep(random.uniform(0.2, 0.8))

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
        if code_elem is None or code_elem.text is None:
          continue
        code = code_elem.text.upper()
        if code not in ['P', 'S']:
          continue

        buy_flag = 1 if code == 'P' else 0
        date_elem = txn.find('.//transactionDate/value', ns)
        date = date_elem.text if date_elem is not None and date_elem.text is not None else ""
        shares_elem = txn.find('.//transactionShares/value', ns)
        price_elem = txn.find('.//transactionPricePerShare/value', ns)

        shares = round(
            float(shares_elem.text), 2
        ) if shares_elem is not None and shares_elem.text is not None else 0.0
        price = round(
            float(price_elem.text), 4
        ) if price_elem is not None and price_elem.text is not None else 0.0
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
        time.sleep(0.5)  # Be polite to SEC Edgar max 10 requests / sec

      except Exception as e:
        self.logger.warning(f"Failed to fetch Insider for {ticker}: {e}")
        # Add a longer sleep if we are likely rate limited, and cache True briefly to backoff
        if "Max retries exceeded" in str(e) or "429" in str(e):
          self.logger.warning(f"Throttled! Backing off for {ticker}.")
          # Temporarily cache to avoid hammering on subsequent retries
          self._save_cache(cache_key, True)
          time.sleep(5.0)

  def _fetch_alphavantage_news(self,
                               ticker: str,
                               limit: int = 50) -> List[Dict[str, Any]]:
    """Fetches News Sentiment using AlphaVantage (Rich Metadata). Returns list of items."""
    if ticker in config.SECTORS.get("Macro Indices",
                                    []) or ticker in config.NEWS_TOPICS:
      return []

    try:
      api_key = self._get_current_api_key() or config.ALPHA_VANTAGE_KEY
      url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&limit={limit}&apikey={api_key}"

      # Cache First
      cache_key = f"av_news_{ticker}"
      data = self._load_cache(cache_key,
                              expiry_seconds=config.CACHE_EXPIRY_AV_NEWS)

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

  def fetch_historical_topic_news(self,
                                  start_date: datetime.date,
                                  end_date: datetime.date,
                                  thorough: bool = False) -> int:
    """
    Fetches historical news for all topics defined in config.NEWS_TOPICS using Google News RSS.
    Chunks the requests into intervals (90 days if thorough, 365 days default) to bypass the 100-result limit.
    """
    total_added = 0
    topics = getattr(config, 'NEWS_TOPICS', [])
    if not topics:
      self.logger.warning("No NEWS_TOPICS defined in config.")
      return 0

    self.logger.info(
        f"Backfilling topic news from {start_date} to {end_date}...")

    # Iterate through each topic
    for topic in tqdm(topics, desc="Historical Topics"):
      topic_added = 0
      # Loop backward in chunks for faster, prioritized recent backfills
      chunk_days = 90 if thorough else 365
      current_end = end_date
      while current_end > start_date:
        current_start = max(current_end - datetime.timedelta(days=chunk_days),
                            start_date)

        start_str = current_start.strftime("%Y-%m-%d")
        end_str = current_end.strftime("%Y-%m-%d")

        safe_topic = urllib.parse.quote(topic)
        url = f"https://news.google.com/rss/search?q={safe_topic}+after:{start_str}+before:{end_str}&hl=en-US&gl=US&ceid=US:en"

        # Calculate dynamic cache expiry:
        # If the end date of the fetch window is before today, we aggressively cache
        # it to prevent spamming Google News RSS on old windows.
        is_historical = current_end < datetime.date.today()
        cache_expiry = config.CACHE_EXPIRY_HISTORICAL_NEWS if is_historical else config.CACHE_EXPIRY_NEWS

        # We reuse the _fetch_rss_content logic to leverage the cache. We pass the raw string url.
        raw_content = self._fetch_rss_content(
            url,
            "Google",
            f"hist_topic_{topic}_{start_str}_{end_str}",
            expiry_seconds=cache_expiry)

        if raw_content:
          feed = feedparser.parse(raw_content)
          items = []
          for entry in feed.entries:
            try:
              dt = pd.to_datetime(entry.published).tz_localize(None)
              title_text = entry.title
              source_text = "Google News"

              if " - " in title_text:
                parts = title_text.rsplit(" - ", 1)
                title_text = parts[0]
                source_text = parts[1]

              items.append({
                  "date":
                      dt,
                  "date_str":
                      dt.strftime('%Y-%m-%d %H:%M:%S'),
                  "source":
                      source_text.strip(),
                  "title":
                      title_text.strip().replace("\t", " ").replace("\n", " "),
                  "link":
                      entry.link,
                  "summary":
                      getattr(entry, "summary",
                              "").replace("\t", " ").replace("\n", " ")
              })
            except Exception as e:
              self.logger.warning(
                  f"Error parsing historical standard feed entry: {e}")

          if items:
            self._save_news_tsv(topic, items)
            topic_added += len(items)
            total_added += len(items)

        # Decrement window
        current_end = current_start - datetime.timedelta(days=1)
        time.sleep(1)  # Polite delay between chunks

      self.logger.info(f"  + {topic_added} items for {topic}")

    return total_added

  def _update_single_ticker_news(self, ticker: str, feeds: Dict[str, str],
                                 limit: int, cutoff: datetime.datetime,
                                 include_alphavantage: bool) -> None:
    """Updates news log for a single ticker (TSV)."""
    ticker_path = self.get_ticker_path(ticker)
    seen_links: Set[str] = set()
    tsv_file = ticker_path / NEWS_FILENAME

    if tsv_file.exists():
      try:
        existing_df = pd.read_csv(tsv_file, sep='\t')
        if 'URL' in existing_df.columns:
          seen_links = set(existing_df['URL'].astype(str))
      except Exception as e:
        self.logger.warning(f"Error reading existing news for {ticker}: {e}")

    cached_fresh = []

    for src_name, url_template in feeds.items():
      try:
        query_term = ticker
        if src_name == "Google" and ticker in TICKER_SEARCH_TERMS:
          query_term = TICKER_SEARCH_TERMS[ticker]

        safe_term = urllib.parse.quote(query_term)
        url = url_template.format(term=safe_term)

        raw_content = self._fetch_rss_content(url, src_name, ticker)
        if not raw_content:
          continue

        feed = feedparser.parse(raw_content)

        for entry in feed.entries[:limit]:
          pub_dt = datetime.datetime.now()
          if hasattr(entry, 'published_parsed') and entry.published_parsed:
            pub_dt = datetime.datetime(*entry.published_parsed[:6])

          if pub_dt < cutoff:
            continue

          entry_link = getattr(entry, 'link', None)
          if entry_link and str(entry_link) in seen_links:
            continue

          summary_text = getattr(entry, 'summary', '').replace('\n',
                                                               ' ').strip()
          if src_name == "Google":
            summary_text = ""
          else:
            summary_text = re.sub(r'<[^>]+>', '', summary_text).strip()[:500]

          # Noise filter for short/ambiguous tickers
          if ticker in TICKER_SEARCH_TERMS:
            text_lower = (entry.title + " " + summary_text).lower()
            fin_kw = [
                'stock', 'shares', 'earnings', 'dividend', 'revenue',
                'quarterly', 'investor', 'nyse', 'nasdaq', 'sec', 'market',
                'valuation', 'profit', 'rating', 'buy', 'sell', 'hold', 'etf',
                'portfolio', 'caterpillar', 'ford', 'realty', 'agilent',
                'servicenow', 'bloom', 'fastenal', 'keysight', 'plug',
                'cloudflare', 'allstate', 'lowe', 'waste management',
                'dominion', 'halliburton', 'applovin'
            ]
            if not any(kw in text_lower for kw in fin_kw):
              continue

          text_for_sentiment = entry.title + " " + summary_text
          sentiment_score = self.get_sentiment_score(text_for_sentiment)

          cached_fresh.append({
              'date': pub_dt,
              'date_str': pub_dt.strftime('%Y-%m-%d'),
              'source': src_name,
              'title': entry.title.replace('\n', ' ').strip(),
              'link': entry.link,
              'sentiment': sentiment_score,
              'summary': summary_text,
          })

      except Exception as e:
        self.logger.warning(
            f"Error processing feed {src_name} for {ticker}: {e}")
        continue

    if include_alphavantage and self._av_keys:
      av_items = self._fetch_alphavantage_news(ticker, limit)
      if av_items:
        cached_fresh.extend(av_items)

    new_unique = []
    for item in cached_fresh:
      link = item.get('link') or item.get('URL')
      if link is not None and link not in seen_links:
        seen_links.add(str(link))
        new_unique.append(item)

    if not new_unique:
      return

    try:
      new_unique.sort(key=lambda x: x.get('date', datetime.datetime.min),
                      reverse=True)
    except Exception as e:
      self.logger.warning(f"Error sorting news items for {ticker}: {e}")

    for item in new_unique:
      if 'sentiment' not in item:
        text_for_score = str(item.get('title', ''))
        if item.get('summary'):
          text_for_score += " " + str(item.get('summary'))
        item['sentiment'] = self.get_sentiment_score(text_for_score)
      if 'summary' not in item:
        item['summary'] = ''

    self._save_news_tsv(ticker, new_unique)

  def _is_ticker_news_cached(self, ticker: str, feeds: Dict[str, str]) -> bool:
    """Checks if the news feeds for a ticker are already cached and fresh."""
    for src_name, url_template in feeds.items():
      query_term = ticker
      if src_name == "Google" and ticker in TICKER_SEARCH_TERMS:
        query_term = TICKER_SEARCH_TERMS[ticker]

      safe_term = urllib.parse.quote(query_term)
      url = url_template.format(term=safe_term)
      url_hash = hashlib.md5(url.encode()).hexdigest()
      cache_key = f"rss_raw_{src_name}_{ticker}_{url_hash}"
      path = self._get_cache_path(cache_key)
      if not path.exists():
        return False
      timestamp = path.stat().st_mtime
      if time.time() - timestamp >= config.CACHE_EXPIRY_NEWS:
        return False
    return True

  def update_news(self,
                  tickers: List[str],
                  feeds: Optional[Dict[str, str]] = None,
                  limit: int = config.DEFAULT_NEWS_LIMIT,
                  days_back: int = config.DEFAULT_NEWS_DAYS,
                  include_alphavantage: bool = False) -> None:
    """Updates news log (TSV, Newest on Top) in parallel."""
    self.logger.info(f"Updating news for {len(tickers)} tickers...")
    if feeds is None:
      feeds = DEFAULT_NEWS_FEEDS

    cutoff = datetime.datetime.now() - datetime.timedelta(days=days_back)

    def _process_ticker(ticker):
      self._update_single_ticker_news(ticker, feeds, limit, cutoff,
                                      include_alphavantage)

    # Separate cached vs uncached tickers to avoid thread/network overhead
    cached_tickers = [
        t for t in tickers if self._is_ticker_news_cached(t, feeds)
    ]
    uncached_tickers = [t for t in tickers if t not in cached_tickers]

    if cached_tickers:
      for t in tqdm(cached_tickers, desc="RSS News (Cached)"):
        _process_ticker(t)

    if uncached_tickers:
      # Safe concurrent worker limit to prevent IP bans/throttling
      with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_process_ticker, t): t for t in uncached_tickers
        }
        for _ in tqdm(as_completed(futures),
                      total=len(futures),
                      desc="RSS News (Fetching)"):
          pass

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

      if ticker in SKIP_EARNINGS:
        for attr in [
            "quarterly_financials", "quarterly_balance_sheet",
            "quarterly_cashflow"
        ]:
          cache_key = f"yf_{attr}_{ticker}"
          if self._load_cache(
              cache_key,
              expiry_seconds=config.CACHE_EXPIRY_FUNDAMENTALS) is None:
            self._save_cache(cache_key, pd.DataFrame())
        continue

      combined_frames = []

      # 1. Fetch Yahoo Finance (Primary)
      try:
        yf_ticker = None

        def get_yf_df(
            attr_name: str,
            yf_t: Optional[yf.Ticker]) -> Tuple[pd.DataFrame, yf.Ticker]:
          cache_key = f"yf_{attr_name}_{ticker}"
          data = self._load_cache(
              cache_key, expiry_seconds=config.CACHE_EXPIRY_FUNDAMENTALS)

          if data is None:
            if yf_t is None:
              yf_t = yf.Ticker(ticker)
            try:
              data = getattr(yf_t, attr_name)
              if data is None:
                data = pd.DataFrame()
              self._save_cache(cache_key, data)
            except Exception:
              self._save_cache(cache_key, pd.DataFrame())
              data = pd.DataFrame()

          return data if data is not None else pd.DataFrame(), yf_t

        # Yahoo returns (Metrics x Date), we want (Date x Metrics) so we Transpose (.T)
        inc, yf_ticker = get_yf_df("quarterly_financials", yf_ticker)
        if not inc.empty:
          combined_frames.append(inc.T)

        bal, yf_ticker = get_yf_df("quarterly_balance_sheet", yf_ticker)
        if not bal.empty:
          combined_frames.append(bal.T)

        cf, yf_ticker = get_yf_df("quarterly_cashflow", yf_ticker)
        if not cf.empty:
          combined_frames.append(cf.T)

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

          cache_key = f"av_{func}_{ticker}"
          data = self._load_cache(
              cache_key, expiry_seconds=config.CACHE_EXPIRY_AV_FINANCIALS)

          if data is None:
            # Simple retry/fetch logic
            max_retries = len(self._av_keys) if self._av_keys else 1
            if max_retries > 5:
              max_retries = 5

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
                  self._save_cache(cache_key, data)
                  break

                # Cache empty responses to prevent repeated useless calls
                self._save_cache(cache_key, [])
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

    # Deduplicate by URL only if URL is present and valid
    # Replace empty string URLs with NaN to prevent dropping all empty-URL rows
    combined['URL'] = combined['URL'].replace('', pd.NA)

    # Identify rows with valid URLs to deduplicate
    valid_url_mask = combined['URL'].notna()

    # Deduplicate the rows with URLs
    if valid_url_mask.any():
      deduped_valid = combined[valid_url_mask].drop_duplicates(subset=['URL'],
                                                               keep='last')
      # Combine back with the rows lacking URLs
      combined = pd.concat([deduped_valid, combined[~valid_url_mask]])

    # Fill NaN URLs back to empty string
    combined['URL'] = combined['URL'].fillna('')

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

    # Reset index to ensure unique integer index for dropping
    df = df.reset_index(drop=True)

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
    scan_limit = min(num_rows, 200)
    window_size = 50  # Increased window size for broader detection

    for i in range(scan_limit):
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

  def estimate_growth_rate(self,
                           eps_quarter_series: pd.Series,
                           lookback_quarters: int = 30) -> float:
    """Estimates annualized earnings growth from quarterly EPS using log-linear regression."""
    eps = eps_quarter_series.dropna()
    eps = eps[eps > 0]
    if len(eps) < 4:
      return np.nan

    eps_recent = eps.tail(lookback_quarters)
    y = np.log(eps_recent.values)
    x = np.arange(len(eps_recent))

    slope, _ = np.polyfit(x, y, 1)

    quarterly_growth = np.exp(slope) - 1
    annual_growth = (1 + quarterly_growth)**4 - 1
    return annual_growth

  def update_fundamentals(self,
                          tickers: List[str],
                          include_alphavantage: bool = False) -> None:
    """Updates fundamentals (TSV Key-Value) & Earnings (TSV). Optional AlphaVantage Overview merge."""
    self.logger.info(
        f"Updating fundamentals (AlphaVantage={include_alphavantage})...")

    for ticker in tqdm(tickers, desc="Fundamentals"):
      ticker_path = self.get_ticker_path(ticker)

      yf_ticker = None

      # 1. Info / Stats
      cache_key = f"fund_{ticker}"
      info = self._load_cache(cache_key,
                              expiry_seconds=config.CACHE_EXPIRY_FUNDAMENTALS)

      if info is None:
        try:
          if yf_ticker is None:
            yf_ticker = yf.Ticker(ticker)
          info = yf_ticker.info
          if info is None:
            info = {}
          self._save_cache(cache_key, info)
        except Exception as e:
          self.logger.warning(f"Failed to fetch info for {ticker}: {e}")
          self._save_cache(cache_key, {})
          info = {}

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
            if pe is not None and gr is not None:
              peg_calc = float(pe) / (float(gr) * 100)
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

            cache_key = f"av_overview_{ticker}"
            overview = self._load_cache(
                cache_key, expiry_seconds=config.CACHE_EXPIRY_AV_OVERVIEW)

            if overview is None:
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
                    self._save_cache(cache_key, overview)
                    break

                  # Missing Symbol or failed lookup
                  self._save_cache(cache_key, {})
                  break
                except:
                  self._get_next_api_key()
                  time.sleep(1)

              # If we exhausted retries (e.g. rate limit), cache empty so we don't stall next run
              if overview is None:
                self._save_cache(cache_key, {})
                overview = {}

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

        # Intrinsic Value Monitor Calculations
        try:
          # 1. Trailing EPS
          eps_ttm = info.get("trailingEps")

          # 2. Growth Estimation (from trailing quarterly earnings)
          # We need to load quarterly EPS temporarily to run the log-linear regression
          growth_rate = None
          earn_key = f"yf_quarterly_financials_{ticker}"
          fin_data = self._load_cache(
              earn_key, expiry_seconds=config.CACHE_EXPIRY_FUNDAMENTALS)

          if fin_data is None:
            if yf_ticker is None:
              yf_ticker = yf.Ticker(ticker)
            try:
              fin_data = yf_ticker.quarterly_financials
              if fin_data is None:
                fin_data = pd.DataFrame()
              self._save_cache(earn_key, fin_data)
            except Exception:
              self._save_cache(earn_key, pd.DataFrame())
              fin_data = pd.DataFrame()

          if fin_data is not None and not fin_data.empty:
            # Basic EPS or Diluted EPS
            eps_row = None
            if "Basic EPS" in fin_data.index:
              eps_row = fin_data.loc["Basic EPS"]
            elif "Diluted EPS" in fin_data.index:
              eps_row = fin_data.loc["Diluted EPS"]

            if eps_row is not None:
              # Need oldest to newest for the formula
              eps_series = eps_row.iloc[::-1].apply(pd.to_numeric,
                                                    errors='coerce')
              growth_rate = self.estimate_growth_rate(eps_series)

          if growth_rate is not None and not np.isnan(growth_rate):
            info["eps_normalized_growth"] = growth_rate

          # 3. Bond Yield (from FRED Macro Data)
          bond_yield = 4.4  # Default fallback Graham yield
          macro_file = self.data_dir / "macro" / MACRO_FILENAME
          if macro_file.exists():
            try:
              macro_df = pd.read_csv(macro_file, sep='\t')
              # US10Y is in the CSV. Get the last valid non-NaN value.
              if "US10Y" in macro_df.columns:
                valid_yields = macro_df["US10Y"].dropna()
                if not valid_yields.empty:
                  bond_yield = valid_yields.iloc[-1]
            except Exception as e:
              self.logger.warning(
                  f"Failed to read bond yield for intrinsic value: {e}")

          # 4. Calculate Graham Intrinsic Value
          if eps_ttm and growth_rate is not None and not np.isnan(growth_rate):
            # Graham Intrinsic Value Equation: Value = EPS * (8.5 + 2 * Growth Rate) * (4.4 / Bond Yield)
            # Growth is expected as an integer percentage in Graham's original formula (e.g. 5 for 5%)
            # We bound growth conservatively
            g_calc = max(0.0, min(
                growth_rate * 100,
                25.0))  # Floor at 0, cap at 25% to prevent absurd valuations

            if eps_ttm > 0:
              intrinsic_value = eps_ttm * (8.5 + 2 * g_calc) * (4.4 /
                                                                bond_yield)
              info["graham_intrinsic_value"] = round(intrinsic_value, 2)

              # Calculate discount
              current_price = info.get("currentPrice") or info.get(
                  "previousClose")
              if current_price and current_price > 0:
                discount = (
                    (intrinsic_value - current_price) / intrinsic_value) * 100
                info["discount_to_intrinsic_value"] = round(discount, 2)

        except Exception as e:
          self.logger.warning(
              f"Failed to calculate Intrinsic Value for {ticker}: {e}")

        sorted_keys = sorted(info.keys())
        with open(ticker_path / FUNDAMENTALS_FILENAME, 'w',
                  encoding='utf-8') as f:
          f.write("Metric\tValue\n")
          for k in sorted_keys:
            val = str(info[k]).replace('\t', ' ').replace('\n', ' ')
            f.write(f"{k}\t{val}\n")

      # 2. Earnings & 3. Financials
      earn_key = f"earn_{ticker}"
      if ticker in SKIP_EARNINGS:
        # Prevent skip logic from bypassing cache writes
        if self._load_cache(
            earn_key, expiry_seconds=config.CACHE_EXPIRY_FUNDAMENTALS) is None:
          self._save_cache(earn_key, pd.DataFrame())
        continue

      try:
        earnings = self._load_cache(
            earn_key, expiry_seconds=config.CACHE_EXPIRY_FUNDAMENTALS)

        if earnings is None:
          try:
            if yf_ticker is None:
              yf_ticker = yf.Ticker(ticker)
            try:
              earnings = yf_ticker.get_earnings_dates(limit=160)
            except Exception:
              # Fallback to standard property if the heavy fetch fails
              earnings = yf_ticker.earnings_dates
            if earnings is None:
              earnings = pd.DataFrame()
            self._save_cache(earn_key, earnings)
          except Exception:
            self._save_cache(earn_key, pd.DataFrame())
            earnings = pd.DataFrame()

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
        series = fetch_fred_series(series_id, self.logger)
        if series is not None:
          self._save_cache(cache_key, series)

      if series is not None and not series.empty:
        series = series.rename(columns={series_id: name})
        if combined_fred.empty:
          combined_fred = series
        else:
          combined_fred = combined_fred.join(series, how='outer')

    if not combined_fred.empty:
      # Forward fill missing lower-frequency data across daily dates
      combined_fred = combined_fred.sort_index().ffill().round(4)
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

    missing_files: dict = {}

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
        expected_files = [PRICES_FILENAME, FUNDAMENTALS_FILENAME]

        if ticker not in SKIP_INSIDER:
          expected_files.append(NEWS_FILENAME)

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
              start = str(dates.min().date())
              end = str(dates.max().date())
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
              example = str(df[col].iloc[-1])
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
            example = str(valid_rows.iloc[-1])

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

  def backup_reports(self) -> None:
    """Creates a compressed ZIP archive of all reports into reports/backups/."""
    try:
      from reports.backup_reports import backup_all_reports
      backup_all_reports()
    except Exception as exc:
      self.logger.warning("Failed to backup reports: %s", exc)


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
  parser.add_argument("--tickers",
                      type=str,
                      help="Comma-separated list of specific tickers to fetch")
  parser.add_argument(
      "--insider-limit",
      type=int,
      default=10,
      help="Max insider filings to fetch (increase for backfill)")
  args = parser.parse_args()

  # Apply Limits
  if args.tickers:
    sorted_tickers = [
        t.strip().upper() for t in args.tickers.split(",") if t.strip()
    ]
    print(f"🎯 FETCHING ONLY SPECIFIC TICKERS: {sorted_tickers}")
    # Skip macro updates when targeted list is requested
    config.NEWS_TOPICS = []
  elif args.limit_tickers:
    print(f"⚠️ LIMITING TICKERS: {args.limit_tickers} (Top alphabetically)")
    sorted_tickers = sorted_tickers[:args.limit_tickers]

  # Pipeline
  start_time = time.time()

  # 1. Macro
  if not args.tickers:
    t0 = time.time()
    fetcher.update_macro()
    print(f"⏱️  [Stage 1/7] Macro updated in {int(time.time() - t0)}s")

  # 2. Prices
  t0 = time.time()
  fetcher.update_prices(sorted_tickers, start_date=config.DEFAULT_START_DATE)
  print(f"⏱️  [Stage 2/7] Prices updated in {int(time.time() - t0)}s")

  # 3. Fundamentals & Earnings
  t0 = time.time()
  fetcher.update_fundamentals(sorted_tickers,
                              include_alphavantage=config.ENABLE_ALPHA_VANTAGE)
  print(f"⏱️  [Stage 3/7] Fundamentals updated in {int(time.time() - t0)}s")

  # 4. Financials (Row-Based)
  t0 = time.time()
  fetcher.update_financials(sorted_tickers,
                            include_alphavantage=config.ENABLE_ALPHA_VANTAGE)
  print(f"⏱️  [Stage 4/7] Financials updated in {int(time.time() - t0)}s")

  # 5. Insider Trading (SEC)
  t0 = time.time()
  fetcher.update_insider_trading(sorted_tickers, limit=args.insider_limit)
  print(f"⏱️  [Stage 5/7] Insider Trading updated in {int(time.time() - t0)}s")

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

  t0 = time.time()
  fetcher.update_news(all_news_targets,
                      limit=args.news_limit,
                      days_back=args.news_days,
                      include_alphavantage=config.ENABLE_ALPHA_VANTAGE)
  print(f"⏱️  [Stage 6/7] News & Sentiment updated in {int(time.time() - t0)}s")

  print("\n✅ All updates complete.")
  print(f"📁 Database: {os.path.abspath(fetcher.data_dir)}")

  # 7. Schema & Stats Report
  t0 = time.time()
  fetcher.generate_data_schema()
  fetcher.generate_data_stats()
  print(f"⏱️  [Stage 7/8] Schema & Stats generated in {int(time.time() - t0)}s")

  # 8. Report Backup Archive
  t0 = time.time()
  fetcher.backup_reports()
  print(f"⏱️  [Stage 8/8] Reports Backup archived in {int(time.time() - t0)}s")

  print(
      f"🏁 Total Market Fetcher execution time: {int(time.time() - start_time)}s"
  )


if __name__ == "__main__":
  main()
