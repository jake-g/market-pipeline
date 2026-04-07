import glob
import logging
import os
import sys
import time
from typing import Any, Dict

import numpy as np
import pandas as pd

# Add the project root to sys.path so 'config' can be resolved
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

import config
from reports.report_utils import enrich_portfolio_df

logger = logging.getLogger(__name__)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

DATA_DIR = os.path.join(project_root, "market_data")
TICKERS_DIR = os.path.join(DATA_DIR, "tickers")


def process_portfolio(tsv_path: str) -> pd.DataFrame:
  """
    Loads a static portfolio TSV, computes live market technicals for each asset,
    and returns a fully enriched DataFrame containing momentum and weights.
    """
  logger.info(f"Processing Portfolio: {tsv_path}")
  if os.path.exists(tsv_path):
    age_days = (time.time() - os.path.getmtime(tsv_path)) / 86400
    if age_days > config.MAX_PORTFOLIO_AGE_DAYS:
      logger.error(
          f"Portfolio file {tsv_path} is stale: {age_days:.1f} days old (Max is {config.MAX_PORTFOLIO_AGE_DAYS} days). failing standalone stand."
      )
      raise ValueError(
          f"Stale portfolio data File exceeds {config.MAX_PORTFOLIO_AGE_DAYS} days filter limit threshold triggering crash."
      )

  try:
    portfolio_df = pd.read_csv(tsv_path, sep='\t')
  except FileNotFoundError:
    logger.error(f"Portfolio file not found: {tsv_path}")
    return pd.DataFrame()

  if portfolio_df.empty:
    return portfolio_df

  # Safety: Infer missing basic accounting columns if Vanguard export drops them
  if 'Cost_Basis' not in portfolio_df.columns:
    if 'Unrealized_PnL_Net' in portfolio_df.columns:
      portfolio_df['Cost_Basis'] = portfolio_df['Current_Value'] - portfolio_df[
          'Unrealized_PnL_Net']
    else:
      portfolio_df['Cost_Basis'] = portfolio_df['Current_Value']  # Assume 0 PnL

  if 'Name' not in portfolio_df.columns:
    portfolio_df['Name'] = portfolio_df['Ticker']

  portfolio_df['Unrealized_PnL_Net'] = portfolio_df[
      'Current_Value'] - portfolio_df['Cost_Basis']
  portfolio_df['Unrealized_PnL_Pct'] = (
      portfolio_df['Unrealized_PnL_Net'] /
      portfolio_df['Cost_Basis'].replace(0, 1)) * 100
  portfolio_df['Custom_Current_Price'] = portfolio_df[
      'Current_Value'] / portfolio_df['Quantity']

  # Total account value for weighting
  total_val = portfolio_df['Current_Value'].sum()

  full_df = enrich_portfolio_df(portfolio_df, DATA_DIR)

  # Resolve pricing columns (enrich_portfolio_df auto-resolves x/y collisions)
  if 'Current_Price' in full_df.columns:
    full_df['Current_Price'] = full_df['Current_Price'].fillna(
        full_df['Custom_Current_Price'])
  else:
    full_df['Current_Price'] = full_df['Custom_Current_Price']

  # Add Portfolio Allocation Weight
  full_df['Portfolio_Weight_Pct'] = (full_df['Current_Value'] / total_val) * 100

  # Add Dynamic Sell Indicators & Time Horizons based on technicals
  horizons = []
  strategies = []
  for _, row in full_df.iterrows():
    if row.get('Ticker') == 'CASH':
      horizons.append("Liquid Reserve")
      strategies.append("Hold for rotational deployment")
      continue

    rsi = row.get('RSI')
    dist_200 = row.get('Dist_to_200MA', 0)
    pnl = row.get('Unrealized_PnL_Pct', 0)

    if pd.notna(rsi) and pd.notna(dist_200) and rsi > 70 and dist_200 > 30:
      horizons.append("Short-Term Trim")
      strategies.append(
          "Trim 15-20% on next gap up; trailing 5% stop to protect profit")
    elif pd.notna(pnl) and pnl < -30:
      horizons.append("Long-Term Hold / Tax Loss")
      strategies.append(
          "Harvest tactical tax loss on rally, or hold for multi-year narrative"
      )
    elif pd.notna(dist_200) and dist_200 < -10:
      horizons.append("Mid-to-Long Hold")
      strategies.append(
          "Accumulate lightly on weakness; Cut entirely if weekly confirms breakdown"
      )
    elif pd.notna(rsi) and rsi < 40:
      horizons.append("Short-Term Accumulate")
      strategies.append(
          "Wait for RSI > 50 momentum shift to add; exit if relative lows fail")
    else:
      horizons.append("Long-Term Core")
      strategies.append(
          "Maintain core weighting; look to trim ~10% if RSI extends > 80")

  full_df['Time_Horizon'] = horizons
  full_df['Exit_Strategy'] = strategies

  # Round float columns to 2 decimals (or 4 for Quantity) to clean up TSV
  float_cols = full_df.select_dtypes(include=['float64', 'float32']).columns
  for col in float_cols:
    if col == 'Quantity':
      full_df[col] = full_df[col].round(4)
    else:
      full_df[col] = full_df[col].round(2)

  return full_df


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  logger.info("Starting Portfolio Batch Processor Engine...")

  portfolios_dir = os.path.dirname(os.path.abspath(__file__))
  tsvs_dir = os.path.join(portfolios_dir, "tsvs")
  logger.info(f"Scanning for portfolios in: {tsvs_dir}")
  tsv_files = glob.glob(os.path.join(tsvs_dir, "*.tsv"))
  # Only process raw portfolio TSVs and the combined active portfolio (ignore other prefixed system TSVs or examples)
  target_files = [
      f for f in tsv_files if "example" not in os.path.basename(f).lower()
  ]

  if not target_files:
    logger.warning("No portfolio TSVs found to process.")
    sys.exit(0)

  logger.info(f"Found {len(target_files)} portfolios to process.")

  for filepath in target_files:
    base_name = os.path.basename(filepath)
    output_path = filepath

    logger.info(f"Running processor on: {base_name}")
    enriched_df = process_portfolio(filepath)

    if enriched_df is not None and not enriched_df.empty:
      # Overwrite the original TSV with the appended metrics columns
      enriched_df.to_csv(output_path, sep='\t', index=False)
      logger.info(f"Successfully appended metrics and saved: {base_name}")
    else:
      logger.error(
          f"Failed to process or returned empty dataframe for: {base_name}")

  logger.info("Batch Processing Complete.")
