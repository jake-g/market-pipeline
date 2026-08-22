#!/usr/bin/env python3
"""Macroeconomic and Maritime Shipping intelligence report generator.

This module processes FRED macroeconomic indicators, policy uncertainty indices,
global maritime chokepoints, and freight rate indicators to generate clean,
multi-panel timeline visualizations, correlation matrices, and markdown/PDF reports.
"""

import datetime
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from tabulate import tabulate

REPORTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(REPORTS_DIR)
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

import config
from reports.report_utils import clean_md
from reports.report_utils import render_markdown_to_pdf
from reports.report_utils import setup_plot_aesthetics

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Silence verbose third-party loggers
logging.getLogger("weasyprint").setLevel(logging.WARNING)
logging.getLogger("weasyprint.progress").setLevel(logging.WARNING)
logging.getLogger("fontTools").setLevel(logging.WARNING)

MACRO_TSV = os.path.join(config.MARKET_DATA_DIR, "macro",
                         "economic_indicators.tsv")
SHIPPING_CHOKEPOINT_TSV = os.path.join(config.MARKET_DATA_DIR, "shipping",
                                       "chokepoint_metrics.tsv")
SHIPPING_MACRO_TSV = os.path.join(config.MARKET_DATA_DIR, "shipping",
                                  "shipping_macro.tsv")

RENDERED_DIR = os.path.join(REPORTS_DIR, "news", "rendered")


def safe_pct_change(old_val: float, new_val: float) -> float:
  """Computes percentage change safely handling nulls and zeros."""
  if pd.isna(old_val) or pd.isna(new_val) or old_val == 0:
    return np.nan
  return ((new_val - old_val) / abs(old_val)) * 100.0


def plot_macro_timeline(df: pd.DataFrame, duration_label: str,
                        output_path: str) -> None:
  """Plots macroeconomic indicators with Policy Uncertainty in a dedicated panel."""
  setup_plot_aesthetics()

  fundamental_cols = ["FEDFUNDS", "US10Y", "CPI"]
  fundamental_cols = [c for c in fundamental_cols if c in df.columns]
  has_uncertainty = "US_POLICY_UNCERTAINTY" in df.columns

  if df.empty or not fundamental_cols:
    return

  if has_uncertainty:
    fig, (ax_top, ax_bottom) = plt.subplots(
        2,
        1,
        figsize=(14, 8),
        sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1.0]},
    )
  else:
    fig, ax_top = plt.subplots(1, 1, figsize=(14, 6))
    ax_bottom = None

  # Top Panel: Fundamental Macro Indicators (Normalized Z-score)
  colors = ["#1D3557", "#2A9D8F", "#E63946", "#F4A261"]
  for idx, col in enumerate(fundamental_cols):
    series = df[col].dropna()
    if not series.empty:
      std_val = series.std()
      norm_series = (series -
                     series.mean()) / (std_val if std_val != 0 else 1.0)
      ax_top.plot(
          series.index,
          norm_series,
          label=f"{col} (Z-Score)",
          linewidth=2.4,
          color=colors[idx % len(colors)],
      )

  ax_top.set_title(
      f"Macro Fundamentals ({duration_label})",
      fontweight="bold",
      fontsize=13,
      pad=10,
  )
  ax_top.set_ylabel("Z-Score", fontweight="bold")
  ax_top.legend(loc="upper left", framealpha=0.9, fontsize=9.5)
  ax_top.grid(True, alpha=0.3)
  ax_top.axhline(0, color="gray", linestyle=":", alpha=0.6)

  # Bottom Panel: Dedicated Economic Policy Uncertainty Index
  if ax_bottom is not None:
    unc_series = df["US_POLICY_UNCERTAINTY"].dropna()
    if not unc_series.empty:
      ax_bottom.plot(
          unc_series.index,
          unc_series.values,
          color="#E76F51",
          label="US Policy Uncertainty",
          linewidth=1.8,
      )
      ax_bottom.fill_between(
          unc_series.index,
          unc_series.values,
          alpha=0.25,
          color="#E76F51",
      )
      med_val = unc_series.median()
      ax_bottom.axhline(
          med_val,
          color="#457B9D",
          linestyle="--",
          linewidth=1.5,
          label=f"Median ({med_val:.1f})",
      )
      ax_bottom.set_title(
          "Policy Uncertainty Index",
          fontweight="bold",
          fontsize=11,
          pad=8,
      )
      ax_bottom.set_ylabel("Index Level", fontweight="bold")
      ax_bottom.legend(loc="upper left", framealpha=0.9, fontsize=9)
      ax_bottom.grid(True, alpha=0.3)

  plt.tight_layout()
  plt.savefig(output_path, dpi=300)
  plt.close()


def generate_macro_report() -> None:
  """Generates comprehensive macroeconomic status report and timeline charts."""
  if not os.path.exists(MACRO_TSV):
    logger.warning("Macro data missing at %s", MACRO_TSV)
    return

  logger.info("Generating Macro Economic Indicator Report...")
  df = pd.read_csv(MACRO_TSV, sep="\t")
  df["DATE"] = pd.to_datetime(df["DATE"])
  df = df.sort_values("DATE").set_index("DATE")

  recent_df = df[df.index >= pd.Timestamp.now() - pd.DateOffset(years=5)]
  os.makedirs(RENDERED_DIR, exist_ok=True)

  # 1. Correlation Matrix Heatmap
  setup_plot_aesthetics()
  corr_cols = [
      "US_POLICY_UNCERTAINTY",
      "GLOBAL_POLICY_UNCERTAINTY",
      "FEDFUNDS",
      "US10Y",
      "CPI",
      "UNRATE",
      "REAL_GDP",
      "WTI_CRUDE",
      "USD_INDEX",
      "TECH_PULSE",
      "ST_LOUIS_FIN_STRESS",
      "CHICAGO_FED_ACTIVITY",
      "DISPOSABLE_INCOME",
  ]
  corr_cols = [c for c in corr_cols if c in recent_df.columns]

  if not recent_df[corr_cols].empty:
    corr_df = recent_df[corr_cols].corr()

    plt.figure(figsize=(12, 10))
    sns.heatmap(
        corr_df,
        annot=True,
        cmap="coolwarm",
        center=0,
        fmt=".2f",
        linewidths=0.5,
        cbar_kws={"shrink": 0.8},
    )
    plt.title(
        "Macro Correlation Matrix (5-Year)",
        fontweight="bold",
        fontsize=13,
        pad=15,
    )
    plt.tight_layout()
    corr_img_path = os.path.join(RENDERED_DIR, "macro_correlation.png")
    plt.savefig(corr_img_path, dpi=300)
    plt.close()

    c_real = corr_df.unstack().dropna()
    c_real = c_real[c_real < 0.999].drop_duplicates()

    top_pos = c_real.nlargest(5)
    top_neg = c_real.nsmallest(5)

    corr_text = "### Top Positive Correlations\n"
    for (i1, i2), val in top_pos.items():
      corr_text += f"- **{i1}** & **{i2}**: `{val:.2f}`\n"

    corr_text += "\n### Top Inverse Correlations\n"
    for (i1, i2), val in top_neg.items():
      corr_text += f"- **{i1}** & **{i2}**: `{val:.2f}`\n"
  else:
    corr_text = "*Not enough data for correlation analysis.*"

  # 2. Multi-Panel Timeline Plots (5-Year & 1-Year)
  plot_macro_timeline(
      recent_df,
      "5-Year",
      os.path.join(RENDERED_DIR, "macro_timeline_5yr.png"),
  )

  yr1_df = recent_df[recent_df.index >= pd.Timestamp.now() -
                     pd.DateOffset(years=1)]
  plot_macro_timeline(yr1_df, "1-Year",
                      os.path.join(RENDERED_DIR, "macro_timeline_1yr.png"))

  # 3. Macro Indicator Summary Table
  latest_data: List[Dict[str, Any]] = []
  anomalies: List[str] = []

  for col in df.columns:
    valid_series = df[col].dropna()
    if valid_series.empty:
      continue

    latest_val = valid_series.iloc[-1]
    latest_date = valid_series.index[-1]

    mo1_date = latest_date - pd.DateOffset(months=1)
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

    recent_series = valid_series[valid_series.index >= pd.Timestamp.now() -
                                 pd.DateOffset(years=5)]
    if len(recent_series) > 10 and recent_series.std() != 0:
      z_score = (latest_val - recent_series.mean()) / recent_series.std()
    else:
      z_score = np.nan

    days_stale = (pd.Timestamp.now() - latest_date).days
    if days_stale > 365:
      anomalies.append(
          f"- ⚠️ **{col}** is stale (Last updated {days_stale} days ago on"
          f" {latest_date.strftime('%Y-%m-%d')}).")

    if len(valid_series) >= 2:
      prev_val = valid_series.iloc[-2]
      if abs(prev_val) > 1.0:
        day_chg = safe_pct_change(prev_val, latest_val)
        if pd.notna(day_chg) and abs(day_chg) > 20:
          direction = "spiked" if day_chg > 0 else "dropped"
          anomalies.append(
              f"- 🚨 **{col}** {direction} by {abs(day_chg):.1f}% in latest"
              f" reading (from {prev_val:.2f} to {latest_val:.2f}).")

    latest_data.append({
        "Indicator": col,
        "Latest": round(latest_val, 2),
        "1M Chg": f"{mo1_chg:+.2f}%" if pd.notna(mo1_chg) else "N/A",
        "1Y Chg": f"{yr1_chg:+.2f}%" if pd.notna(yr1_chg) else "N/A",
        "5Y Z-Score": round(z_score, 2),
        "Date": latest_date.strftime("%Y-%m-%d"),
        "_sort_z": abs(z_score) if pd.notna(z_score) else 0,
    })

  anomalies_text = (
      "\n".join(anomalies) if anomalies else
      "- *No severe macroeconomic anomalies or extreme jumps detected.*")

  summary_df = pd.DataFrame(latest_data)
  summary_df = summary_df.sort_values("_sort_z",
                                      ascending=False).drop(columns=["_sort_z"])

  summary_md = tabulate(summary_df.values,
                        headers=summary_df.columns,
                        tablefmt="github")

  report_md = f"""# Macroeconomic Indicators

## Overview
This report monitors {len(df.columns)} core macroeconomic indicators from the Federal Reserve Economic Data (FRED) system. Indicators are ranked by **5-Year Z-Score** to highlight the most statistically significant deviations in the current macroeconomic regime.

## Indicator Alerts
{anomalies_text}

## 1-Year Trends
![Timeline Plot 1Yr](rendered/macro_timeline_1yr.png)

## 5-Year Trends
![Timeline Plot 5Yr](rendered/macro_timeline_5yr.png)

## Correlation Matrix
{corr_text}

![Correlation Matrix](rendered/macro_correlation.png)

## Indicator Dashboard
{summary_md}
"""

  report_path = os.path.join(REPORTS_DIR, "news", "MACRO_REPORT.md")
  with open(report_path, "w", encoding="utf-8") as f:
    f.write(clean_md(report_md))
  logger.info("Generated %s", report_path)
  render_markdown_to_pdf(report_path)


def generate_shipping_report() -> None:
  """Generates global maritime shipping and supply chain intelligence report."""
  if not os.path.exists(SHIPPING_CHOKEPOINT_TSV):
    logger.warning("Shipping data missing at %s", SHIPPING_CHOKEPOINT_TSV)
    return

  logger.info("Generating Shipping Indicators Report...")
  df = pd.read_csv(SHIPPING_CHOKEPOINT_TSV, sep="\t")
  if "Date" not in df.columns:
    logger.warning(
        "No 'Date' column found in Shipping Chokepoint TSV. Skipping report.")
    return

  df["Date"] = pd.to_datetime(df["Date"])
  os.makedirs(RENDERED_DIR, exist_ok=True)

  # 1. Clean Multi-Panel Shipping Status & Trend Plot
  setup_plot_aesthetics()
  fig, (ax_bar, ax_macro) = plt.subplots(1, 2, figsize=(15, 6))

  latest_date = df["Date"].max()
  latest_df = (df[df["Date"] == latest_date].copy().sort_values(
      "Congestion_Index", ascending=True))

  # Left Panel: Latest Chokepoint Congestion Level
  bar_colors = [
      "#2A9D8F" if x < 0.3 else "#F4A261" if x < 0.7 else "#E63946"
      for x in latest_df["Congestion_Index"]
  ]
  bars = ax_bar.barh(
      latest_df["Chokepoint_Name"],
      latest_df["Congestion_Index"],
      color=bar_colors,
      alpha=0.85,
  )
  ax_bar.set_xlim(0, 1.15)
  ax_bar.set_title(
      "Chokepoint Congestion Index",
      fontweight="bold",
      fontsize=12,
  )
  ax_bar.set_xlabel("Congestion (0.0 = Normal, 1.0 = Bottleneck)")
  ax_bar.grid(True, alpha=0.3)

  for bar, vessels in zip(bars, latest_df["Vessel_Count"]):
    width = bar.get_width()
    ax_bar.text(
        width + 0.02,
        bar.get_y() + bar.get_height() / 2,
        f"{width:.2f} ({int(vessels)} vessels)",
        va="center",
        fontweight="bold",
        fontsize=9,
    )

  # Right Panel: Global Shipping & Freight Macro Trends
  has_shipping_macro = False
  if os.path.exists(SHIPPING_MACRO_TSV):
    sm_df = pd.read_csv(SHIPPING_MACRO_TSV, sep="\t")
    if not sm_df.empty and "Date" in sm_df.columns:
      sm_df["Date"] = pd.to_datetime(sm_df["Date"])
      for name, group in sm_df.groupby("Name"):
        group = group.sort_values("Date")
        if len(group) > 1:
          std_v = group["Value"].std()
          norm_v = (group["Value"] -
                    group["Value"].mean()) / (std_v if std_v != 0 else 1.0)
          ax_macro.plot(group["Date"], norm_v, label=name, linewidth=2.2)
          has_shipping_macro = True

  if has_shipping_macro:
    ax_macro.set_title(
        "Freight Macro Trends (Z-Score)",
        fontweight="bold",
        fontsize=12,
    )
    ax_macro.set_ylabel("Z-Score")
    ax_macro.legend(loc="upper left", framealpha=0.9, fontsize=9)
    ax_macro.grid(True, alpha=0.3)
  else:
    pivot_df = df.pivot(index="Date",
                        columns="Chokepoint_Name",
                        values="Congestion_Index")
    for col in pivot_df.columns:
      series = pivot_df[col].dropna()
      ax_macro.plot(series.index, series, label=col, marker="o", markersize=3)
    ax_macro.set_title("Historical Congestion Trend", fontweight="bold")
    ax_macro.set_ylabel("Congestion Index")
    ax_macro.legend(loc="upper left", framealpha=0.9, fontsize=9)
    ax_macro.grid(True, alpha=0.3)

  plt.tight_layout()
  timeline_img_path = os.path.join(RENDERED_DIR, "shipping_timeline.png")
  plt.savefig(timeline_img_path, dpi=300)
  plt.close()

  # 2. Latest Status Table
  table_md = tabulate(
      latest_df[["Chokepoint_Name", "Vessel_Count", "Congestion_Index"]].values,
      headers=["Chokepoint", "Vessels", "Congestion Index"],
      tablefmt="github",
  )

  # 3. Macro Shipping Section
  macro_section = ""
  if os.path.exists(SHIPPING_MACRO_TSV):
    sm_df = pd.read_csv(SHIPPING_MACRO_TSV, sep="\t")
    if not sm_df.empty and "Date" in sm_df.columns:
      sm_df["Date"] = pd.to_datetime(sm_df["Date"])
      macro_items: List[List[Any]] = []

      for name, group in sm_df.groupby("Name"):
        group = group.sort_values("Date")
        latest_row = group.iloc[-1]
        latest_val = latest_row["Value"]

        yr1_date = latest_row["Date"] - pd.DateOffset(years=1)
        past_group = group[group["Date"] <= yr1_date]
        if not past_group.empty:
          yr1_val = past_group.iloc[-1]["Value"]
          yr1_chg = safe_pct_change(yr1_val, latest_val)
          yr1_str = f" ({yr1_chg:+.2f}% YoY)" if pd.notna(yr1_chg) else ""
        else:
          yr1_str = ""

        macro_items.append([
            name,
            round(latest_val, 2),
            yr1_str.strip(),
            latest_row["Date"].strftime("%Y-%m-%d"),
        ])

      sm_summary_df = pd.DataFrame(
          macro_items, columns=["Metric", "Latest", "YoY Chg", "Date"])
      sm_summary_md = tabulate(
          sm_summary_df.values,
          headers=sm_summary_df.columns,
          tablefmt="github",
      )

      macro_section = f"""
## Shipping Macro Metrics
{sm_summary_md}
"""

  report_md = f"""# Maritime Shipping Report

## Overview
This report monitors global maritime chokepoints (Strait of Hormuz, Malacca Strait, Panama Canal, Taiwan Strait) and macroeconomic freight indicators to track supply chain bottlenecks, tanker availability, and logistical disruptions.

## Congestion Trends
![Congestion Timeline](rendered/shipping_timeline.png)

## Chokepoint Status
{table_md}
{macro_section}
"""

  report_path = os.path.join(REPORTS_DIR, "news", "SHIPPING_REPORT.md")
  with open(report_path, "w", encoding="utf-8") as f:
    f.write(clean_md(report_md))
  logger.info("Generated %s", report_path)
  render_markdown_to_pdf(report_path)


if __name__ == "__main__":
  generate_macro_report()
  generate_shipping_report()
