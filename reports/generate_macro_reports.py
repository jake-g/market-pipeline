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


# ---------------------------------------------------------------------------
# Macro report: native-observation analytics + regime panels
# ---------------------------------------------------------------------------

# Grouping drives the dashboard layout and the panel plots.
MACRO_GROUPS: Dict[str, List[str]] = {
    "Rates & Curve": [
        "FEDFUNDS", "US02Y", "US10Y", "US30Y", "YC_10Y_2Y", "YC_30Y_10Y",
        "REAL_FEDFUNDS"
    ],
    "Inflation & Growth": [
        "CPI_YOY", "FOOD_CPI_YOY", "GDP", "REAL_GDP", "CHICAGO_FED_ACTIVITY",
        "RECESSION_PROB", "M2_YOY", "M2_VELOCITY"
    ],
    "Labor & Consumer": [
        "UNRATE", "UMICH_SENTIMENT", "SAVINGS_RATE", "DISPOSABLE_INCOME",
        "CREDIT_CARD_DELINQUENCY", "HOUSING_STARTS", "HOUSEHOLD_NET_WORTH"
    ],
    "Credit & Stress": [
        "HY_SPREAD", "BAA_SPREAD", "AAA_SPREAD", "CORP_SPREAD",
        "ST_LOUIS_FIN_STRESS", "KANSAS_CITY_FIN_STRESS", "FED_ASSETS"
    ],
    "Commodities & FX": [
        "WTI_CRUDE", "NAT_GAS_PRICE", "COPPER_PRICE", "CORN_PRICE",
        "WHEAT_PRICE", "SUGAR_PRICE", "USD_INDEX", "USD_CNY", "USD_EUR",
        "USD_JPY"
    ],
    "Policy & Trade": [
        "US_POLICY_UNCERTAINTY", "GLOBAL_POLICY_UNCERTAINTY",
        "EUROPE_POLICY_UNCERTAINTY", "TARIFFS", "CHINA_IMPORTS", "TECH_PULSE",
        "RD_INVESTMENT"
    ],
    "Logistics & Power": [
        "FREIGHT_PPI", "TRUCK_PPI", "AIR_PPI", "WAREHOUSE_PPI",
        "ELECTRIC_POWER_INDEX", "MFG_CONST"
    ],
    "Structural (slow)": ["US_POPULATION", "US_BIRTH_RATE", "LIFE_EXPECTANCY"],
}
# Series quoted in percent / points: report absolute change (pp) not %.
RATE_LIKE = {
    "FEDFUNDS",
    "US02Y",
    "US10Y",
    "US30Y",
    "YC_10Y_2Y",
    "YC_30Y_10Y",
    "REAL_FEDFUNDS",
    "CPI_YOY",
    "FOOD_CPI_YOY",
    "M2_YOY",
    "UNRATE",
    "SAVINGS_RATE",
    "HY_SPREAD",
    "BAA_SPREAD",
    "AAA_SPREAD",
    "CORP_SPREAD",
    "RECESSION_PROB",
    "CREDIT_CARD_DELINQUENCY",
    "ST_LOUIS_FIN_STRESS",
    "KANSAS_CITY_FIN_STRESS",
    "CHICAGO_FED_ACTIVITY",
    "US_BIRTH_RATE",
}


def load_macro_observations(path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
  """Loads the macro TSV and recovers native observations per series.

  The fetcher forward-fills every series onto a daily index, which makes
  monthly/quarterly data look like step functions. Statistics computed on
  that frame (z-scores, correlations, "1M change") are dominated by the
  fill, so we rebuild each series as the points where the value actually
  changed, clipped to today.

  Args:
    path (str): economic_indicators.tsv.

  Returns:
    Tuple of (daily ffilled frame, dict-like frame of native observations
    where non-observation days are NaN).
  """
  df = pd.read_csv(path, sep="\t")
  df["DATE"] = pd.to_datetime(df["DATE"])
  df = df.sort_values("DATE").set_index("DATE")
  df = df[df.index <= pd.Timestamp.today().normalize()]

  obs = pd.DataFrame(index=df.index)
  for col in df.columns:
    s = df[col]
    changed = s.ne(s.shift()) & s.notna()
    obs[col] = s.where(changed)
  return df, obs


def add_derived_series(daily: pd.DataFrame,
                       obs: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
  """Adds curve, real-rate and YoY transforms to both frames."""

  def _yoy(col: str) -> pd.Series:
    s = obs[col].dropna()
    if s.empty:
      return pd.Series(dtype=float)
    # Compare with the observation closest to 365 days earlier.
    target_idx = pd.DatetimeIndex([d - pd.DateOffset(years=1) for d in s.index])
    prior = s.reindex(target_idx,
                      method="nearest",
                      tolerance=pd.Timedelta(days=45))
    out = (np.asarray(s.values, dtype=float) /
           np.asarray(prior.values, dtype=float) - 1) * 100
    return pd.Series(out, index=s.index)

  derived: Dict[str, pd.Series] = {}
  if {"US10Y", "US02Y"} <= set(daily.columns):
    derived["YC_10Y_2Y"] = daily["US10Y"] - daily["US02Y"]
  if {"US30Y", "US10Y"} <= set(daily.columns):
    derived["YC_30Y_10Y"] = daily["US30Y"] - daily["US10Y"]
  for src, name in (("CPI", "CPI_YOY"), ("FOOD_CPI", "FOOD_CPI_YOY"),
                    ("M2_MONEY", "M2_YOY")):
    if src in obs.columns:
      derived[name] = _yoy(src)
  if "FEDFUNDS" in daily.columns and "CPI_YOY" in derived:
    cpi_yoy_daily = derived["CPI_YOY"].reindex(daily.index).ffill()
    derived["REAL_FEDFUNDS"] = daily["FEDFUNDS"] - cpi_yoy_daily

  for name, s in derived.items():
    s = s.dropna()
    daily[name] = s.reindex(daily.index).ffill()
    changed = daily[name].ne(daily[name].shift()) & daily[name].notna()
    obs[name] = daily[name].where(changed)
  return daily, obs


def _nearest_before(s: pd.Series, when: pd.Timestamp) -> float:
  prior = s[s.index <= when]
  return float(prior.iloc[-1]) if not prior.empty else np.nan


def _fmt_change(col: str, old: float, new: float) -> str:
  if pd.isna(old) or pd.isna(new):
    return "—"
  if col in RATE_LIKE:
    return f"{new - old:+.2f}pp"
  return f"{safe_pct_change(old, new):+.1f}%"


def _trend_arrow(s: pd.Series) -> str:
  """Sign of the 3-month slope on native observations."""
  if len(s) < 3:
    return "·"
  cutoff = s.index[-1] - pd.DateOffset(months=3)
  recent = s[s.index >= cutoff]
  if len(recent) < 2:
    recent = s.tail(3)
  x = np.arange(len(recent))
  slope = np.polyfit(x, recent.values, 1)[0]
  scale = abs(recent.values).mean() or 1.0
  if slope / scale > 0.002:
    return "↑"
  if slope / scale < -0.002:
    return "↓"
  return "→"


def build_indicator_rows(obs: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
  """Per-indicator stats on native observations + alert strings."""
  now = pd.Timestamp.today().normalize()
  rows: List[Dict[str, Any]] = []
  alerts: List[str] = []
  five_y = now - pd.DateOffset(years=5)

  for col in obs.columns:
    s = obs[col].dropna()
    if s.empty:
      continue
    latest, when = float(s.iloc[-1]), s.index[-1]
    m1 = _nearest_before(s, when - pd.DateOffset(months=1))
    m3 = _nearest_before(s, when - pd.DateOffset(months=3))
    y1 = _nearest_before(s, when - pd.DateOffset(years=1))
    hist = s[s.index >= five_y]
    z = pct = np.nan
    if len(hist) > 10 and hist.std() > 0:
      z = (latest - hist.mean()) / hist.std()
      pct = (hist < latest).mean() * 100

    # Staleness relative to the series' own cadence.
    gaps = s.index.to_series().diff().dt.days.dropna()
    cadence = float(gaps.tail(12).median()) if not gaps.empty else 30.0
    days_old = (now - when).days
    stale = days_old > max(3 * cadence, cadence + 45)

    # Jump alert: last move vs the distribution of moves.
    if len(hist) > 12:
      moves = hist.diff().dropna()
      last_move = latest - float(s.iloc[-2]) if len(s) > 1 else 0.0
      if moves.std() > 0 and abs(last_move) > 2.5 * moves.std():
        alerts.append(
            f"- 🚨 **{col}**: latest move {last_move:+.2f} is "
            f"{abs(last_move)/moves.std():.1f}σ of its 5Y move distribution "
            f"(now {latest:,.2f}, {when:%Y-%m-%d}).")
    if pd.notna(z) and abs(z) >= 2:
      alerts.append(f"- ⚠️ **{col}** at {latest:,.2f} is {z:+.1f}σ from its "
                    f"5-year mean ({pct:.0f}th percentile).")
    if stale:
      alerts.append(f"- ⏳ **{col}** stale: last observation {when:%Y-%m-%d} "
                    f"({days_old}d; typical cadence {cadence:.0f}d).")

    rows.append({
        "Indicator": col,
        "Latest": latest,
        "Δ1M": _fmt_change(col, m1, latest),
        "Δ3M": _fmt_change(col, m3, latest),
        "Δ1Y": _fmt_change(col, y1, latest),
        "5Y Z": z,
        "5Y pct": pct,
        "Trend": _trend_arrow(s),
        "As of": when.strftime("%Y-%m-%d"),
        "Stale": stale,
    })
  return pd.DataFrame(rows), alerts


def regime_summary(obs: pd.DataFrame) -> str:
  """Rule-based one-paragraph regime read from the latest observations."""

  def last(col: str) -> float:
    s = obs[col].dropna() if col in obs.columns else pd.Series(dtype=float)
    return float(s.iloc[-1]) if not s.empty else np.nan

  def chg3m(col: str) -> float:
    s = obs[col].dropna() if col in obs.columns else pd.Series(dtype=float)
    if s.empty:
      return np.nan
    return last(col) - _nearest_before(s, s.index[-1] - pd.DateOffset(months=3))

  us10, curve, real_ff = last("US10Y"), last("YC_10Y_2Y"), last("REAL_FEDFUNDS")
  cpi, hy, wti = last("CPI_YOY"), last("HY_SPREAD"), last("WTI_CRUDE")
  unrate, sent = last("UNRATE"), last("UMICH_SENTIMENT")
  bits = []
  growth = "expansion" if last("CHICAGO_FED_ACTIVITY") > -0.3 else "slowing"
  infl = ("re-accelerating" if chg3m("CPI_YOY") > 0.2 else
          "cooling" if chg3m("CPI_YOY") < -0.2 else "sticky")
  label = ("Stagflation-tilt" if infl != "cooling" and growth == "slowing" else
           "Late-cycle (hot rates)" if us10 >= 5 else
           "Disinflationary expansion" if infl == "cooling" else "Mid-cycle")
  bits.append(
      f"Growth {growth} (CFNAI {last('CHICAGO_FED_ACTIVITY'):+.2f}), "
      f"inflation {infl} (CPI {cpi:.1f}% YoY, {chg3m('CPI_YOY'):+.1f}pp "
      f"in 3M)")
  bits.append(f"10Y {us10:.2f}% ({chg3m('US10Y'):+.2f}pp 3M), curve 10s2s "
              f"{curve:+.2f}, real fed funds {real_ff:+.2f}%")
  bits.append(
      f"HY spread {hy:.2f}% ({chg3m('HY_SPREAD')*100:+.0f}bp 3M), "
      f"WTI ${wti:.0f} ({safe_pct_change(wti - chg3m('WTI_CRUDE'), wti):+.0f}% 3M)"
  )
  bits.append(f"unemployment {unrate:.1f}%, UMich sentiment {sent:.0f}")
  return f"**{label}.** " + "; ".join(bits) + "."


def plot_regime_panels(daily: pd.DataFrame, obs: pd.DataFrame, years: int,
                       output_path: str) -> None:
  """Four-panel regime dashboard: rates/curve, inflation, credit, commodities."""
  setup_plot_aesthetics()
  start = pd.Timestamp.today() - pd.DateOffset(years=years)
  d = daily[daily.index >= start]
  o = obs[obs.index >= start]
  fig, axes = plt.subplots(2, 2, figsize=(16, 10))
  (ax_rates, ax_infl), (ax_credit, ax_cmdty) = axes

  # 1. Rates & curve
  for col, c in (("FEDFUNDS", "#1D3557"), ("US02Y", "#457B9D"),
                 ("US10Y", "#2A9D8F"), ("US30Y", "#E9C46A")):
    if col in d:
      ax_rates.plot(d.index, d[col], label=col, color=c, linewidth=1.8)
  ax_rates.set_ylabel("%")
  ax_rates.set_title("Policy rate & Treasury curve", fontweight="bold")
  if "YC_10Y_2Y" in d:
    ax2 = ax_rates.twinx()
    yc = d["YC_10Y_2Y"]
    ax2.fill_between(d.index,
                     yc,
                     0,
                     where=yc < 0,
                     color="#E63946",
                     alpha=0.25,
                     label="10s2s inverted")
    ax2.plot(d.index,
             yc,
             color="#E63946",
             linewidth=1,
             linestyle="--",
             label="10s2s spread (rhs)")
    ax2.set_ylabel("10Y−2Y (pp)")
    ax2.axhline(0, color="#E63946", linewidth=0.6)
    h1, l1 = ax_rates.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax_rates.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)
  else:
    ax_rates.legend(loc="upper left", fontsize=8)

  # 2. Inflation & real policy
  for col, c, lab in (("CPI_YOY", "#E63946",
                       "CPI YoY"), ("FOOD_CPI_YOY", "#F4A261", "Food CPI YoY"),
                      ("REAL_FEDFUNDS", "#1D3557", "Real fed funds")):
    if col in o:
      s = o[col].dropna()
      ax_infl.plot(s.index,
                   s,
                   label=lab,
                   color=c,
                   linewidth=1.8,
                   marker="o",
                   markersize=2.5)
  ax_infl.axhline(2, color="gray", linestyle=":", label="2% target")
  ax_infl.axhline(0, color="black", linewidth=0.6)
  ax_infl.set_ylabel("%")
  ax_infl.set_title("Inflation vs real policy rate", fontweight="bold")
  ax_infl.legend(loc="upper left", fontsize=8)

  # 3. Credit & stress
  for col, c in (("HY_SPREAD", "#E63946"), ("BAA_SPREAD", "#F4A261"),
                 ("AAA_SPREAD", "#2A9D8F")):
    if col in d:
      ax_credit.plot(d.index,
                     d[col],
                     label=col.replace("_", " "),
                     color=c,
                     linewidth=1.6)
  ax_credit.set_ylabel("spread (%)")
  ax_credit.set_title("Credit spreads & financial stress", fontweight="bold")
  if "ST_LOUIS_FIN_STRESS" in d:
    ax3 = ax_credit.twinx()
    ax3.plot(d.index,
             d["ST_LOUIS_FIN_STRESS"],
             color="#6D597A",
             linewidth=1.2,
             linestyle="--",
             label="StL fin stress (rhs)")
    ax3.axhline(0, color="#6D597A", linewidth=0.5)
    ax3.set_ylabel("index")
    h1, l1 = ax_credit.get_legend_handles_labels()
    h2, l2 = ax3.get_legend_handles_labels()
    ax_credit.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)
  else:
    ax_credit.legend(loc="upper left", fontsize=8)

  # 4. Commodities & dollar (rebased to 100 at window start)
  for col, c in (("WTI_CRUDE", "#264653"), ("NAT_GAS_PRICE", "#2A9D8F"),
                 ("COPPER_PRICE", "#E76F51"), ("USD_INDEX", "#8D99AE")):
    if col in d:
      s = d[col].dropna()
      if not s.empty and s.iloc[0] != 0:
        ax_cmdty.plot(s.index,
                      s / s.iloc[0] * 100,
                      label=col,
                      color=c,
                      linewidth=1.6)
  ax_cmdty.axhline(100, color="black", linewidth=0.6)
  ax_cmdty.set_ylabel("rebased = 100")
  ax_cmdty.set_title("Commodities & dollar (rebased)", fontweight="bold")
  ax_cmdty.legend(loc="upper left", fontsize=8)

  for ax in axes.flat:
    ax.grid(True, alpha=0.3)
  fig.suptitle(f"Macro Regime Dashboard ({years}-Year)",
               fontweight="bold",
               fontsize=14)
  plt.tight_layout()
  plt.savefig(output_path, dpi=200)
  plt.close()


def plot_macro_timeline(df: pd.DataFrame, duration_label: str,
                        output_path: str) -> None:
  """Backward-compatible wrapper: Z-score panel for the fundamentals."""
  setup_plot_aesthetics()
  cols = [
      c for c in ("FEDFUNDS", "US10Y", "CPI_YOY", "HY_SPREAD")
      if c in df.columns
  ]
  if df.empty or not cols:
    return
  fig, ax = plt.subplots(figsize=(14, 5))
  for col, c in zip(cols, ["#1D3557", "#2A9D8F", "#E63946", "#F4A261"]):
    s = df[col].dropna()
    if s.std() > 0:
      ax.plot(s.index, (s - s.mean()) / s.std(),
              label=f"{col} (z)",
              color=c,
              linewidth=2)
  ax.axhline(0, color="gray", linestyle=":")
  ax.set_title(f"Macro Fundamentals z-scores ({duration_label})",
               fontweight="bold")
  ax.legend(loc="upper left", fontsize=9)
  ax.grid(True, alpha=0.3)
  plt.tight_layout()
  plt.savefig(output_path, dpi=200)
  plt.close()


def monthly_change_correlation(obs: pd.DataFrame,
                               cols: List[str],
                               years: int = 5) -> pd.DataFrame:
  """Correlation of MONTHLY CHANGES (not levels) over the window.

  Level correlations between trending series (CPI vs GDP ≈ 0.97) are
  spurious; changes answer "do these move together month to month?".
  Rates/spreads use differences, everything else percentage changes.
  """
  start = pd.Timestamp.today() - pd.DateOffset(years=years)
  monthly = obs[cols][obs.index >= start].resample("ME").last().ffill()
  chg = pd.DataFrame(index=monthly.index)
  for c in cols:
    chg[c] = monthly[c].diff() if c in RATE_LIKE else monthly[c].pct_change()
  chg = chg.replace([np.inf, -np.inf], np.nan).dropna(how="all")
  return chg.corr(min_periods=12)


def generate_macro_report() -> None:
  """Generates the macro regime report: dashboard, alerts, panels, tables."""
  if not os.path.exists(MACRO_TSV):
    logger.warning("Macro data missing at %s", MACRO_TSV)
    return
  logger.info("Generating Macro Economic Indicator Report...")
  os.makedirs(RENDERED_DIR, exist_ok=True)

  daily, obs = load_macro_observations(MACRO_TSV)
  daily, obs = add_derived_series(daily, obs)

  # Plots
  plot_regime_panels(daily, obs, 5,
                     os.path.join(RENDERED_DIR, "macro_regime_5yr.png"))
  plot_regime_panels(daily, obs, 1,
                     os.path.join(RENDERED_DIR, "macro_regime_1yr.png"))
  five = daily[daily.index >= pd.Timestamp.today() - pd.DateOffset(years=5)]
  plot_macro_timeline(five, "5-Year",
                      os.path.join(RENDERED_DIR, "macro_timeline_5yr.png"))
  plot_macro_timeline(
      five[five.index >= pd.Timestamp.today() - pd.DateOffset(years=1)],
      "1-Year", os.path.join(RENDERED_DIR, "macro_timeline_1yr.png"))

  # Correlation of monthly changes
  corr_cols = [
      c for c in ("US10Y", "YC_10Y_2Y", "FEDFUNDS", "CPI_YOY", "UNRATE",
                  "HY_SPREAD", "ST_LOUIS_FIN_STRESS", "WTI_CRUDE",
                  "COPPER_PRICE", "USD_INDEX", "UMICH_SENTIMENT",
                  "US_POLICY_UNCERTAINTY", "CHICAGO_FED_ACTIVITY", "TECH_PULSE")
      if c in obs.columns
  ]
  corr_text = "*Not enough data for correlation analysis.*"
  if corr_cols:
    corr_df = monthly_change_correlation(obs, corr_cols)
    setup_plot_aesthetics()
    plt.figure(figsize=(12, 10))
    sns.heatmap(corr_df,
                annot=True,
                cmap="coolwarm",
                center=0,
                fmt=".2f",
                linewidths=0.5,
                cbar_kws={"shrink": 0.8},
                vmin=-1,
                vmax=1)
    plt.title("Correlation of Monthly Changes (5-Year)",
              fontweight="bold",
              fontsize=13,
              pad=15)
    plt.tight_layout()
    plt.savefig(os.path.join(RENDERED_DIR, "macro_correlation.png"), dpi=200)
    plt.close()
    corr_vals: Dict[Tuple[str, str], float] = {
        (a, b): float(str(corr_df.loc[a, b])) for i, a in enumerate(corr_cols)
        for b in corr_cols[i + 1:]
        if pd.notna(corr_df.loc[a, b])
    }
    pairs = [(a, b, v) for (a, b), v in corr_vals.items()]
    pairs.sort(key=lambda x: x[2], reverse=True)
    corr_text = "### Move together (top +)\n" + "\n".join(
        f"- **{a}** & **{b}**: `{v:+.2f}`" for a, b, v in pairs[:5])
    corr_text += "\n\n### Move opposite (top −)\n" + "\n".join(
        f"- **{a}** & **{b}**: `{v:+.2f}`" for a, b, v in pairs[-5:][::-1])

  # Tables
  table, alerts = build_indicator_rows(obs)
  alerts_text = ("\n".join(alerts) if alerts else
                 "- *No ≥2σ levels, ≥2.5σ jumps or stale series.*")

  def _fmt_row(r: pd.Series) -> List[Any]:
    latest = r["Latest"]
    latest_s = (f"{latest:,.2f}" if abs(latest) < 1e5 else f"{latest:,.0f}")
    z = f"{r['5Y Z']:+.1f}" if pd.notna(r["5Y Z"]) else "—"
    pct = f"{r['5Y pct']:.0f}" if pd.notna(r["5Y pct"]) else "—"
    flag = " ⏳" if r["Stale"] else ""
    return [
        r["Indicator"] + flag, latest_s, r["Δ1M"], r["Δ3M"], r["Δ1Y"], z, pct,
        r["Trend"], r["As of"]
    ]

  headers = [
      "Indicator", "Latest", "Δ1M", "Δ3M", "Δ1Y", "5Y Z", "5Y pct", "3M",
      "As of"
  ]
  group_md = ""
  seen: set = set()
  for group, cols in MACRO_GROUPS.items():
    sub = table[table["Indicator"].isin(cols)]
    if sub.empty:
      continue
    seen.update(sub["Indicator"])
    sub = sub.assign(_o=sub["Indicator"].map(cols.index)).sort_values("_o")
    body = tabulate([_fmt_row(r) for _, r in sub.iterrows()],
                    headers=headers,
                    tablefmt="github")
    if group.startswith("Structural"):
      group_md += (f"\n<details><summary>{group}</summary>\n\n{body}\n\n"
                   "</details>\n")
    else:
      group_md += f"\n### {group}\n{body}\n"
  rest = table[~table["Indicator"].isin(seen)]
  if not rest.empty:
    group_md += "\n### Other\n" + tabulate(
        [_fmt_row(r) for _, r in rest.iterrows()],
        headers=headers,
        tablefmt="github") + "\n"

  extremes = table.dropna(subset=["5Y Z"]).reindex(
      table["5Y Z"].abs().sort_values(ascending=False).index).head(8)
  extremes_md = tabulate(
      [[
          r["Indicator"], f"{r['Latest']:,.2f}"
          if abs(r["Latest"]) < 1e5 else f"{r['Latest']:,.0f}",
          f"{r['5Y Z']:+.1f}", f"{r['5Y pct']:.0f}", r["Δ3M"], r["Trend"]
      ] for _, r in extremes.iterrows()],
      headers=["Indicator", "Latest", "5Y Z", "pct", "Δ3M", "3M"],
      tablefmt="github")

  report_md = f"""# Macroeconomic Regime Report

*Generated {datetime.date.today():%Y-%m-%d}. All statistics are computed on
native FRED observations (not the forward-filled daily grid); Δ columns are
percentage changes for levels and percentage-point (pp) changes for rates,
spreads and ratios.*

## Regime Read
{regime_summary(obs)}

## Alerts
{alerts_text}

## Most Extreme vs 5-Year History
{extremes_md}

## Regime Dashboard (5-Year)
![Regime 5Y](rendered/macro_regime_5yr.png)

## Regime Dashboard (1-Year)
![Regime 1Y](rendered/macro_regime_1yr.png)

*How to read*: top-left shows the policy rate against the curve with 10s2s
inversions shaded; top-right compares headline/food inflation with the real
policy rate (positive = restrictive); bottom-left is credit stress; bottom
right rebases commodities and the dollar to 100 at the window start.

## Correlation of Monthly Changes (5-Year)
{corr_text}

![Correlation Matrix](rendered/macro_correlation.png)

## Indicator Dashboard
{group_md}
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
  # Fetcher semantics: 1.0 = baseline traffic, >1 = busier than normal.
  bar_colors = [
      "#2A9D8F" if x < 1.2 else "#F4A261" if x < 2.0 else "#E63946"
      for x in latest_df["Congestion_Index"]
  ]
  bars = ax_bar.barh(
      latest_df["Chokepoint_Name"],
      latest_df["Congestion_Index"],
      color=bar_colors,
      alpha=0.85,
  )
  ax_bar.set_xlim(0, max(1.5, latest_df["Congestion_Index"].max() * 1.2))
  ax_bar.axvline(1.0, color="gray", linestyle=":", linewidth=1)
  ax_bar.set_title(
      "Chokepoint Congestion Index",
      fontweight="bold",
      fontsize=12,
  )
  ax_bar.set_xlabel("Congestion index (1.0 = baseline; >2 = bottleneck)")
  ax_bar.grid(True, alpha=0.3)

  for bar_patch, vessels in zip(bars, latest_df["Vessel_Count"]):
    width = bar_patch.get_width()
    ax_bar.text(
        width + 0.02,
        bar_patch.get_y() + bar_patch.get_height() / 2,
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
          headers=list(sm_summary_df.columns),
          tablefmt="github",
      )

      macro_section = f"""
## Shipping Macro Metrics
{sm_summary_md}
"""

  report_md = f"""# Maritime Shipping Report

## Overview
This report monitors global maritime chokepoints (Strait of Hormuz, Malacca Strait, Panama Canal, Taiwan Strait) and macroeconomic freight indicators to track supply chain bottlenecks, tanker availability, and logistical disruptions.

> [!WARNING]
> Chokepoint counts come from a ~20-second AISStream sample and fall back to a static baseline (index 1.0) when the sample is empty, so most rows are placeholders. Treat this section as a plumbing demo until a real source (IMF PortWatch daily transits, NY Fed GSCPI, Freightos FBX) is wired in.

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
