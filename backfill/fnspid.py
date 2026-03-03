import argparse
import logging
from pathlib import Path

import config
from market_fetcher import MarketFetcher

# FNSPID Backfill Settings
FNSPID_START_DATE = "2010-01-01"
FNSPID_END_DATE = "2020-06-11"  # Strict cutoff based on audit

# FNSPID Backfill Aliases (Old Ticker -> New Ticker)
# Used to map historical tickers in FNSPID to current tickers
FNSPID_MAPPING = {
    "FB": "META",
    "RDS.A": "SHEL",
    "RDS.B": "SHEL",
    "TOT": "TTE",
    "ACIC": "ACHR",
    "HEAR": "ACHR",
    "GOOGL": "GOOG",  # Prefer GOOG (Class C) over GOOGL (Class A)
    "HDSN": "HDSN",  # Keep as is
}


def main():
  parser = argparse.ArgumentParser(
      description="Backfill historical Benzinga news via FNSPID")
  parser.add_argument(
      "--audit",
      action="store_true",
      help="Audit the FNSPID dataset stats instead of backfilling")
  parser.add_argument("--limit",
                      type=int,
                      default=None,
                      help="Limit rows to scan/backfill")
  parser.add_argument(
      "--start-year",
      type=int,
      default=None,
      help="Start year for backfill (default: config.DEFAULT_START_DATE year)")
  parser.add_argument("--verify",
                      action="store_true",
                      help="Verify data integrity after backfill")
  args = parser.parse_args()

  # Note on FNSPID Dataset:
  # - Dates: ~2010 to June 2020 (Strict Cutoff)
  # - Content: Benzinga News (Summary/Headlines)
  # - Coverage: High for major US tickers
  # - Gap: 2020-2025 is missing (Use other sources)

  # Configure Logging
  logging.basicConfig(level=logging.INFO, format='%(message)s')
  logger = logging.getLogger(__name__)

  # Suppress noisy library logs via their native APIs
  try:
    import datasets
    import huggingface_hub
    datasets.logging.set_verbosity_error()
    huggingface_hub.logging.set_verbosity_error()
  except ImportError:
    logger.warning(
        "⚠️  'datasets' library not found. Backfill will be skipped.")
    return

  # Suppress other loggers
  for lib in ["urllib3", "requests", "fsspec", "httpx", "httpcore", "filelock"]:
    logging.getLogger(lib).setLevel(logging.WARNING)

  if args.audit:
    audit_fnspid(logger, limit=args.limit)
    return

  logger.info("📚 Starting Historical News Backfill (FNSPID)...")
  # Determine Start Year
  if args.start_year:
    start_year = args.start_year
  else:
    try:
      start_year = int(config.DEFAULT_START_DATE.split("-")[0])
    except Exception:
      start_year = 2020

  logger.info(f"   Target Start Year: {start_year}")

  # Check for early exit (Strictly < 2020 as per user request to avoid overlap/unnecessary fetches)
  if start_year >= 2020:
    logger.warning(
        f"⚠️  Skipping Backfill: Start Year {start_year} >= 2020 (FNSPID data ends ~June 2020)."
    )
    return

  if args.limit:
    logger.info(f"   Limit: {args.limit} rows")

  fetcher = MarketFetcher()

  # Get all tickers
  all_tickers = set()
  for sector, tickers in config.SECTORS.items():
    all_tickers.update(tickers)
  sorted_tickers = sorted(list(all_tickers))

  logger.info(f"   Targets: {len(sorted_tickers)} tickers")

  # Run Backfill
  backfill_benzinga_history(fetcher,
                            sorted_tickers,
                            start_year=start_year,
                            max_rows=args.limit)

  logger.info("\n✅ Backfill complete.")

  fetcher.generate_data_stats()

  if args.verify:
    logger.info("\n🧪 Verifying data integrity...")
    # Check AAPL or known ticker
    test_ticker = "AAPL"
    ticker_path = fetcher.get_ticker_path(test_ticker)
    news_file = ticker_path / "news.tsv"

    if not news_file.exists():
      logger.error(f"   ❌ {test_ticker} news file not found!")
      return

    import pandas as pd
    try:
      df = pd.read_csv(news_file, sep='\t')
      benzinga_count = 0
      publisher_found = False

      for index, row in df.iterrows():
        source = str(row.get('Source', ''))
        if "Benzinga" in source:
          benzinga_count += 1
          if "(" in source and ")" in source:
            publisher_found = True
    except Exception as e:
      logger.error(f"   ❌ Error reading news.tsv: {e}")
      return

    logger.info(f"   🔍 Found {benzinga_count} Benzinga items for {test_ticker}")
    if publisher_found:
      logger.info(
          "   ✅ Publisher attribution detected (e.g., 'Benzinga (Name)').")
    else:
      logger.warning(
          "   ⚠️ No specific Publisher attribution found in sampled lines.")

    if benzinga_count > 0:
      logger.info("   ✅ Verification PASSED.")
    else:
      logger.warning(
          "   ⚠️ Verification inconclusive (no Benzinga items found in sample)."
      )


def backfill_benzinga_history(fetcher, tickers, start_year=2018, max_rows=None):
  """
    Backfills historical Benzinga news using the FNSPID dataset.
    MOVED from MarketFetcher to decouple dependencies.
    """
  logger = logging.getLogger(__name__)
  logger.info(
      f"Backfilling Benzinga history from FNSPID dataset (Start: {start_year})..."
  )
  logger.warning(
      "NOTE: FNSPID dataset ends in June 2020. Data from 2020-2025 will be missing."
  )

  try:
    try:
      from datasets import load_dataset
    except ImportError:
      logger.error(
          "datasets library not found. Please run: pip install datasets")
      return

    ds = load_dataset("Zihan1004/FNSPID", split="train", streaming=True)

    target_set = set(tickers)
    # Use local mappings instead of config
    fnspid_map = FNSPID_MAPPING

    interest_map = {t: t for t in target_set}
    for old, new in fnspid_map.items():
      if new in target_set:
        interest_map[old] = new

    buffer = {}

    # Use tqdm for progress
    from tqdm import tqdm
    iterator = tqdm(ds, total=max_rows, desc="   Scanning FNSPID", unit="rows")

    for i, row in enumerate(iterator):
      if max_rows and i >= max_rows:
        break

      date_str = str(row.get('Date', ''))
      try:
        row_year = int(date_str[:4])
        if row_year < start_year:
          continue
      except ValueError:
        continue

      symbol = row.get('Stock_symbol')
      if symbol in interest_map:
        target_ticker = interest_map[symbol]
        publisher = row.get('Publisher')
        source_label = f"Benzinga ({publisher})" if publisher else "Benzinga"

        # Try to get a summary
        summary = row.get('Lsa_summary') or row.get('Textrank_summary') or \
                  row.get('Article') or ''
        if summary and len(str(summary)) > 500:
          summary = str(summary)[:497] + '...'

        item = {
            'date_str':
                date_str[:10],
            'source':
                source_label,
            'title':
                row.get('Article_title', ''),
            'link':
                row.get('Url', ''),
            'sentiment':
                MarketFetcher.get_sentiment_score(row.get('Article_title', '')),
            'summary':
                str(summary).replace('\n', ' ').strip()
        }

        if target_ticker not in buffer:
          buffer[target_ticker] = []
        buffer[target_ticker].append(item)

    for ticker, items in buffer.items():
      # Use fetcher's internal save method to handle deduplication and file I/O
      fetcher._save_news_tsv(ticker, items)
      logger.info(f"Backfilled {len(items)} items for {ticker}")

  except Exception as e:
    logger.error(f"FNSPID backfill failed: {e}")


def audit_fnspid(logger, limit=None):
  from collections import Counter
  import datetime
  import os

  from datasets import load_dataset
  from tqdm import tqdm

  logger.info("🔍 Auditing FNSPID Backfill Source (Zihan1004/FNSPID)...")

  # Interest Set
  interest_tickers = set()
  for sector, tickers in config.SECTORS.items():
    interest_tickers.update(tickers)

  logger.info(f"   Target Tickers: {len(interest_tickers)}")

  try:
    ds = load_dataset("Zihan1004/FNSPID", split="train", streaming=True)

    stats = {
        "total_rows": 0,
        "relevant_rows": 0,
        "publishers": Counter(),
        "tickers": Counter(),
        "max_year": 0,
        "min_year": 9999,
        "max_date": "",
        "min_date": "9999-99-99",
        "has_url": 0,
        "has_summary": 0
    }

    # Sampling limits - Doubled to 1M as requested, or use provided limit
    MAX_SCAN = limit if limit else 1_000_000

    iterator = tqdm(ds, desc="   Scanning Stream", total=MAX_SCAN, unit="rows")

    for i, row in enumerate(iterator):
      if i >= MAX_SCAN:
        break

      stats["total_rows"] += 1

      ticker = row.get('Stock_symbol')
      # Use local mapping
      if ticker in FNSPID_MAPPING:
        ticker = FNSPID_MAPPING[ticker]

      if ticker in interest_tickers:
        stats["relevant_rows"] += 1
        stats["tickers"][ticker] += 1
        stats["publishers"][row.get('Publisher', 'Unknown')] += 1

        if row.get('Url'):
          stats['has_url'] += 1
        if row.get('Lsa_summary') or row.get('Textrank_summary'):
          stats['has_summary'] += 1

        date_str = str(row.get('Date', ''))[:10]
        if date_str:
          if date_str > stats["max_date"]:
            stats["max_date"] = date_str
          if date_str < stats["min_date"]:
            stats["min_date"] = date_str

    # Generate Report
    report = []
    report.append("# Backfill Audit: FNSPID")
    report.append(
        f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # Concise Summary
    rel_pct = (stats['relevant_rows'] /
               stats['total_rows']) * 100 if stats['total_rows'] > 0 else 0
    report.append("## Summary")
    report.append(f"- **Range**: {stats['min_date']} to {stats['max_date']}")
    report.append(
        f"- **Scan**: {stats['total_rows']:,} rows (Coverage: {rel_pct:.1f}%)")
    report.append(f"- **Publishers**: {len(stats['publishers'])} found")
    report.append(f"- **Tickers**: {len(stats['tickers'])} found\n")

    report.append("## 1. Global Metrics")
    if stats['relevant_rows'] > 0:
      report.append(
          f"- **URL Coverage**: {(stats['has_url']/stats['relevant_rows'])*100:.1f}%"
      )
      report.append(
          f"- **Summary Coverage**: {(stats['has_summary']/stats['relevant_rows'])*100:.1f}%\n"
      )

    report.append("## 2. Top Tickers")
    report.append("| Ticker | Count |")
    report.append("|---|---|")
    for t, c in stats["tickers"].most_common(15):
      report.append(f"| {t} | {c:,} |")
    report.append("")

    report.append("## 3. Top Publishers")
    report.append("| Publisher | Count |")
    report.append("|---|---|")
    for p, c in stats["publishers"].most_common(10):
      report.append(f"| {p} | {c:,} |")

    # Save to backfill_stats/FNSPID_STATS.md
    output_path = Path(config.DATA_DIR) / "backfill_stats" / "FNSPID_STATS.md"
    output_path.parent.mkdir(exist_ok=True, parents=True)

    with open(output_path, "w") as f:
      f.write("\n".join(report))

    logger.info(f"\n✅ Audit Complete. Stats saved to {output_path}")
    logger.info(f"   Range: {stats['min_date']} -> {stats['max_date']}")

  except Exception as e:
    logger.error(f"Audit failed: {e}")


if __name__ == "__main__":
  main()
