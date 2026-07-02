#!/usr/bin/env python3
import datetime
import logging
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from tabulate import tabulate

# Add project root to sys path
REPORTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(REPORTS_DIR)
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

import config
from reports.report_utils import render_markdown_to_pdf
from reports.report_utils import setup_plot_aesthetics

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

MACRO_TSV = os.path.join(config.MARKET_DATA_DIR, "macro",
                         "economic_indicators.tsv")
SHIPPING_CHOKEPOINT_TSV = os.path.join(config.MARKET_DATA_DIR, "shipping",
                                       "chokepoint_metrics.tsv")
SHIPPING_MACRO_TSV = os.path.join(config.MARKET_DATA_DIR, "shipping",
                                  "shipping_macro.tsv")

RENDERED_DIR = os.path.join(REPORTS_DIR, "news", "rendered")


def safe_pct_change(old_val, new_val):
  if pd.isna(old_val) or pd.isna(new_val) or old_val == 0:
    return np.nan
  return ((new_val - old_val) / abs(old_val)) * 100


def generate_macro_report():
  if not os.path.exists(MACRO_TSV):
    logger.warning(f"Macro data missing at {MACRO_TSV}")
    return

  logger.info("Generating Macro Economic Indicator Report...")
  df = pd.read_csv(MACRO_TSV, sep="\t")
  df['DATE'] = pd.to_datetime(df['DATE'])
  df = df.sort_values("DATE").set_index("DATE")

  # Filter for the last 5 years for meaningful recent analysis
  recent_df = df[df.index >= pd.Timestamp.now() - pd.DateOffset(years=5)]

  # Ensure rendered directory exists
  os.makedirs(RENDERED_DIR, exist_ok=True)

  # 1. Correlation Matrix
  setup_plot_aesthetics()
  corr_cols = [
      'US_POLICY_UNCERTAINTY', 'GLOBAL_POLICY_UNCERTAINTY', 'FEDFUNDS', 'US10Y',
      'CPI', 'UNRATE', 'REAL_GDP', 'WTI_CRUDE', 'USD_INDEX', 'TECH_PULSE',
      'ST_LOUIS_FIN_STRESS', 'CHICAGO_FED_ACTIVITY', 'DISPOSABLE_INCOME'
  ]
  corr_cols = [c for c in corr_cols if c in recent_df.columns]

  if not recent_df[corr_cols].empty:
    corr_df = recent_df[corr_cols].corr()

    plt.figure(figsize=(12, 10))
    sns.heatmap(corr_df,
                annot=True,
                cmap="coolwarm",
                center=0,
                fmt=".2f",
                linewidths=0.5)
    plt.title("Macro Indicators Correlation Matrix (Last 5 Years)",
              fontweight="bold")
    plt.tight_layout()
    corr_img_path = os.path.join(RENDERED_DIR, "macro_correlation.png")
    plt.savefig(corr_img_path, dpi=300)
    plt.close()

    # Extract top correlations for text output
    c_real = corr_df.unstack().dropna()
    c_real = c_real[
        c_real < 0.999].drop_duplicates()  # Remove self correlation and dupes

    top_pos = c_real.nlargest(5)
    top_neg = c_real.nsmallest(5)

    corr_text = "### 🔥 Top Positive Correlations\n"
    for (i1, i2), val in top_pos.items():
      corr_text += f"- **{i1}** & **{i2}**: `{val:.2f}`\n"

    corr_text += "\n### 🧊 Top Inverse Correlations\n"
    for (i1, i2), val in top_neg.items():
      corr_text += f"- **{i1}** & **{i2}**: `{val:.2f}`\n"
  else:
    corr_text = "*Not enough data for correlation analysis.*"

  # 2. Timeline Plots (1-Yr and 5-Yr)
  plot_cols = ['US_POLICY_UNCERTAINTY', 'FEDFUNDS', 'US10Y', 'CPI']
  plot_cols = [c for c in plot_cols if c in recent_df.columns]

  if plot_cols:
    # 5-Year Plot
    plt.figure(figsize=(14, 7))
    for c in plot_cols:
      series = recent_df[c].dropna()
      if not series.empty:
        norm_series = (series - series.mean()) / series.std()
        plt.plot(series.index, norm_series, label=c)
    plt.title("Key Macro Trends (Z-Score Normalized, Last 5 Years)",
              fontweight="bold")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    timeline_img_path = os.path.join(RENDERED_DIR, "macro_timeline_5yr.png")
    plt.savefig(timeline_img_path, dpi=300)
    plt.close()

    # 1-Year Plot
    yr1_df = recent_df[recent_df.index >= pd.Timestamp.now() -
                       pd.DateOffset(years=1)]
    plt.figure(figsize=(14, 7))
    for c in plot_cols:
      series = yr1_df[c].dropna()
      if not series.empty:
        norm_series = (series - series.mean()) / series.std()
        plt.plot(series.index, norm_series, label=c)
    plt.title("Key Macro Trends (Z-Score Normalized, Last 1 Year)",
              fontweight="bold")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    timeline_img_path_1yr = os.path.join(RENDERED_DIR, "macro_timeline_1yr.png")
    plt.savefig(timeline_img_path_1yr, dpi=300)
    plt.close()

  # Create Summary Table with 1-Mo, 1-Yr Changes, and 5-Yr Z-Score
  latest_data = []

  for col in df.columns:
    valid_series = df[col].dropna()
    if valid_series.empty:
      continue

    latest_val = valid_series.iloc[-1]
    latest_date = valid_series.index[-1]

    # 1 Month ago
    mo1_date = latest_date - pd.DateOffset(months=1)
    # 1 Year ago
    yr1_date = latest_date - pd.DateOffset(years=1)

    try:
      mo1_val = valid_series[valid_series.index <= mo1_date].iloc[-1]
    except IndexError:
      mo1_val = np.nan

    try:
      yr1_val = valid_series[valid_series.index <= yr1_date].iloc[-1]
    except IndexError:
      yr1_val = np.nan

    mo1_chg = safe_pct_change(mo1_val, latest_val)
    yr1_chg = safe_pct_change(yr1_val, latest_val)

    # 5-Year Z-Score
    recent_series = valid_series[valid_series.index >= pd.Timestamp.now() -
                                 pd.DateOffset(years=5)]
    if len(recent_series) > 10 and recent_series.std() != 0:
      z_score = (latest_val - recent_series.mean()) / recent_series.std()
    else:
      z_score = np.nan

    latest_data.append({
        "Indicator": col,
        "Latest Value": round(latest_val, 2),
        "1-Mo Chg (%)": f"{mo1_chg:.2f}%" if pd.notna(mo1_chg) else "N/A",
        "1-Yr Chg (%)": f"{yr1_chg:.2f}%" if pd.notna(yr1_chg) else "N/A",
        "5-Yr Z-Score": round(z_score, 2),
        "Date": latest_date.strftime("%Y-%m-%d"),
        "_sort_z": abs(z_score) if pd.notna(z_score) else 0
    })

  # Anomaly Detection (Stale Data or Extreme Sudden Jumps)
  anomalies = []
  for col in df.columns:
    valid_series = df[col].dropna()
    if valid_series.empty:
      continue
    latest_date = valid_series.index[-1]
    days_stale = (pd.Timestamp.now() - latest_date).days
    if days_stale > 365:
      anomalies.append(
          f"- ⚠️ **{col}** is extremely stale (Last updated {days_stale} days ago on {latest_date.strftime('%Y-%m-%d')})."
      )

    # Detect sudden 1-day spikes > 15% (for values > 1.0 to avoid small number noise)
    if len(valid_series) >= 2:
      latest_val = valid_series.iloc[-1]
      prev_val = valid_series.iloc[-2]
      if abs(prev_val) > 1.0:
        day_chg = safe_pct_change(prev_val, latest_val)
        if pd.notna(day_chg) and abs(day_chg) > 15:
          direction = "spiked" if day_chg > 0 else "crashed"
          anomalies.append(
              f"- 🚨 **{col}** {direction} by {abs(day_chg):.1f}% in its latest reading (from {prev_val:.2f} to {latest_val:.2f})."
          )

  anomalies_text = "\n".join(
      anomalies
  ) if anomalies else "- *No severe data anomalies or extremely stale metrics detected.*"

  summary_df = pd.DataFrame(latest_data)
  # Sort by absolute Z-Score descending (most extreme metrics first)
  summary_df = summary_df.sort_values("_sort_z",
                                      ascending=False).drop(columns=["_sort_z"])

  summary_md = tabulate(summary_df.values,
                        headers=summary_df.columns,
                        tablefmt="github")

  report_md = f"""# Macro Economic Indicators Report
**Generated:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 Overview
This report provides a high-level summary of the {len(df.columns)} macroeconomic indicators tracked in the pipeline.
The table is sorted by **5-Year Z-Score** to highlight the most statistically extreme deviations in the current macroeconomic environment.

## 🚨 Data Anomalies & Alerts
{anomalies_text}

## 📈 Key Trends (Normalized)
### 1-Year Zoom
![Timeline Plot 1Yr](rendered/macro_timeline_1yr.png)

### 5-Year Zoom
![Timeline Plot 5Yr](rendered/macro_timeline_5yr.png)

## 🔗 Correlation Matrix & Insights (Last 5 Years)
{corr_text}

![Correlation Matrix](rendered/macro_correlation.png)

## 📋 Latest Indicator Values (Sorted by Absolute Z-Score)
{summary_md}
"""

  report_path = os.path.join(REPORTS_DIR, "news", "MACRO_REPORT.md")
  with open(report_path, "w") as f:
    f.write(report_md)
  logger.info(f"Generated {report_path}")
  render_markdown_to_pdf(report_path)


def generate_shipping_report():
  if not os.path.exists(SHIPPING_CHOKEPOINT_TSV):
    logger.warning(f"Shipping data missing at {SHIPPING_CHOKEPOINT_TSV}")
    return

  logger.info("Generating Shipping Indicators Report...")
  df = pd.read_csv(SHIPPING_CHOKEPOINT_TSV, sep="\t")
  if 'Date' not in df.columns:
    logger.warning(
        "No 'Date' column found in Shipping Chokepoint TSV. Skipping report.")
    return

  df['Date'] = pd.to_datetime(df['Date'])

  os.makedirs(RENDERED_DIR, exist_ok=True)

  # 1. Congestion Timeline Plot
  setup_plot_aesthetics()
  plt.figure(figsize=(14, 7))

  pivot_df = df.pivot(index="Date",
                      columns="Chokepoint_Name",
                      values="Congestion_Index")
  if not pivot_df.empty:
    for col in pivot_df.columns:
      series = pivot_df[col].dropna()
      plt.plot(series.index, series, label=col, marker="o", markersize=4)

    plt.title("Maritime Chokepoint Congestion Index", fontweight="bold")
    plt.ylabel("Congestion Index")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    timeline_img_path = os.path.join(RENDERED_DIR, "shipping_timeline.png")
    plt.savefig(timeline_img_path, dpi=300)
    plt.close()

  # 2. Latest Status Table
  latest_date = df['Date'].max()
  latest_df = df[df['Date'] == latest_date].copy()

  table_md = tabulate(
      latest_df[["Chokepoint_Name", "Vessel_Count", "Congestion_Index"]].values,
      headers=["Chokepoint", "Vessel Count", "Congestion Index"],
      tablefmt="github")

  # 3. Macro Shipping
  macro_section = ""
  if os.path.exists(SHIPPING_MACRO_TSV):
    sm_df = pd.read_csv(SHIPPING_MACRO_TSV, sep="\t")
    if not sm_df.empty and 'Date' in sm_df.columns:
      sm_df['Date'] = pd.to_datetime(sm_df['Date'])

      macro_items = []

      # Pivot by Name to get individual series
      for name, group in sm_df.groupby("Name"):
        group = group.sort_values("Date")
        latest_row = group.iloc[-1]
        latest_val = latest_row['Value']

        # Calculate 1yr change
        yr1_date = latest_row['Date'] - pd.DateOffset(years=1)
        past_group = group[group['Date'] <= yr1_date]
        if not past_group.empty:
          yr1_val = past_group.iloc[-1]['Value']
          yr1_chg = safe_pct_change(yr1_val, latest_val)
          yr1_str = f" ({yr1_chg:+.2f}% YoY)" if pd.notna(yr1_chg) else ""
        else:
          yr1_str = ""

        macro_items.append([
            name,
            round(latest_val, 2),
            yr1_str.strip(), latest_row['Date'].strftime("%Y-%m-%d")
        ])

      sm_summary_df = pd.DataFrame(
          macro_items, columns=["Metric", "Latest Value", "YoY Change", "Date"])
      sm_summary_md = tabulate(sm_summary_df.values,
                               headers=sm_summary_df.columns,
                               tablefmt="github")

      macro_section = f"""
## 🌍 Shipping Macro Metrics
{sm_summary_md}
"""

  report_md = f"""# Global Shipping & Logistics Report
**Generated:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 🚢 Overview
This report monitors global maritime chokepoints and shipping macroeconomic indicators to track supply chain bottlenecks, freight costs, and logistical disruptions.

## 📈 Congestion Trends
![Congestion Timeline](rendered/shipping_timeline.png)

## 📍 Latest Chokepoint Status (As of {latest_date.strftime("%Y-%m-%d")})
{table_md}
{macro_section}
"""

  report_path = os.path.join(REPORTS_DIR, "news", "SHIPPING_REPORT.md")
  with open(report_path, "w") as f:
    f.write(report_md)
  logger.info(f"Generated {report_path}")
  render_markdown_to_pdf(report_path)


if __name__ == "__main__":
  generate_macro_report()
  generate_shipping_report()
