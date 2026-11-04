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

POLITICAL_ODDS_TSV = os.path.join(config.MARKET_DATA_DIR, "political",
                                  "political_odds.tsv")
POLITICAL_EVENTS_TSV = os.path.join(config.MARKET_DATA_DIR, "political",
                                    "political_events.tsv")
# Odds older than this (days) trigger a staleness warning.
POLITICAL_STALE_DAYS = 2
# Movers table ignores thin sub-markets below this lifetime volume (USD).
POLITICAL_MOVER_MIN_VOLUME = 10_000
# (label, key, outcome); outcome None = top outcome on the latest date.
POLITICAL_DASHBOARD: List[Tuple[str, str, Optional[str]]] = [
    ("House → Democrats", "house_2026", "Democratic Party"),
    ("Senate → Democrats", "senate_2026", "Democratic Party"),
    ("Dec FOMC (top)", "fed_decision_dec_2026", None),
    ("Fed cuts in 2026 (top)", "fed_cuts_2026", None),
    ("Fed funds end-2026 (top)", "fed_rate_end_2026", None),
    ("10Y high 2026 (top bucket)", "us10y_high_2026", None),
    ("Shutdown by Dec 31", "gov_shutdown", "December 31"),
    ("US recession 2026", "us_recession_2026", "Yes"),
    ("Taiwan invasion 2026", "china_taiwan_invasion", "Yes"),
    ("Taiwan invasion by 2027", "china_taiwan_invasion_2027", "Yes"),
    ("Hormuz normal by Dec 31", "hormuz_traffic_normal", "Yes"),
    ("Anthropic IPO by Dec 15", "anthropic_ipo", "December 15, 2026"),
    ("Trump approve (14d)", "approval_trump", "Approve"),
    ("Trump disapprove (14d)", "approval_trump", "Disapprove"),
]
# (label, key, outcome) for the geopolitics tail-risk dashboard.
POLITICAL_TAIL_RISKS: List[Tuple[str, str, Optional[str]]] = [
    ("China invades Taiwan 2026", "china_taiwan_invasion", "Yes"),
    ("China invades Taiwan by 2027", "china_taiwan_invasion_2027", "Yes"),
    ("China–Taiwan clash", "china_taiwan_clash", "Yes"),
    ("China–Taiwan blockade", "china_taiwan_blockade", "Yes"),
    ("US–China military clash", "us_china_military_clash", "Yes"),
    ("US invades Iran", "us_invade_iran", "Yes"),
    ("Iran regime falls 2026", "iran_regime_fall_2026", "Yes"),
    ("Hormuz traffic normal", "hormuz_traffic_normal", "Yes"),
    ("US acquires Greenland", "greenland_acquire", "Yes"),
    ("US strikes Cuba", "us_strike_cuba", "Yes"),
    ("NK invades SK", "nk_invade_sk", "Yes"),
    ("India–Pakistan strike", "india_pakistan_strike", "Yes"),
    ("Ukraine joins NATO", "ukraine_nato", "Yes"),
    ("US default 2027", "us_default_2027", "Yes"),
    ("Fed emergency cut", "fed_emergency_cut", "Yes"),
    ("AI bubble burst (top)", "ai_bubble_burst", None),
    ("US recession 2026", "us_recession_2026", "Yes"),
]
# Section title -> (categories, plots embedded under the section).
POLITICAL_SECTIONS: Dict[str, Tuple[List[str], List[str]]] = {
    "Elections": (["elections", "elections_2028", "approval"],
                  ["political_elections.png", "political_approval.png"]),
    "Fed & Rates": (["fed", "rates"], ["political_fed_rates.png"]),
    "Fiscal, Economy & Trade":
        (["fiscal", "economy", "trade", "energy", "domestic"], []),
    "Geopolitics": (["geopolitics"], ["political_geopolitics.png"]),
    "Markets & IPOs": (["markets"], []),
    "Foreign Politics": (["foreign_elections"], []),
}


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
        "WTI_CRUDE", "USD_INDEX", "USD_CNY", "USD_EUR", "USD_JPY"
    ],
    "Policy & Trade": [
        "US_POLICY_UNCERTAINTY", "EUROPE_POLICY_UNCERTAINTY", "TARIFFS",
        "CHINA_IMPORTS", "TECH_PULSE", "RD_INVESTMENT"
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

  active_indicators = {ind for group in MACRO_GROUPS.values() for ind in group}

  for col in obs.columns:
    if col not in active_indicators:
      continue
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

  # 4. Energy & FX (rebased to 100 at window start)
  for col, c in (("WTI_CRUDE", "#264653"), ("USD_INDEX", "#8D99AE"),
                 ("USD_CNY", "#E76F51"), ("USD_EUR", "#2A9D8F")):
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
  ax_cmdty.set_title("Energy & FX (rebased)", fontweight="bold")
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
        if str(corr_df.loc[a, b]).lower() != "nan"
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
This report monitors global maritime chokepoints (Strait of Hormuz, Malacca Strait, Suez Canal, Bab el-Mandeb, Panama Canal, Taiwan Strait) and macroeconomic freight indicators to track supply chain bottlenecks, tanker availability, and logistical disruptions.

> [!NOTE]
> Chokepoint transit counts and congestion indices are sourced from IMF PortWatch daily transit calls data (covering Hormuz, Malacca, Suez, Bab el-Mandeb, Panama, and Taiwan Strait). Baseline indices reflect normalized pre-disruption transit volume (1.0 = normal baseline).

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


# ---------------------------------------------------------------------------
# Political sentiment report: prediction-market odds + approval + calendar
# ---------------------------------------------------------------------------


def _fmt_prob(x: float) -> str:
  return "—" if pd.isna(x) else f"{x * 100:.1f}%"


def _fmt_pp(x: float) -> str:
  return "—" if pd.isna(x) else f"{x * 100:+.1f}"


def _fmt_volume(x: float) -> str:
  return f"${x / 1e6:.1f}M" if x >= 1e6 else f"${x / 1e3:.0f}K"


def _latest_and_deltas(
    df: pd.DataFrame,
    key: str,
    outcome: Optional[str] = None) -> Optional[Dict[str, Any]]:
  """Latest probability of a (key, outcome) and its 1/7/30-day changes.

  "Now" is the key's own latest date (approval polls lag the odds by weeks)
  and each delta compares against the nearest prior print on or before the
  target date, so sparse histories degrade to NaN rather than crash.

  Args:
    df: Long-format political odds frame with a datetime ``Date`` column.
    key: Config key (e.g. ``house_2026``).
    outcome: Sub-market label; None picks the top outcome on the latest date.

  Returns:
    Dict with key, outcome, category, prob, d1, d7, d30, volume, date; or
    None when the key/outcome is absent.
  """
  sub = df[df["Key"] == key]
  if sub.empty:
    return None
  if outcome is None:
    latest = sub[sub["Date"] == sub["Date"].max()]
    outcome = str(
        latest.sort_values("Prob", ascending=False)["Outcome"].iloc[0])
  sub = sub[sub["Outcome"] == outcome].sort_values("Date")
  if sub.empty:
    return None
  s = sub.set_index("Date")["Prob"].astype(float)
  now, when = float(s.iloc[-1]), s.index[-1]
  return {
      "key": key,
      "outcome": outcome,
      "category": str(sub["Category"].iloc[-1]),
      "prob": now,
      "d1": now - _nearest_before(s, when - pd.Timedelta(days=1)),
      "d7": now - _nearest_before(s, when - pd.Timedelta(days=7)),
      "d30": now - _nearest_before(s, when - pd.Timedelta(days=30)),
      "volume": float(sub["Volume_USD"].iloc[-1]),
      "date": when,
  }


def _political_snapshot(df: pd.DataFrame) -> pd.DataFrame:
  """One row per (Key, Outcome) with latest prob, deltas and volume."""
  pairs = df[["Key", "Outcome"]].drop_duplicates().itertuples(index=False)
  rows = [_latest_and_deltas(df, k, o) for k, o in pairs]
  return pd.DataFrame([r for r in rows if r is not None])


def _political_series(df: pd.DataFrame, key: str, outcome: str) -> pd.Series:
  sub = df[(df["Key"] == key) & (df["Outcome"] == outcome)].sort_values("Date")
  return sub.set_index("Date")["Prob"].astype(float)


def _bar_distribution(ax: Any, snap: pd.DataFrame, key: str,
                      title: str) -> None:
  """Horizontal bars of the current outcome distribution for one key."""
  d = snap[snap["key"] == key].sort_values("prob")
  if d.empty:
    ax.set_visible(False)
    return
  ax.barh(d["outcome"], d["prob"] * 100, color="#457B9D", alpha=0.85)
  for y, (p, d7) in enumerate(zip(d["prob"], d["d7"])):
    ax.text(p * 100 + 1,
            y,
            f"{p*100:.0f}% ({_fmt_pp(d7)} 7d)",
            va="center",
            fontsize=8)
  ax.set_xlim(0, 115)
  ax.set_title(title, fontweight="bold", fontsize=10)
  ax.tick_params(axis="y", labelsize=8)
  ax.grid(True, axis="x", alpha=0.3)


def _plot_political_elections(df: pd.DataFrame, snap: pd.DataFrame,
                              path: str) -> None:
  """House/Senate Dem-control timeline + 2028 nominee/winner top-5 odds."""
  setup_plot_aesthetics()
  fig, (ax_tl, ax_bar) = plt.subplots(1, 2, figsize=(16, 7))
  for key, c, lab in (("house_2026", "#1D3557", "House → Dem"),
                      ("senate_2026", "#E63946", "Senate → Dem")):
    s = _political_series(df, key, "Democratic Party")
    if not s.empty:
      ax_tl.plot(s.index, s * 100, label=lab, color=c, linewidth=2)
  ax_tl.axhline(50, color="gray", linestyle=":", linewidth=1)
  ax_tl.set_ylim(0, 100)
  ax_tl.set_ylabel("Probability (%)")
  ax_tl.set_title("2026 Midterms: Democratic control", fontweight="bold")
  ax_tl.legend(loc="lower right", fontsize=9)
  ax_tl.grid(True, alpha=0.3)
  ax_tl.tick_params(axis="x", rotation=30)

  labels, vals, colors = [], [], []
  for key, c, prefix in (("pres_winner_2028", "#6D597A",
                          "Winner"), ("gop_nominee_2028", "#E63946", "GOP"),
                         ("dem_nominee_2028", "#1D3557", "Dem")):
    top = snap[snap["key"] == key].nlargest(5, "prob").sort_values("prob")
    for _, r in top.iterrows():
      labels.append(f"{prefix}: {r['outcome']}")
      vals.append(r["prob"] * 100)
      colors.append(c)
  if vals:
    ax_bar.barh(labels, vals, color=colors, alpha=0.85)
    for y, v in enumerate(vals):
      ax_bar.text(v + 0.5, y, f"{v:.0f}%", va="center", fontsize=8)
    ax_bar.tick_params(axis="y", labelsize=8)
  ax_bar.set_xlabel("Probability (%)")
  ax_bar.set_title("2028: nominee & winner odds (top 5)", fontweight="bold")
  ax_bar.grid(True, axis="x", alpha=0.3)
  plt.tight_layout()
  plt.savefig(path, dpi=300)
  plt.close()


def _plot_political_fed_rates(df: pd.DataFrame, snap: pd.DataFrame,
                              path: str) -> None:
  """Fed/rates distributions (left) and top-outcome timelines (right)."""
  setup_plot_aesthetics()
  fig = plt.figure(figsize=(16, 11))
  gs = fig.add_gridspec(4, 2, width_ratios=[1, 1.15], hspace=0.6)
  dists = (("fed_decision_dec_2026", "Dec 2026 FOMC decision"),
           ("fed_cuts_2026", "Number of Fed cuts in 2026"),
           ("fed_rate_end_2026", "Fed funds upper bound, end-2026"),
           ("fed_rate_end_2027", "Fed funds upper bound, end-2027"))
  for i, (key, title) in enumerate(dists):
    _bar_distribution(fig.add_subplot(gs[i, 0]), snap, key, title)

  ax_tl = fig.add_subplot(gs[:, 1])
  for key, c in (("fed_decision_dec_2026", "#1D3557"), ("us10y_high_2026",
                                                        "#E63946")):
    top = _latest_and_deltas(df, key)
    if top is None:
      continue
    s = _political_series(df, key, top["outcome"])
    ax_tl.plot(s.index,
               s * 100,
               color=c,
               linewidth=2,
               label=f"{key}: {top['outcome']}")
  ax_tl.set_ylim(0, 100)
  ax_tl.set_ylabel("Probability (%)")
  ax_tl.set_title("Top-outcome probability over time", fontweight="bold")
  ax_tl.legend(loc="upper left", fontsize=9)
  ax_tl.grid(True, alpha=0.3)
  ax_tl.tick_params(axis="x", rotation=30)
  plt.savefig(path, dpi=300, bbox_inches="tight")
  plt.close()


def _plot_political_geopolitics(df: pd.DataFrame, path: str) -> None:
  """Tail-risk dashboard: current Yes-prob bars coloured by 30-day change."""
  rows = [
      r for r in (_latest_and_deltas(df, k, o)
                  for _, k, o in POLITICAL_TAIL_RISKS) if r is not None
  ]
  if not rows:
    return
  labels = {k: lab for lab, k, _ in POLITICAL_TAIL_RISKS}
  d = pd.DataFrame(rows).sort_values("prob")
  d30 = d["d30"].fillna(0.0) * 100
  span = max(5.0, float(d30.abs().max()))
  norm = plt.Normalize(-span, span)
  cmap = plt.get_cmap("coolwarm")

  setup_plot_aesthetics()
  fig, ax = plt.subplots(figsize=(13, 8))
  ax.barh([labels[k] for k in d["key"]],
          d["prob"] * 100,
          color=cmap(norm(d30.values)),
          edgecolor="black",
          linewidth=0.4)
  for y, (p, c) in enumerate(zip(d["prob"], d["d30"])):
    ax.text(p * 100 + 0.8,
            y,
            f"{p*100:.0f}%  ({_fmt_pp(c)} 30d)",
            va="center",
            fontsize=8)
  sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
  sm.set_array([])
  fig.colorbar(sm, ax=ax, pad=0.02).set_label("30-day change (pp)")
  ax.set_xlim(0, 115)
  ax.set_xlabel("Current probability (%)")
  ax.set_title("Geopolitical & market tail risks (red = rising)",
               fontweight="bold")
  ax.grid(True, axis="x", alpha=0.3)
  plt.tight_layout()
  plt.savefig(path, dpi=300)
  plt.close()


def _plot_political_approval(df: pd.DataFrame, snap: pd.DataFrame,
                             path: str) -> None:
  """Approve/Disapprove 14d-average timeline + approval-low-2026 buckets."""
  setup_plot_aesthetics()
  fig, (ax_tl, ax_bar) = plt.subplots(1,
                                      2,
                                      figsize=(16, 6),
                                      gridspec_kw={"width_ratios": [1.6, 1]})
  for outcome, c in (("Approve", "#2A9D8F"), ("Disapprove", "#E63946")):
    s = _political_series(df, "approval_trump", outcome)
    if not s.empty:
      ax_tl.plot(s.index, s * 100, label=outcome, color=c, linewidth=2)
  ax_tl.set_ylabel("Share (%)")
  ax_tl.set_title("Trump job approval (14-day poll average, VoteHub)",
                  fontweight="bold")
  ax_tl.legend(loc="center left", fontsize=9)
  ax_tl.grid(True, alpha=0.3)
  _bar_distribution(ax_bar, snap, "approval_low_2026",
                    "Lowest approval in 2026 (Polymarket)")
  plt.tight_layout()
  plt.savefig(path, dpi=300)
  plt.close()


def _political_read_through(get: Any) -> List[str]:
  """Threshold rules over dashboard probabilities -> 4-6 bullets."""
  bullets: List[str] = []
  fomc = get("fed_decision_dec_2026", None)
  if fomc:
    p = fomc["prob"] * 100
    if "increase" in fomc["outcome"] and p > 60:
      bullets.append(f"**Rates gate unlikely to release**: Dec FOMC "
                     f"`{fomc['outcome']}` at {p:.0f}% — hike priced.")
    elif "decrease" in fomc["outcome"] and p > 60:
      bullets.append(f"**Easing priced**: Dec FOMC `{fomc['outcome']}` "
                     f"at {p:.0f}%.")
    else:
      bullets.append(f"**Dec FOMC contested**: top outcome "
                     f"`{fomc['outcome']}` only {p:.0f}%.")
  hormuz = get("hormuz_traffic_normal", "Yes")
  if hormuz:
    p = hormuz["prob"] * 100
    bullets.append(
        f"**Oil tail open**: Hormuz-normal-by-Dec-31 only {p:.0f}%." if p <
        25 else f"**Hormuz normalization priced** at {p:.0f}%.")
  house, senate = get("house_2026",
                      "Democratic Party"), get("senate_2026",
                                               "Democratic Party")
  if house and senate:
    h, s = house["prob"] * 100, senate["prob"] * 100
    if h > 90 and s > 90:
      bullets.append(f"**Gridlock priced**: Dem House {h:.0f}% / Senate "
                     f"{s:.0f}% — expect veto politics, little fiscal "
                     "legislation.")
    elif h < 50 and s < 50:
      bullets.append(f"**Unified GOP control favored**: Dem House {h:.0f}% "
                     f"/ Senate {s:.0f}%.")
    else:
      bullets.append(f"**Split-control base case**: Dem House {h:.0f}% / "
                     f"Senate {s:.0f}%.")
  tw = get("china_taiwan_invasion_2027", "Yes")
  if tw and tw["prob"] * 100 > 8:
    bullets.append(f"**Semis supply-chain tail**: Taiwan invasion by 2027 "
                   f"at {tw['prob']*100:.0f}%.")
  rec = get("us_recession_2026", "Yes")
  if rec:
    p = rec["prob"] * 100
    bullets.append(f"**Recession risk elevated**: 2026 recession {p:.0f}%."
                   if p > 30 else f"**Growth scare not priced**: 2026 "
                   f"recession only {p:.0f}%.")
  sd = get("gov_shutdown", "December 31")
  if sd and sd["prob"] * 100 > 50:
    bullets.append(f"**Fiscal noise ahead**: shutdown by Dec 31 at "
                   f"{sd['prob']*100:.0f}%.")
  return bullets[:6]


def generate_political_report() -> None:
  """Generates the political sentiment report from prediction-market odds."""
  if not os.path.exists(POLITICAL_ODDS_TSV):
    logger.warning("Political data missing at %s", POLITICAL_ODDS_TSV)
    return
  logger.info("Generating Political Sentiment Report...")
  os.makedirs(RENDERED_DIR, exist_ok=True)
  df = pd.read_csv(POLITICAL_ODDS_TSV, sep="\t")
  if df.empty or "Date" not in df.columns:
    logger.warning("Political odds TSV empty or malformed. Skipping report.")
    return
  df["Date"] = pd.to_datetime(df["Date"])
  snap = _political_snapshot(df)
  cache: Dict[Tuple[str, Optional[str]], Optional[Dict[str, Any]]] = {}

  def get(key: str, outcome: Optional[str]) -> Optional[Dict[str, Any]]:
    if (key, outcome) not in cache:
      cache[(key, outcome)] = _latest_and_deltas(df, key, outcome)
    return cache[(key, outcome)]

  # Plots
  _plot_political_elections(
      df, snap, os.path.join(RENDERED_DIR, "political_elections.png"))
  _plot_political_fed_rates(
      df, snap, os.path.join(RENDERED_DIR, "political_fed_rates.png"))
  _plot_political_geopolitics(
      df, os.path.join(RENDERED_DIR, "political_geopolitics.png"))
  _plot_political_approval(df, snap,
                           os.path.join(RENDERED_DIR, "political_approval.png"))

  # Header / staleness
  data_as_of = df["Date"].max()
  stale_days = (pd.Timestamp(datetime.date.today()) - data_as_of).days
  stale_md = ""
  if stale_days > POLITICAL_STALE_DAYS:
    stale_md = (f"\n> [!WARNING]\n> Odds are **{stale_days} days stale** "
                f"(last print {data_as_of:%Y-%m-%d}); run "
                "`make political-fetch`.\n")

  # Regime dashboard
  dash_rows: List[List[Any]] = []
  missing: List[str] = []
  for label, key, outcome in POLITICAL_DASHBOARD:
    r = get(key, outcome)
    if r is None:
      missing.append(f"{key}/{outcome or 'top'}")
      continue
    dash_rows.append([
        label, r["outcome"],
        _fmt_prob(r["prob"]),
        _fmt_pp(r["d1"]),
        _fmt_pp(r["d7"]),
        _fmt_pp(r["d30"]), f"{r['date']:%Y-%m-%d}"
    ])
  if missing:
    logger.warning("Political dashboard keys missing: %s", ", ".join(missing))
  dash_md = tabulate(
      dash_rows,
      headers=["Signal", "Outcome", "Prob", "Δ1d", "Δ7d", "Δ30d", "As of"],
      tablefmt="github",
      disable_numparse=True)

  # Biggest movers (7d), excluding approval and thin markets
  mv = snap[(snap["category"] != "approval") &
            (snap["volume"] >= POLITICAL_MOVER_MIN_VOLUME)].dropna(
                subset=["d7"])
  mv = mv.reindex(mv["d7"].abs().sort_values(ascending=False).index).head(12)
  movers_md = tabulate(
      [[
          r["key"], r["outcome"],
          _fmt_prob(r["prob"]),
          _fmt_pp(r["d1"]),
          _fmt_pp(r["d7"]),
          _fmt_pp(r["d30"]),
          _fmt_volume(r["volume"])
      ] for _, r in mv.iterrows()],
      headers=["Key", "Outcome", "Prob", "Δ1d", "Δ7d", "Δ30d", "Volume"],
      tablefmt="github",
      disable_numparse=True)

  # Per-category sections: top-3 outcomes per key
  sections_md = ""
  for title, (cats, plots) in POLITICAL_SECTIONS.items():
    sub = snap[snap["category"].isin(cats)]
    if sub.empty:
      continue
    rows = []
    for k, g in sub.groupby("key", sort=True):
      for _, row in g.nlargest(3, "prob").iterrows():
        rows.append([
            str(k), row["outcome"],
            _fmt_prob(row["prob"]),
            _fmt_pp(row["d7"])
        ])
    body = tabulate(rows,
                    headers=["Key", "Outcome", "Prob", "Δ7d"],
                    tablefmt="github",
                    disable_numparse=True)
    imgs = "".join(f"\n![{p}](rendered/{p})\n" for p in plots)
    sections_md += f"\n### {title}\n{body}\n{imgs}"

  # Upcoming events (next 90 days)
  events_md = "*No events calendar found.*"
  if os.path.exists(POLITICAL_EVENTS_TSV):
    ev = pd.read_csv(POLITICAL_EVENTS_TSV, sep="\t")
    ev["Date"] = pd.to_datetime(ev["Date"])
    today = pd.Timestamp(datetime.date.today())
    ev = ev[(ev["Date"] >= today) &
            (ev["Date"] <= today + pd.Timedelta(days=90))].sort_values("Date")
    events_md = tabulate([[
        f"{r['Date']:%Y-%m-%d}", r["Event"], r["Category"],
        "" if pd.isna(r["Notes"]) else r["Notes"]
    ] for _, r in ev.iterrows()],
                         headers=["Date", "Event", "Category", "Notes"],
                         tablefmt="github")

  read_md = "\n".join(f"- {b}" for b in _political_read_through(get))

  report_md = f"""# Political Sentiment Report

*Generated {datetime.date.today():%Y-%m-%d}. Probabilities are Polymarket
Yes-prices (0–100%); Δ columns are percentage-point changes versus the
nearest prior print 1 / 7 / 30 days earlier.*

> [!NOTE]
> Sources: Polymarket Gamma/CLOB (odds, volume) and VoteHub (approval polls,
> 14-day trailing mean). Data as of {data_as_of:%Y-%m-%d}.
{stale_md}
## Regime Dashboard
{dash_md}

## Biggest Movers (7-day, volume ≥ ${POLITICAL_MOVER_MIN_VOLUME/1e3:.0f}K)
{movers_md}

## Market Read-Through
{read_md}

## Markets by Category
{sections_md}
## Upcoming Key Events (next 90 days)
{events_md}
"""
  report_path = os.path.join(REPORTS_DIR, "news", "POLITICAL_REPORT.md")
  with open(report_path, "w", encoding="utf-8") as f:
    f.write(clean_md(report_md))
  logger.info("Generated %s", report_path)
  render_markdown_to_pdf(report_path)


if __name__ == "__main__":
  generate_macro_report()
  generate_shipping_report()
  generate_political_report()
