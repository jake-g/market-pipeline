"""Fetches 'political sentiment' (prediction-market odds + approval polls).

Sources (all free and keyless):
  * Polymarket Gamma API: resolves config.POLITICAL_MARKETS events and reads
    current outcome prices.
  * Polymarket CLOB `prices-history`: daily price history for backfill.
  * VoteHub polls API: presidential approval polls, averaged into a 14-day
    rolling approve/disapprove series.

Usage:
  python political_fetcher.py                  # daily incremental update
  python political_fetcher.py --backfill --days 120
"""

import argparse
import datetime
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd
import requests

import config

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_HISTORY_URL = "https://clob.polymarket.com/prices-history"
VOTEHUB_URL = "https://api.votehub.com/polls"
APPROVAL_SUBJECT = "Trump"
APPROVAL_WINDOW_DAYS = 14
MAX_OUTCOMES = 6  # Cap per event (e.g. 128-candidate nominee markets).
ODDS_COLUMNS = [
    "Date", "Key", "Category", "Question", "Outcome", "Prob", "Volume_USD",
    "Source", "Market_Id"
]
MERGE_KEYS = ["Date", "Key", "Outcome"]


class PoliticalFetcher:
  """Fetches political prediction-market odds and approval polls to TSV.

  Attributes:
      out_dir: Output directory (market_data/political).
      odds_file: Long-format odds TSV path.
      events_file: Key-events calendar TSV path.
      cache_dir: joblib cache directory.
      logger: Module logger.
  """

  def __init__(self,
               data_dir: str = config.MARKET_DATA_DIR,
               cache_dir: str = config.CACHE_DIR):
    """Initializes output and cache directories.

    Args:
        data_dir: Base directory for outputs.
        cache_dir: Base directory for the joblib cache.
    """
    self.out_dir = Path(data_dir) / "political"
    self.out_dir.mkdir(parents=True, exist_ok=True)
    self.odds_file = self.out_dir / "political_odds.tsv"
    self.events_file = self.out_dir / "political_events.tsv"
    self.cache_dir = Path(cache_dir) / "political"
    self.cache_dir.mkdir(parents=True, exist_ok=True)
    self.logger = logging.getLogger(self.__class__.__name__)

  # ---------------------------------------------------------------- caching
  def _cache_path(self, cache_key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in cache_key)
    return self.cache_dir / f"{safe}.joblib"

  def _load_cache(self, cache_key: str, expiry_seconds: int) -> Optional[Any]:
    path = self._cache_path(cache_key)
    if path.exists() and time.time() - path.stat().st_mtime < expiry_seconds:
      try:
        return joblib.load(path)
      except Exception as e:  # pylint: disable=broad-except
        self.logger.warning("Failed to load cache %s: %s", cache_key, e)
    return None

  def _save_cache(self, cache_key: str, data: Any) -> None:
    try:
      joblib.dump(data, self._cache_path(cache_key))
    except Exception as e:  # pylint: disable=broad-except
      self.logger.warning("Failed to save cache %s: %s", cache_key, e)

  def _get_json(self,
                url: str,
                params: Dict[str, Any],
                cache_key: str,
                expiry: int = config.CACHE_EXPIRY_POLITICAL) -> Optional[Any]:
    """GETs JSON with disk caching; returns None on any HTTP/parse error."""
    cached = self._load_cache(cache_key, expiry)
    if cached is not None:
      return cached
    try:
      resp = requests.get(url,
                          params=params,
                          timeout=20,
                          headers={"User-Agent": config.HTTP_USER_AGENT})
      resp.raise_for_status()
      data = resp.json()
    except (requests.RequestException, ValueError) as e:
      self.logger.warning("Request failed %s %s: %s", url, params, e)
      return None
    self._save_cache(cache_key, data)
    return data

  # ------------------------------------------------------------- polymarket
  def resolve_event(self, entry: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Resolves a config entry to a Gamma event (by slug, else by search).

    Args:
        entry: A config.POLITICAL_MARKETS dict.

    Returns:
        The Gamma event JSON (with embedded `markets`) or None if not found.
    """
    query = entry["slug_or_query"]
    key = entry["key"]
    if " " not in query:
      events = self._get_json(f"{GAMMA_URL}/events", {"slug": query},
                              f"event_{query}")
      if events:
        return events[0]
      self.logger.warning("[%s] slug '%s' not found; trying search", key, query)
    found = self._get_json(f"{GAMMA_URL}/public-search", {
        "q": query,
        "limit_per_type": 5,
        "events_status": "active"
    }, f"search_{query}")
    events = (found or {}).get("events") or []
    events = [e for e in events if not e.get("closed")]
    if not events:
      self.logger.error("[%s] NO MARKET FOUND for '%s'; skipping", key, query)
      return None
    best = max(events, key=lambda e: float(e.get("volume") or 0))
    self.logger.info("[%s] search '%s' -> '%s'", key, query, best.get("slug"))
    return best

  @staticmethod
  def parse_event_markets(event: Dict[str, Any], key: str,
                          category: str) -> List[Dict[str, Any]]:
    """Flattens a Gamma event into one row per outcome (Yes-price of each).

    Args:
        event: Gamma event JSON with embedded `markets`.
        key: Config key for this event.
        category: Config category for this event.

    Returns:
        Rows with Key, Category, Question, Outcome, Prob, Volume_USD,
        Market_Id and Token_Id (Yes-side CLOB token for history lookups).
    """
    rows = []
    for m in event.get("markets", []):
      if m.get("closed"):
        continue  # Resolved sub-market (e.g. a past date bucket).
      try:
        prices = [float(p) for p in json.loads(m["outcomePrices"] or "")]
        tokens = json.loads(m.get("clobTokenIds") or "[]")
        outcomes = json.loads(m.get("outcomes") or '["Yes", "No"]')
      except (KeyError, ValueError, TypeError):
        continue
      if not prices or not tokens:
        continue
      yes_idx = outcomes.index("Yes") if "Yes" in outcomes else 0
      rows.append({
          "Key":
              key,
          "Category":
              category,
          "Question":
              event.get("title") or m.get("question"),
          "Outcome":
              m.get("groupItemTitle") or m.get("question"),
          "Prob":
              round(prices[yes_idx], 4),
          "Volume_USD":
              round(float(m.get("volumeNum") or m.get("volume") or 0)),
          "Source":
              "polymarket",
          "Market_Id":
              str(m.get("id")),
          "Token_Id":
              str(tokens[yes_idx]),
      })
    if len(rows) == 1:  # Plain binary market: label the Yes side.
      rows[0]["Outcome"] = "Yes"
    rows.sort(key=lambda r: (-r["Prob"], -r["Volume_USD"]))
    return rows[:MAX_OUTCOMES]

  @staticmethod
  def parse_price_history(payload: Optional[Dict[str, Any]],
                          start_date: str) -> Dict[str, float]:
    """Converts CLOB history to {YYYY-MM-DD: last price of that local day}.

    Args:
        payload: `{"history": [{"t": epoch_seconds, "p": price}, ...]}`.
        start_date: Inclusive lower bound (YYYY-MM-DD).

    Returns:
        Mapping of date string to probability, filtered to >= start_date.
    """
    daily: Dict[str, float] = {}
    for pt in (payload or {}).get("history", []):
      try:
        day = datetime.datetime.fromtimestamp(int(pt["t"])).strftime("%Y-%m-%d")
        price = float(pt["p"])
      except (KeyError, TypeError, ValueError):
        continue
      if day >= start_date:
        daily[day] = round(price, 4)  # Points are ascending; keep last.
    return daily

  def fetch_odds(self, backfill: bool = False, days: int = 120) -> pd.DataFrame:
    """Fetches current odds for all configured markets (plus history).

    Args:
        backfill: If True also pull daily CLOB history for `days` days.
        days: History window for backfill.

    Returns:
        Long-format DataFrame with ODDS_COLUMNS.
    """
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    start = (today - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    rows: List[Dict[str, Any]] = []
    for entry in config.POLITICAL_MARKETS:
      event = self.resolve_event(entry)
      if event is None:
        continue
      markets = self.parse_event_markets(event, entry["key"], entry["category"])
      if not markets:
        self.logger.warning("[%s] event has no priced markets", entry["key"])
      for m in markets:
        token = m.pop("Token_Id")
        rows.append({"Date": today_str, **m})
        if not backfill:
          continue
        hist = self._get_json(CLOB_HISTORY_URL, {
            "market": token,
            "interval": "max",
            "fidelity": 1440
        }, f"hist_{token}_{today_str}")
        for day, prob in self.parse_price_history(hist, start).items():
          if day != today_str:
            rows.append({"Date": day, **m, "Prob": prob})
      self.logger.info(
          "[%s] %d outcomes: %s", entry["key"], len(markets),
          ", ".join(f"{m['Outcome']}={m['Prob']:.0%}" for m in markets[:4]))
    return pd.DataFrame(rows, columns=ODDS_COLUMNS)

  # --------------------------------------------------------------- approval
  @staticmethod
  def parse_approval_polls(polls: List[Dict[str, Any]],
                           start_date: str) -> pd.DataFrame:
    """Averages VoteHub approval polls into a daily rolling series.

    Args:
        polls: VoteHub poll objects (`end_date`, `answers[{choice, pct}]`).
        start_date: Inclusive lower bound for emitted rows.

    Returns:
        Long-format DataFrame (ODDS_COLUMNS) with Approve/Disapprove rows.
    """
    recs = []
    for p in polls:
      for a in p.get("answers", []):
        if a.get("choice") in ("Approve", "Disapprove"):
          recs.append((p["end_date"], a["choice"], float(a["pct"]) / 100))
    if not recs:
      return pd.DataFrame(columns=ODDS_COLUMNS)
    df = pd.DataFrame(recs, columns=["Date", "Outcome", "Prob"])
    df["Date"] = pd.to_datetime(df["Date"])
    daily = df.groupby(["Outcome", "Date"])["Prob"].mean().unstack(0)
    daily = daily.asfreq("D").rolling(f"{APPROVAL_WINDOW_DAYS}D",
                                      min_periods=1).mean().dropna()
    out = daily.stack().reset_index()
    out.columns = ["Date", "Outcome", "Prob"]
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
    out = out[out["Date"] >= start_date].copy()
    out["Prob"] = out["Prob"].round(4)
    out["Key"] = "approval_trump"
    out["Category"] = "approval"
    out["Question"] = (f"Trump job approval ({APPROVAL_WINDOW_DAYS}d poll "
                       "average, VoteHub)")
    out["Volume_USD"] = len(polls)
    out["Source"] = "votehub"
    out["Market_Id"] = f"votehub:approval:{APPROVAL_SUBJECT}"
    return out[ODDS_COLUMNS]

  def fetch_approval(self, days: int) -> pd.DataFrame:
    """Fetches approval polls and returns the last `days` of daily averages."""
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    polls = self._get_json(VOTEHUB_URL, {
        "poll_type": "approval",
        "subject": APPROVAL_SUBJECT
    }, f"votehub_{today:%Y%m%d}")
    if not polls:
      self.logger.warning("VoteHub approval polls unavailable")
      return pd.DataFrame(columns=ODDS_COLUMNS)
    return self.parse_approval_polls(polls, start)

  # ------------------------------------------------------------------ output
  @staticmethod
  def merge_odds(existing: Optional[pd.DataFrame],
                 new: pd.DataFrame) -> pd.DataFrame:
    """Merges new rows into existing, deduping on (Date, Key, Outcome)."""
    frames = [f for f in (existing, new) if f is not None and not f.empty]
    if not frames:
      return pd.DataFrame(columns=ODDS_COLUMNS)
    merged = pd.concat(frames, ignore_index=True)[ODDS_COLUMNS]
    merged = merged.drop_duplicates(subset=MERGE_KEYS, keep="last")
    return merged.sort_values(["Date", "Key", "Outcome"],
                              ascending=[False, True,
                                         True]).reset_index(drop=True)

  def write_events(self) -> None:
    """Writes the hand-maintained key-events calendar from config."""
    df = pd.DataFrame(config.POLITICAL_EVENTS,
                      columns=["Date", "Event", "Category", "Notes"])
    df.sort_values("Date").to_csv(self.events_file, sep="\t", index=False)

  def run(self, backfill: bool = False, days: int = 120) -> pd.DataFrame:
    """Runs the full fetch and merges into political_odds.tsv.

    Args:
        backfill: Pull daily CLOB history instead of just today's prices.
        days: Lookback window (backfill) / approval refresh window (daily).

    Returns:
        The merged odds DataFrame that was written.
    """
    approval_days = days if backfill else 30
    new = pd.concat(
        [self.fetch_odds(backfill, days),
         self.fetch_approval(approval_days)],
        ignore_index=True)
    existing = None
    if self.odds_file.exists():
      existing = pd.read_csv(self.odds_file, sep="\t")
    merged = self.merge_odds(existing, new)
    merged.to_csv(self.odds_file, sep="\t", index=False)
    self.write_events()
    self.logger.info("Wrote %d rows (%d fetched) to %s", len(merged), len(new),
                     self.odds_file)
    return merged


def main() -> None:
  """CLI entrypoint."""
  logging.basicConfig(
      level=logging.INFO,
      format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
  parser = argparse.ArgumentParser(description="Fetch political sentiment")
  parser.add_argument("--backfill",
                      action="store_true",
                      help="Pull daily price history via Polymarket CLOB")
  parser.add_argument("--days",
                      type=int,
                      default=120,
                      help="Backfill lookback window in days")
  args = parser.parse_args()
  t0 = time.time()
  PoliticalFetcher().run(backfill=args.backfill, days=args.days)
  logging.getLogger(__name__).info("Political fetcher finished in %ds",
                                   int(time.time() - t0))


if __name__ == "__main__":
  main()
