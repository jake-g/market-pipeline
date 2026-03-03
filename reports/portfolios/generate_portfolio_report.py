from datetime import datetime
import glob
import logging
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Append project root to import config
PORTFOLIOS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(PORTFOLIOS_DIR, "..", ".."))
sys.path.append(PROJECT_ROOT)
import config
from reports.portfolios.yahoo_portfolio_fetcher import load_env_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PLOTS_DIR = os.path.join(PORTFOLIOS_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

env_path = os.path.join(PORTFOLIOS_DIR, ".env")
load_env_file(env_path)

env_active = os.environ.get("ACTIVE_TRADING_PORTFOLIOS", "")
if env_active:
  ACTIVE_TRADING_PORTFOLIOS = [
      p.strip() for p in env_active.split(",") if p.strip()
  ]
else:
  logger.warning(
      "ACTIVE_TRADING_PORTFOLIOS not found in .env. Falling back to empty list."
  )
  ACTIVE_TRADING_PORTFOLIOS = []


def map_sectors(df: pd.DataFrame) -> pd.DataFrame:
  """Maps tickers to their sector defined in config.py."""
  if df.empty or 'Ticker' not in df.columns:
    return df

  sector_map = {}
  for sector, tickers_list in config.SECTORS.items():
    for t in tickers_list:
      sector_map[t] = sector

  df['Sector'] = df['Ticker'].map(
      lambda x: sector_map.get(x, 'Other/Untracked'))
  return df


def create_pie_chart(df: pd.DataFrame,
                     label_col: str,
                     value_col: str,
                     title: str,
                     filename: str,
                     top_n: int = 15):  # pylint: disable=too-many-positional-arguments
  """Utility to generate a pie chart and save to plots dir."""
  if df.empty or df[value_col].sum() <= 0:
    return None

  df_copy = df[df[value_col] > 0].copy()
  df_copy = df_copy.sort_values(by=value_col, ascending=False)

  if len(df_copy) > top_n:
    top_holdings = df_copy.head(top_n)
    other_value = df_copy.iloc[top_n:][value_col].sum()
    other_row = pd.DataFrame([{label_col: "Other", value_col: other_value}])
    plot_df = pd.concat([top_holdings, other_row], ignore_index=True)
  else:
    plot_df = df_copy

  fig, ax = plt.subplots(figsize=(10, 8))

  # Custom autopct to only show internal percentages if > 2%
  def custom_autopct(pct):
    return f'{pct:.1f}%' if pct > 2.0 else ''

  colors = sns.color_palette("muted", len(plot_df))
  wedges, texts, autotexts = ax.pie(
      plot_df[value_col],
      labels=None,  # Remove overlapping outer labels
      autopct=custom_autopct,
      startangle=140,
      colors=colors,
      textprops={'color': "black"}  # Internal text color
  )

  # Create an external legend instead
  legend_labels = [
      f'{row[label_col]} ({row[value_col]/plot_df[value_col].sum()*100:.1f}%)'
      for _, row in plot_df.iterrows()
  ]
  ax.legend(wedges,
            legend_labels,
            title=label_col,
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1))

  ax.axis('equal')
  plt.title(title, pad=20)
  plt.tight_layout()
  plt.savefig(os.path.join(PLOTS_DIR, filename), bbox_inches='tight')
  plt.close()
  return f"plots/{filename}"


def generate_report():
  """Builds an exhaustive REPORT.md file analyzing all portfolios, focused on active accounts."""

  # -------------------------------------------------------------
  # Render Output String
  # -------------------------------------------------------------
  report_lines = [
      "# Portfolio Tracking",
      f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n",
      "---", ""
  ]

  # Files Discovery
  # Gather ALL final processed TSV files from the tsvs/ folder
  all_tsv_files = [
      f for f in glob.glob(os.path.join(PORTFOLIOS_DIR, "tsvs", "*.tsv"))
      if not os.path.basename(f).startswith("_") and
      "example" not in os.path.basename(f).lower()
  ]
  if not all_tsv_files:
    # Fallback to standard TSVs if metrics not yet run
    all_tsv_files = [
        f for f in glob.glob(os.path.join(PORTFOLIOS_DIR, "*.tsv"))
        if "_combined" not in f and "_meta" not in f and
        f != "portfolio.json" and "example" not in os.path.basename(f).lower()
    ]

  active_files = []
  inactive_files = []
  for f in all_tsv_files:
    base = os.path.basename(f).replace(".tsv", "")
    if base in ACTIVE_TRADING_PORTFOLIOS:
      active_files.append(f)
    else:
      inactive_files.append(f)

  # Compile Combined Active DataFrame
  combined_active_rows = []
  for f in active_files:
    df = pd.read_csv(f, sep='\t')
    for _, row in df.iterrows():
      combined_active_rows.append(row.to_dict())

  active_agg_df = pd.DataFrame()
  if combined_active_rows:
    raw_active_df = pd.DataFrame(combined_active_rows)
    # Aggregate logic
    active_agg_df = raw_active_df.groupby('Ticker').agg({
        'Current_Value': 'sum',
        'Quantity': 'sum',
        'Unrealized_PnL_Net': 'sum',
        'Day_Change_Net': 'sum'
    }).reset_index()
    # Derive price and percentages safely
    active_agg_df['Price'] = active_agg_df.apply(
        lambda row: round(row['Current_Value'] / row['Quantity'], 2)
        if row['Quantity'] > 0 else 0,
        axis=1)
    active_agg_df['Cost_Basis'] = active_agg_df[
        'Current_Value'] - active_agg_df['Unrealized_PnL_Net']
    active_agg_df['Unrealized_PnL_Pct'] = active_agg_df.apply(
        lambda row: round(row['Unrealized_PnL_Net'] / row['Cost_Basis'] * 100, 2
                         ) if row['Cost_Basis'] > 0 else 0,
        axis=1)
    active_agg_df['Day_Change_Pct'] = active_agg_df.apply(
        lambda row: round(
            row['Day_Change_Net'] /
            (row['Current_Value'] - row['Day_Change_Net']) * 100, 2)
        if (row['Current_Value'] - row['Day_Change_Net']) > 0 else 0,
        axis=1)
    active_agg_df = active_agg_df.sort_values(by='Current_Value',
                                              ascending=False)
    active_agg_df = map_sectors(active_agg_df)

  # 1. Active Portfolio Section
  report_lines.append("## 📈 Active Trading Portfolios\n")
  if not active_agg_df.empty:
    total_active_val = active_agg_df['Current_Value'].sum()
    total_active_day = active_agg_df['Day_Change_Net'].sum()
    report_lines.append(f"- **Active Tracked Value:** ${total_active_val:,.2f}")
    report_lines.append(
        f"- **Active Daily Change:** ${total_active_day:,.2f}\n")

    # Plots
    alloc_plot = create_pie_chart(active_agg_df, 'Ticker', 'Current_Value',
                                  "Active Portfolio Holdings",
                                  "active_allocation_pie.png")
    sector_agg = active_agg_df.groupby(
        'Sector')['Current_Value'].sum().reset_index()
    sec_plot = create_pie_chart(sector_agg, 'Sector', 'Current_Value',
                                "Active Sector Weighting",
                                "active_sector_pie.png")

    report_lines.append("### Active Visualizations\n")
    if alloc_plot:
      report_lines.append(f"![Active Holdings]({alloc_plot})")
    if sec_plot:
      report_lines.append(f"![Active Sectors]({sec_plot})")
    report_lines.append("\n\n### Active Aggregate Holdings\n")

    # Format df slightly for markdown
    display_df = active_agg_df[[
        'Ticker', 'Sector', 'Price', 'Quantity', 'Current_Value',
        'Unrealized_PnL_Net', 'Unrealized_PnL_Pct', 'Day_Change_Net',
        'Day_Change_Pct'
    ]].round(2)
    report_lines.append(display_df.to_markdown(index=False))
    report_lines.append("\n\n")

  # List Individual Active Portfolios
  for f in sorted(active_files):
    df = pd.read_csv(f, sep='\t')
    name = os.path.basename(f).replace('.tsv', '').replace('_', ' ').title()
    report_lines.append(f"### {name} (Active - {len(df)} positions)\n")
    report_lines.append(df.to_markdown(index=False))
    report_lines.append("\n\n")

  # 2. Complete Global View Section
  report_lines.append("---\n\n## 🌍 Full Global Portfolio View\n")

  meta_path = os.path.join(PORTFOLIOS_DIR, "portfolio_summary.tsv")
  if os.path.exists(meta_path):
    meta_df = pd.read_csv(meta_path, sep='\t')
    # Filter unknown generated example if present
    meta_df = meta_df[~meta_df['Portfolio_Name'].str.
                      contains("Example", case=False, na=False)]

    total_value = meta_df['Total_Value'].sum()
    total_positions = meta_df['Position_Count'].sum()
    report_lines.append(f"- **Total Account Value:** ${total_value:,.2f}")
    report_lines.append(f"- **Total Positions:** {total_positions}\n\n")

  # Load Combined All Portfolios
  combined_path = os.path.join(PORTFOLIOS_DIR, "_combined_portfolio.tsv")
  combined_df = pd.DataFrame()
  if os.path.exists(combined_path):
    combined_df = pd.read_csv(combined_path, sep='\t')

  if not combined_df.empty:
    combined_df = map_sectors(combined_df)
    all_alloc = create_pie_chart(combined_df, 'Ticker', 'Current_Value',
                                 "Total Global Allocation",
                                 "all_allocation_pie.png")
    if all_alloc:
      report_lines.append(f"![Total Global Allocation]({all_alloc})\n\n")

    report_lines.append("### All Aggregate Holdings\n")
    display_all = combined_df[[
        'Ticker', 'Sector', 'Price', 'Quantity', 'Current_Value',
        'Unrealized_PnL_Net', 'Day_Change_Net'
    ]].round(2)
    report_lines.append(display_all.to_markdown(index=False))
    report_lines.append("\n\n")

  # List Individual Inactive Portfolios
  report_lines.append("### Inactive / Set & Forget Portfolios\n")
  for f in sorted(inactive_files):
    df = pd.read_csv(f, sep='\t')
    name = os.path.basename(f).replace('.tsv', '').replace('_', ' ').title()
    report_lines.append(f"#### {name} ({len(df)} positions)\n")
    report_lines.append(df.to_markdown(index=False))
    report_lines.append("\n\n")

  # Write output
  report_path = os.path.join(PORTFOLIOS_DIR, "REPORT.md")
  with open(report_path, "w") as f:
    f.write("\n".join(report_lines))

  logger.info(
      f"Successfully generated comprehensive Active/Global Markdown report: {report_path}"
  )


if __name__ == "__main__":
  generate_report()
