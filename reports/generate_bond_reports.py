"""Bond-market & fixed-income account report generator.

Produces the plots and metric tables behind a "what do today's yields mean
for my bond account" report. Generic math (macro access, rate-shock
approximations, synthetic Treasury history, valuation / tax helpers) lives
in ``reports.report_utils``; this module holds the *bond-portfolio specific*
pieces: ETF reference data (duration, credit bucket, forward-yield proxy),
account enrichment, scenario definitions and the plot / markdown outputs.

Usage:
    venv/bin/python3 reports/generate_bond_reports.py \\
        --account portfolios/tsvs/<bond_account>.tsv \\
        --out reports/10-13_portfolio_bond_yields --prefix 10_13 \\
        [--retirement portfolios/tsvs/<401k>.tsv] [--asof 2026-10-13]

Outputs (inside ``--out``):
    plots/<prefix>_*.png      figures referenced by REPORT.md
    bond_metrics.json         every computed number (machine readable)
    bond_metrics.md           markdown tables ready to paste into a report
"""

import argparse
import datetime
import glob
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tabulate import tabulate

REPORTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(REPORTS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

import config  # noqa: E402
from reports import report_utils as ru  # noqa: E402

matplotlib.use("Agg")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Bond-specific reference data
# ---------------------------------------------------------------------------
# Forward-yield proxies are (macro_column, spread_bp): estimate =
# economic_indicators[column] + spread_bp / 100. ``None`` falls back to the
# trailing 12M distribution yield in fundamentals.tsv (lags by ~6 months in
# a fast-moving rate environment). Durations are approximate effective
# durations (years) from issuer fact sheets; HY spread duration ≈ duration.
# yapf: disable
BOND_ETF_REFERENCE: Dict[str, Dict[str, Any]] = {
    # --- Cash-like: T-bills & floating rate (reprice within weeks) ---
    "SGOV":  {"name": "iShares 0-3M Treasury", "bucket": "T-Bill / Floating",
              "credit": "Treasury", "duration": 0.1,
              "yield_proxy": ("US03M", 0)},
    "SHV":   {"name": "iShares 0-1Y Treasury", "bucket": "T-Bill / Floating",
              "credit": "Treasury", "duration": 0.3,
              "yield_proxy": ("US03M", 0)},
    "GBIL":  {"name": "GS Access Treasury 0-1Y", "bucket": "T-Bill / Floating",
              "credit": "Treasury", "duration": 0.3,
              "yield_proxy": ("US03M", 5)},
    "VBIL":  {"name": "Vanguard 0-3M Treasury", "bucket": "T-Bill / Floating",
              "credit": "Treasury", "duration": 0.1,
              "yield_proxy": ("US03M", 0)},
    "FLRN":  {"name": "SPDR IG Floating Rate", "bucket": "T-Bill / Floating",
              "credit": "IG Corp", "duration": 0.1,
              "yield_proxy": ("SOFR", 60)},
    "FLTR":  {"name": "VanEck IG Floating Rate", "bucket": "T-Bill / Floating",
              "credit": "IG Corp", "duration": 0.1,
              "yield_proxy": ("SOFR", 70)},
    "VUSB":  {"name": "Vanguard Ultra-Short Bond", "bucket": "T-Bill / Floating",
              "credit": "IG Corp", "duration": 0.9,
              "yield_proxy": ("SOFR", 55)},
    "VMFXX": {"name": "Vanguard Federal Money Mkt", "bucket": "T-Bill / Floating",
              "credit": "Treasury", "duration": 0.1,
              "yield_proxy": ("FEDFUNDS_UPPER", -12)},
    # --- Short Treasuries (1-3Y) ---
    "SCHO":  {"name": "Schwab 1-3Y Treasury", "bucket": "Short Treasury",
              "credit": "Treasury", "duration": 1.9,
              "yield_proxy": ("US02Y", 0)},
    "SHY":   {"name": "iShares 1-3Y Treasury", "bucket": "Short Treasury",
              "credit": "Treasury", "duration": 1.9,
              "yield_proxy": ("US02Y", 0)},
    "VGSH":  {"name": "Vanguard 1-3Y Treasury", "bucket": "Short Treasury",
              "credit": "Treasury", "duration": 1.9,
              "yield_proxy": ("US02Y", 0)},
    # --- Short IG corporates ---
    "VCSH":  {"name": "Vanguard 1-5Y IG Corp", "bucket": "Short IG Corp",
              "credit": "IG Corp", "duration": 2.6,
              "yield_proxy": ("US02Y", 95)},
    # --- High yield ---
    "SHYG":  {"name": "iShares 0-5Y High Yield", "bucket": "Short High Yield",
              "credit": "High Yield", "duration": 2.3,
              "yield_proxy": ("HY_YIELD", -20)},
    "SJNK":  {"name": "SPDR Short-Term High Yield", "bucket": "Short High Yield",
              "credit": "High Yield", "duration": 2.1,
              "yield_proxy": ("HY_YIELD", -20)},
    "HYLB":  {"name": "Xtrackers USD High Yield", "bucket": "Broad High Yield",
              "credit": "High Yield", "duration": 3.3,
              "yield_proxy": ("HY_YIELD", 0)},
    "USHY":  {"name": "iShares Broad USD High Yield", "bucket": "Broad High Yield",
              "credit": "High Yield", "duration": 3.4,
              "yield_proxy": ("HY_YIELD", 0)},
    "HYG":   {"name": "iShares iBoxx High Yield", "bucket": "Broad High Yield",
              "credit": "High Yield", "duration": 3.2,
              "yield_proxy": ("HY_YIELD", -30)},
    # --- Intermediate / aggregate ---
    "VGIT":  {"name": "Vanguard 3-10Y Treasury", "bucket": "Intermediate Treasury",
              "credit": "Treasury", "duration": 5.0,
              "yield_proxy": ("US05Y", 10)},
    "IEF":   {"name": "iShares 7-10Y Treasury", "bucket": "Intermediate Treasury",
              "credit": "Treasury", "duration": 7.3,
              "yield_proxy": ("US10Y", -10)},
    "BND":   {"name": "Vanguard Total Bond Market", "bucket": "Aggregate Bond",
              "credit": "IG Mix", "duration": 6.0,
              "yield_proxy": ("US10Y", 25)},
    "BNDX":  {"name": "Vanguard Total Intl Bond (hedged)",
              "bucket": "Aggregate Bond", "credit": "IG Mix", "duration": 7.0,
              "yield_proxy": None},
    "LQD":   {"name": "iShares IG Corporate", "bucket": "Long IG Corp",
              "credit": "IG Corp", "duration": 8.3,
              "yield_proxy": ("CORP_YIELD", 20)},
    "TIP":   {"name": "iShares TIPS", "bucket": "Inflation-Linked",
              "credit": "Treasury", "duration": 6.6,
              "yield_proxy": ("US10Y_REAL", 0)},
    # --- Long Treasuries ---
    "VGLT":  {"name": "Vanguard Long-Term Treasury", "bucket": "Long Treasury",
              "credit": "Treasury", "duration": 14.8,
              "yield_proxy": ("US30Y", -10)},
    "TLT":   {"name": "iShares 20+ Year Treasury", "bucket": "Long Treasury",
              "credit": "Treasury", "duration": 16.0,
              "yield_proxy": ("US30Y", 0)},
}
# yapf: enable

# 12-month scenarios: parallel Treasury shock, credit-spread shocks and
# realised High Yield losses (percent of the HY sleeve).
BOND_SCENARIOS: Dict[str, Dict[str, float]] = {
    "Base (curve unchanged)": {},
    "Two more hikes (+50bp, HY +50)": {
        "rate_bp": 50,
        "hy_spread_bp": 50
    },
    "Bear steepener (+100bp, HY +75)": {
        "rate_bp": 100,
        "hy_spread_bp": 75,
        "ig_spread_bp": 20
    },
    "Growth scare (-100bp, HY +250)": {
        "rate_bp": -100,
        "hy_spread_bp": 250,
        "ig_spread_bp": 50,
        "hy_default_pct": 1.5
    },
    "Recession (-200bp, HY +500)": {
        "rate_bp": -200,
        "hy_spread_bp": 500,
        "ig_spread_bp": 100,
        "hy_default_pct": 4.0
    },
    "2008-style (-300bp, HY +1200)": {
        "rate_bp": -300,
        "hy_spread_bp": 1200,
        "ig_spread_bp": 300,
        "hy_default_pct": 8.0
    },
}
BOND_SHOCKS_BP: Tuple[int, ...] = (-200, -150, -100, -50, 0, 50, 100, 150, 200)

# Benchmarks shown next to the account (label -> ticker).
BENCHMARKS: Dict[str, str] = {
    "T-Bills (SGOV)": "SGOV",
    "1-3Y Tsy (VGSH)": "VGSH",
    "3-10Y Tsy (VGIT)": "VGIT",
    "Total Bond (BND)": "BND",
    "20Y+ Tsy (TLT)": "TLT",
    "High Yield (HYG)": "HYG",
    "S&P 500 (SPY)": "SPY",
}
SHOCK_CURVE_TICKERS: Tuple[str, ...] = ("SGOV", "VGSH", "VGIT", "BND", "TLT")
SCENARIO_BENCHMARKS: Tuple[str, ...] = ("SGOV", "VGIT", "BND", "TLT", "HYG")

PALETTE = {
    "account": "#1D3557",
    "SGOV": "#8D99AE",
    "VGSH": "#457B9D",
    "VGIT": "#2A9D8F",
    "BND": "#E9C46A",
    "TLT": "#E76F51",
    "HYG": "#9B2226",
    "SPY": "#6A4C93",
}
ASSET_CLASS_COLORS = {
    "Employer Stock": "#9B2226",
    "Equity": "#457B9D",
    "Bond": "#2A9D8F",
    "Cash": "#8D99AE",
    "Crypto": "#E9C46A",
}

# ---------------------------------------------------------------------------
# Account enrichment & portfolio math (bond specific)
# ---------------------------------------------------------------------------


def forward_yield_estimate(
    ticker: str,
    macro_row: pd.Series,
    tickers_dir: Optional[str] = None) -> Optional[float]:
  """Estimates a forward (current-market) yield for a bond ETF.

  Args:
    ticker (str): ETF ticker.
    macro_row (pd.Series): A macro row (see ``report_utils.macro_asof``).
    tickers_dir (Optional[str]): ``market_data/tickers`` for the trailing
      distribution-yield fallback.

  Returns:
    Optional[float]: Yield in percent, or None if unknown.
  """
  ref = BOND_ETF_REFERENCE.get(ticker)
  if ref and ref.get("yield_proxy"):
    col, spread_bp = ref["yield_proxy"]
    val = macro_row.get(col)
    if val is not None and not pd.isna(val):
      return float(val) + spread_bp / 100.0
  if tickers_dir:
    trailing = ru.read_fundamental_metric(tickers_dir, ticker, "yield")
    if trailing is not None:
      return trailing * 100.0 if trailing < 1 else trailing
  return None


def load_bond_account(tsv_path: str) -> pd.DataFrame:
  """Loads a broker TSV and keeps positive-value rows with weights.

  Args:
    tsv_path (str): ``portfolios/tsvs/*.tsv`` export.

  Returns:
    pd.DataFrame: Holdings with a ``Weight`` column (percent).
  """
  df = ru.load_portfolio_tsv(tsv_path)
  df = df[df["Current_Value"].fillna(0) > 0].copy()
  total = df["Current_Value"].sum()
  df["Weight"] = df["Current_Value"] / total * 100.0 if total else 0.0
  return df.reset_index(drop=True)


def enrich_bond_holdings(df: pd.DataFrame,
                         macro: pd.DataFrame,
                         tickers_dir: str,
                         asof: Optional[Any] = None) -> pd.DataFrame:
  """Adds reference data, yields and expense ratios to account holdings.

  Args:
    df (pd.DataFrame): Output of :func:`load_bond_account`.
    macro (pd.DataFrame): Output of ``report_utils.load_macro_frame``.
    tickers_dir (str): ``market_data/tickers``.
    asof (Optional[Any]): Macro snapshot date (default: latest).

  Returns:
    pd.DataFrame: Copy with ``Name, Bucket, Credit, Duration, Fwd_Yield,
    Trailing_Yield, Expense_Ratio, Income_Fwd`` columns.
  """
  row = ru.macro_asof(macro, asof or macro.index.max())
  out = df.copy()
  cols: Dict[str, List[Any]] = {
      k: [] for k in ("Name", "Bucket", "Credit", "Duration", "Fwd_Yield",
                     "Trailing_Yield", "Expense_Ratio")
  }
  for t in out["Ticker"]:
    ref = BOND_ETF_REFERENCE.get(t, {})
    cols["Name"].append(ref.get("name", t))
    cols["Bucket"].append(ref.get("bucket", "Other"))
    cols["Credit"].append(ref.get("credit", "Unknown"))
    cols["Duration"].append(ref.get("duration", np.nan))
    cols["Fwd_Yield"].append(forward_yield_estimate(t, row, tickers_dir))
    ty = ru.read_fundamental_metric(tickers_dir, t, "yield")
    cols["Trailing_Yield"].append(ty *
                                  100.0 if ty is not None and ty < 1 else ty)
    cols["Expense_Ratio"].append(
        ru.read_fundamental_metric(tickers_dir, t, "netExpenseRatio"))
  for k, v in cols.items():
    out[k] = v
  out["Income_Fwd"] = out["Current_Value"] * out["Fwd_Yield"].fillna(0) / 100
  return out


def _weighted_average(values: pd.Series, weights: pd.Series) -> float:
  mask = values.notna() & weights.notna()
  if not mask.any() or weights[mask].sum() == 0:
    return float("nan")
  return float((values[mask] * weights[mask]).sum() / weights[mask].sum())


def portfolio_bond_stats(df: pd.DataFrame) -> Dict[str, Any]:
  """Aggregates an enriched holdings frame into portfolio-level stats.

  Args:
    df (pd.DataFrame): Output of :func:`enrich_bond_holdings`.

  Returns:
    Dict[str, Any]: ``total_value, duration, fwd_yield, trailing_yield,
    expense_ratio, breakeven_bp, income_fwd, credit_mix, bucket_mix``.
  """
  w = df["Current_Value"]
  total = float(w.sum())
  duration = _weighted_average(df["Duration"], w)
  fwd_yield = _weighted_average(df["Fwd_Yield"], w)
  breakeven = (fwd_yield / duration *
               100.0) if duration and duration > 0 else float("inf")

  def mix(col: str) -> Dict[str, float]:
    share = df.groupby(col)["Current_Value"].sum() / total * 100
    share = share.round(1).sort_values(ascending=False)
    return {str(k): float(v) for k, v in share.items()}

  return {
      "total_value": total,
      "duration": duration,
      "fwd_yield": fwd_yield,
      "trailing_yield": _weighted_average(df["Trailing_Yield"], w),
      "expense_ratio": _weighted_average(df["Expense_Ratio"], w),
      "breakeven_bp": breakeven,
      "income_fwd": float(df["Income_Fwd"].sum()),
      "credit_mix": mix("Credit"),
      "bucket_mix": mix("Bucket"),
  }


def bond_scenario_table(df: pd.DataFrame,
                        scenarios: Dict[str, Dict[str, float]],
                        horizon_years: float = 1.0) -> pd.DataFrame:
  """Runs rate + credit scenarios over an enriched holdings frame.

  Floating-rate / T-bill buckets take no price hit; half of the rate move
  flows into their carry instead (coupons reset).

  Args:
    df (pd.DataFrame): Output of :func:`enrich_bond_holdings`.
    scenarios (Dict[str, Dict[str, float]]): name -> shocks (``rate_bp``,
      ``hy_spread_bp``, ``ig_spread_bp``, ``hy_default_pct``).
    horizon_years (float): Carry horizon.

  Returns:
    pd.DataFrame: ``Portfolio_TR_%`` plus ``<Credit>_pp`` contributions.
  """
  total = df["Current_Value"].sum()
  rows = []
  for name, s in scenarios.items():
    rate = s.get("rate_bp", 0.0)
    contrib: Dict[str, float] = {}
    port = 0.0
    for _, h in df.iterrows():
      credit = h["Credit"]
      if credit == "High Yield":
        spread, loss = s.get("hy_spread_bp", 0.0), s.get("hy_default_pct", 0.0)
      elif credit in ("IG Corp", "IG Mix"):
        spread, loss = s.get("ig_spread_bp", 0.0), 0.0
      else:
        spread, loss = 0.0, 0.0
      dur = float(h["Duration"]) if pd.notna(h["Duration"]) else 0.0
      y = float(h["Fwd_Yield"]) if pd.notna(h["Fwd_Yield"]) else 0.0
      floating = h["Bucket"] == "T-Bill / Floating"
      tr = ru.rate_shock_return(y + ((rate / 100.0) * 0.5 if floating else 0),
                                dur,
                                0 if floating else rate,
                                spread_shock_bp=spread,
                                horizon_years=horizon_years,
                                default_loss_pct=loss)
      wgt = h["Current_Value"] / total
      port += tr * wgt
      contrib[credit] = contrib.get(credit, 0.0) + tr * wgt
    row = {"Scenario": name, "Portfolio_TR_%": round(port, 2)}
    row.update({f"{k}_pp": round(v, 2) for k, v in contrib.items()})
    rows.append(row)
  return pd.DataFrame(rows).set_index("Scenario")


def benchmark_frame(tickers: Sequence[str], macro_row: pd.Series,
                    tickers_dir: str) -> pd.DataFrame:
  """Builds a one-row-per-ETF frame shaped like an enriched account.

  Args:
    tickers (Sequence[str]): Benchmark tickers in BOND_ETF_REFERENCE.
    macro_row (pd.Series): Macro row for yield proxies.
    tickers_dir (str): ``market_data/tickers``.

  Returns:
    pd.DataFrame: Columns used by :func:`bond_scenario_table`.
  """
  rows = []
  for t in tickers:
    ref = BOND_ETF_REFERENCE[t]
    rows.append({
        "Ticker": t,
        "Current_Value": 100.0,
        "Bucket": ref["bucket"],
        "Credit": ref["credit"],
        "Duration": ref["duration"],
        "Fwd_Yield": forward_yield_estimate(t, macro_row, tickers_dir),
    })
  return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Price-history helpers
# ---------------------------------------------------------------------------


def load_adjusted_closes(tickers: Sequence[str], tickers_dir: str, start: Any,
                         end: Any) -> pd.DataFrame:
  """Loads adjusted closes (pipeline ``Close`` is dividend-adjusted).

  Args:
    tickers (Sequence[str]): Tickers with ``prices.tsv``.
    tickers_dir (str): ``market_data/tickers``.
    start (Any): Window start.
    end (Any): Window end.

  Returns:
    pd.DataFrame: Date index, one column per ticker, forward-filled.
  """
  frames = {}
  for t in tickers:
    path = os.path.join(tickers_dir, t, "prices.tsv")
    if not os.path.exists(path):
      logger.warning("No prices for %s", t)
      continue
    px = pd.read_csv(path, sep="\t", parse_dates=["Date"]).set_index("Date")
    frames[t] = pd.to_numeric(px["Close"], errors="coerce")
  df = pd.DataFrame(frames).sort_index().ffill()
  return df.loc[pd.Timestamp(start):pd.Timestamp(end)]


def growth_of_100(prices: pd.DataFrame,
                  weights: Optional[Dict[str, float]] = None) -> pd.DataFrame:
  """Rebases price columns to 100; optionally adds a fixed-weight blend.

  Args:
    prices (pd.DataFrame): Adjusted closes.
    weights (Optional[Dict[str, float]]): Ticker -> weight for an
      ``Account`` column (fixed weights, i.e. no drift / rebalancing).

  Returns:
    pd.DataFrame: Growth of 100 per column (+ ``Account`` when weighted).
  """
  base = prices.dropna(how="all").copy()
  rebased = base / base.iloc[0] * 100.0
  if weights:
    cols = [t for t in weights if t in rebased.columns]
    w = np.array([weights[t] for t in cols])
    w = w / w.sum()
    rebased["Account"] = (rebased[cols] * w).sum(axis=1)
  return rebased


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------


def _save(fig: plt.Figure, path: str) -> None:
  os.makedirs(os.path.dirname(path), exist_ok=True)
  fig.tight_layout()
  fig.savefig(path, dpi=160, bbox_inches="tight")
  plt.close(fig)
  logger.info("Saved %s", path)


def plot_curve_shift(curve: pd.DataFrame, policy_upper: float,
                     out: str) -> None:
  """Treasury curve snapshots (categorical tenor axis)."""
  fig, ax = plt.subplots(figsize=(10, 5.5))
  x = np.arange(len(curve.index))
  labels = [c for c in curve.columns if c != "Years"]
  styles = ["-", "--", "-.", ":"]
  for i, lbl in enumerate(labels):
    ax.plot(x,
            curve[lbl],
            marker="o",
            lw=2.4 if i == 0 else 1.6,
            ls=styles[i % len(styles)],
            label=lbl,
            color=["#1D3557", "#457B9D", "#2A9D8F", "#E9C46A"][i % 4])
  for xi, v in zip(x, curve[labels[0]]):
    ax.annotate(f"{v:.2f}%", (xi, v),
                textcoords="offset points",
                xytext=(0, 8),
                ha="center",
                fontsize=9,
                color="#1D3557")
  ax.axhline(policy_upper,
             color="#9B2226",
             ls="--",
             lw=1,
             label=f"Fed funds upper {policy_upper:.2f}%")
  ax.set_xticks(x)
  ax.set_xticklabels(curve.index)
  ax.set_ylabel("Yield (%)")
  ax.set_title("US Treasury curve: today vs. prior snapshots",
               fontweight="bold")
  ax.legend(loc="lower right")
  _save(fig, out)


def plot_yield_drivers(macro: pd.DataFrame, asof: pd.Timestamp,
                       out: str) -> None:
  """10Y decomposition (real / breakeven / term premium) + front end."""
  win = macro.loc[asof - pd.DateOffset(months=24):asof]
  fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
  ax = axes[0]
  for col, c, lbl in (("US10Y", "#1D3557", "10Y nominal"),
                      ("US10Y_REAL", "#2A9D8F", "10Y real (TIPS)"),
                      ("BREAKEVEN_10Y", "#E9C46A", "10Y breakeven infl."),
                      ("TERM_PREMIUM_10Y", "#E76F51", "10Y term premium")):
    if col in win.columns:
      s = win[col].dropna()
      ax.plot(s.index, s, color=c, lw=1.8, label=f"{lbl} ({s.iloc[-1]:.2f}%)")
  six_m = asof - pd.DateOffset(months=6)
  ax.axvspan(six_m, asof, color="grey", alpha=0.08)
  ax.set_title("What moved the 10Y: real yield, not inflation expectations",
               fontweight="bold")
  ax.set_ylabel("%")
  ax.legend(ncol=2, fontsize=9)
  ax = axes[1]
  for col, c, lbl in (("FEDFUNDS_UPPER", "#9B2226",
                       "Fed funds upper"), ("US03M", "#8D99AE", "3M bill"),
                      ("US02Y", "#457B9D", "2Y"), ("US05Y", "#2A9D8F", "5Y")):
    if col in win.columns:
      s = win[col].dropna()
      lab = f"{lbl} ({s.iloc[-1]:.2f}%)"
      if col == "FEDFUNDS_UPPER":
        ax.step(s.index, s, where="post", color=c, lw=1.8, label=lab)
      else:
        ax.plot(s.index, s, color=c, lw=1.8, label=lab)
  ax.axvspan(six_m, asof, color="grey", alpha=0.08)
  ax.set_title("Front end is pricing more hikes (2Y well above policy rate)",
               fontweight="bold")
  ax.set_ylabel("%")
  ax.legend(ncol=2, fontsize=9)
  _save(fig, out)


def plot_total_return(growth: pd.DataFrame, labels: Dict[str, str], title: str,
                      out: str) -> None:
  """Growth-of-100 lines with end-value labels."""
  fig, ax = plt.subplots(figsize=(11, 6))
  for col in growth.columns:
    is_acct = col == "Account"
    color = PALETTE["account"] if is_acct else PALETTE.get(col, None)
    ax.plot(growth.index,
            growth[col],
            lw=3 if is_acct else 1.6,
            color=color,
            label=labels.get(col, col),
            zorder=5 if is_acct else 3)
    ax.annotate(f"{growth[col].iloc[-1] - 100:+.1f}%",
                (growth.index[-1], growth[col].iloc[-1]),
                textcoords="offset points",
                xytext=(6, 0),
                fontsize=9,
                color=color,
                va="center")
  ax.axhline(100, color="black", lw=0.8)
  ax.set_title(title, fontweight="bold")
  ax.set_ylabel("Growth of 100 (total return)")
  ax.legend(fontsize=9, loc="upper left")
  _save(fig, out)


def plot_account_anatomy(df: pd.DataFrame, stats: Dict[str, Any],
                         out: str) -> None:
  """Bucket weights vs. contribution to income and to duration risk."""
  rows = []
  for bucket, x in df.groupby("Bucket"):
    rows.append({
        "Bucket":
            bucket,
        "Weight":
            float(x["Current_Value"].sum()),
        "Income":
            float(x["Income_Fwd"].sum()),
        "DurationRisk":
            float((x["Current_Value"] * x["Duration"].fillna(0)).sum()),
        "Duration":
            _weighted_average(x["Duration"], x["Current_Value"]),
        "Yield":
            _weighted_average(x["Fwd_Yield"], x["Current_Value"]),
    })
  g = pd.DataFrame(rows).set_index("Bucket")
  for c in ("Weight", "Income", "DurationRisk"):
    g[c] = g[c] / g[c].sum() * 100
  g = g.sort_values("Weight", ascending=True)
  fig, axes = plt.subplots(1,
                           2,
                           figsize=(13, 5.5),
                           gridspec_kw={"width_ratios": [1.1, 1]})
  ax = axes[0]
  colors = plt.cm.viridis(np.linspace(0.15, 0.9, len(g)))
  ax.barh(g.index, g["Weight"], color=colors)
  for i, (idx, r) in enumerate(g.iterrows()):
    ax.text(r["Weight"] + 0.8,
            i, f"{r['Weight']:.0f}% · dur {r['Duration']:.1f}y · "
            f"yld {r['Yield']:.1f}%",
            va="center",
            fontsize=9)
  ax.set_xlim(0, max(g["Weight"]) * 1.65)
  ax.set_xlabel("% of account")
  ax.set_title(
      f"Account anatomy — duration {stats['duration']:.1f}y, "
      f"fwd yield {stats['fwd_yield']:.1f}%",
      fontweight="bold")
  ax = axes[1]
  y = np.arange(len(g))
  h = 0.27
  ax.barh(y + h, g["Weight"], h, label="% of value", color="#8D99AE")
  ax.barh(y, g["Income"], h, label="% of income", color="#2A9D8F")
  ax.barh(y - h,
          g["DurationRisk"],
          h,
          label="% of rate risk (w×D)",
          color="#E76F51")
  ax.set_yticks(y)
  ax.set_yticklabels([])
  ax.set_xlabel("%")
  ax.set_title("Where the income and the rate risk come from",
               fontweight="bold")
  ax.legend(fontsize=9, loc="lower right")
  _save(fig, out)


def plot_rate_shock_curves(grid: pd.DataFrame, out: str) -> None:
  """12M total return vs. parallel shift, one line per instrument."""
  fig, ax = plt.subplots(figsize=(10, 6))
  shocks = [int(c.replace("bp", "")) for c in grid.columns]
  for name, row in grid.iterrows():
    key = str(name).rsplit(" ", maxsplit=1)[-1].strip("()")
    is_acct = str(name).startswith("Account")
    ax.plot(shocks,
            row.values,
            marker="o",
            lw=3 if is_acct else 1.7,
            color=PALETTE["account"] if is_acct else PALETTE.get(key),
            label=name)
  ax.axhline(0, color="black", lw=0.8)
  ax.axvline(0, color="grey", lw=0.8, ls=":")
  ax.set_xlabel("Instantaneous parallel yield shock (bp)")
  ax.set_ylabel("Approx. 12-month total return (%)")
  ax.set_title("Carry + duration: who wins if yields rise or fall from here",
               fontweight="bold")
  ax.legend(fontsize=9)
  _save(fig, out)


def plot_scenarios(table: pd.DataFrame, out: str) -> None:
  """Grouped bars of scenario total returns (rows=scenarios)."""
  fig, ax = plt.subplots(figsize=(12, 6))
  n = len(table.columns)
  x = np.arange(len(table.index))
  width = 0.8 / n
  for i, col in enumerate(table.columns):
    key = col.rsplit(" ", maxsplit=1)[-1].strip("()")
    is_acct = col.startswith("Account")
    color = PALETTE["account"] if is_acct else PALETTE.get(key)
    bars = ax.bar(x + (i - (n - 1) / 2) * width,
                  table[col],
                  width,
                  label=col,
                  color=color)
    for b in bars:
      ax.annotate(f"{b.get_height():+.0f}",
                  (b.get_x() + b.get_width() / 2, b.get_height()),
                  textcoords="offset points",
                  xytext=(0, 3 if b.get_height() >= 0 else -11),
                  ha="center",
                  fontsize=7.5)
  ax.axhline(0, color="black", lw=0.8)
  ax.set_xticks(x)
  ax.set_xticklabels([s.replace(" (", "\n(") for s in table.index], fontsize=9)
  ax.set_ylabel("Approx. 12-month total return (%)")
  ax.set_title("Scenario matrix: account vs. alternatives (12M horizon)",
               fontweight="bold")
  ax.legend(fontsize=9, ncol=3)
  _save(fig, out)


def plot_starting_yield(table: pd.DataFrame, today_yield: float,
                        split_year: int, out: str) -> Dict[str, float]:
  """Scatter of starting 10Y yield vs. subsequent 5Y / 10Y returns."""
  fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
  stats: Dict[str, float] = {}
  for ax, h in zip(axes, (5, 10)):
    col = f"Fwd_{h}Y"
    d = table[["Start_Yield", col]].dropna()
    years = pd.DatetimeIndex(d.index).year
    pre = d[years < split_year]
    post = d[years >= split_year]
    ax.scatter(pre["Start_Yield"],
               pre[col],
               s=9,
               alpha=0.35,
               color="grey",
               label=f"pre-{split_year}")
    ax.scatter(post["Start_Yield"],
               post[col],
               s=9,
               alpha=0.5,
               color="#457B9D",
               label=f"{split_year}+")
    slope, intercept = np.polyfit(d["Start_Yield"], d[col], 1)
    xs = np.linspace(d["Start_Yield"].min(), d["Start_Yield"].max(), 50)
    ax.plot(xs, slope * xs + intercept, color="#1D3557", lw=1.5)
    corr = float(d["Start_Yield"].corr(d[col]))
    fitted = slope * today_yield + intercept
    stats[f"corr_{h}y"] = round(corr, 3)
    stats[f"fit_{h}y"] = round(float(fitted), 2)
    ax.axvline(today_yield, color="#E76F51", ls="--", lw=1.5)
    ax.annotate(f"today {today_yield:.2f}%\nfit → {fitted:.1f}%/yr",
                (today_yield, fitted),
                textcoords="offset points",
                xytext=(10, 20),
                fontsize=9,
                color="#E76F51",
                arrowprops={
                    "arrowstyle": "->",
                    "color": "#E76F51"
                })
    ax.set_title(
        f"Start yield vs. next {h}Y annualised return "
        f"(r = {corr:.2f})",
        fontweight="bold")
    ax.set_xlabel("Starting 10Y Treasury yield (%)")
    ax.legend(fontsize=9, loc="upper left")
  axes[0].set_ylabel("Subsequent annualised total return (%)")
  _save(fig, out)
  return stats


def plot_base_rates(tables: Dict[str, pd.DataFrame], out: str) -> None:
  """Median forward returns of bonds vs cash by horizon per condition."""
  fig, axes = plt.subplots(1,
                           len(tables),
                           figsize=(5 * len(tables), 5),
                           sharey=True)
  if len(tables) == 1:
    axes = [axes]
  for ax, (name, t) in zip(axes, tables.items()):
    x = np.arange(len(t.index))
    err = np.array([t["Median_%"] - t["P10_%"], t["P90_%"] - t["Median_%"]])
    ax.bar(x - 0.2,
           t["Median_%"],
           0.4,
           yerr=err,
           capsize=3,
           color="#2A9D8F",
           label="Bond (median, P10–P90)")
    if "Cash_Median_%" in t.columns:
      ax.bar(x + 0.2,
             t["Cash_Median_%"],
             0.4,
             color="#8D99AE",
             label="Cash (median)")
      for xi, (_, r) in zip(x, t.iterrows()):
        ax.text(xi,
                max(r["P90_%"], r["Cash_Median_%"]) + 0.6,
                f"beat cash\n{r['Beat_Cash_%']:.0f}%",
                ha="center",
                fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{h}\n(n={n})" for h, n in zip(t.index, t["N_months"])])
    ax.set_title(name, fontweight="bold", fontsize=10)
    ax.axhline(0, color="black", lw=0.8)
    ax.legend(fontsize=8, loc="upper right")
  axes[0].set_ylabel("Annualised forward total return (%)")
  _save(fig, out)


def plot_credit_spreads(macro: pd.DataFrame, asof: pd.Timestamp,
                        out: str) -> Dict[str, float]:
  """HY spread (short history) and Baa spread (1986+) with percentiles."""
  fig, axes = plt.subplots(2, 1, figsize=(11, 8))
  info: Dict[str, float] = {}
  ax = axes[0]
  hy = macro["HY_SPREAD"].dropna()
  hy = hy.loc[:asof]
  ax.plot(hy.index, hy, color="#9B2226", lw=1.6, label="HY OAS (%)")
  if "HY_YIELD" in macro.columns:
    ax2 = ax.twinx()
    hyy = macro["HY_YIELD"].dropna().loc[:asof]
    ax2.plot(hyy.index, hyy, color="#E9C46A", lw=1.2, label="HY yield (%)")
    ax2.set_ylabel("HY effective yield (%)")
    ax2.legend(loc="upper right", fontsize=9)
  ax.axhline(hy.iloc[-1], color="#9B2226", ls=":", lw=1)
  ax.set_title(
      f"High-yield spread {hy.iloc[-1]:.2f}% — compensation for "
      f"default risk is thin vs. recessions (8–20%)",
      fontweight="bold")
  ax.set_ylabel("OAS (%)")
  ax.legend(loc="upper left", fontsize=9)
  info["hy_spread"] = float(hy.iloc[-1])
  info["hy_spread_pct_rank"] = float((hy < hy.iloc[-1]).mean() * 100)
  ax = axes[1]
  baa = macro["BAA_SPREAD"].dropna().loc[:asof]
  ax.plot(baa.index, baa, color="#457B9D", lw=1.2, label="Baa − 10Y (%)")
  if "RECESSION_PROB" in macro.columns:
    rp = macro["RECESSION_PROB"].reindex(baa.index).ffill()
    ax.fill_between(baa.index,
                    baa.min(),
                    baa.max(),
                    where=rp > 50,
                    color="grey",
                    alpha=0.25,
                    label="Recession prob > 50%")
  ax.axhline(baa.iloc[-1], color="#457B9D", ls=":", lw=1)
  pct = float((baa < baa.iloc[-1]).mean() * 100)
  ax.set_title(
      f"Baa corporate spread {baa.iloc[-1]:.2f}% = {pct:.0f}th "
      f"percentile since {baa.index[0].year} (tight)",
      fontweight="bold")
  ax.set_ylabel("%")
  ax.legend(loc="upper left", fontsize=9)
  info["baa_spread"] = float(baa.iloc[-1])
  info["baa_spread_pct_rank"] = pct
  _save(fig, out)
  return info


def plot_household(before: pd.Series, after: pd.Series, out: str) -> None:
  """Two stacked bars: household mix now vs. after the proposed moves."""
  classes = [c for c in ASSET_CLASS_COLORS if c in before.index]
  fig, ax = plt.subplots(figsize=(11, 3.8))
  for i, (lbl, s) in enumerate((("After moves", after), ("Today", before))):
    left = 0.0
    tot = float(s.sum())
    for c in classes:
      v = float(s.get(c, 0.0)) / tot * 100
      ax.barh(i,
              v,
              left=left,
              color=ASSET_CLASS_COLORS[c],
              label=c if i == 0 else None)
      if v > 3:
        ax.text(left + v / 2,
                i,
                f"{c}\n{v:.1f}%",
                ha="center",
                va="center",
                fontsize=8.5,
                color="white",
                fontweight="bold")
      left += v
  ax.set_yticks([0, 1])
  ax.set_yticklabels(["After moves", "Today"])
  ax.set_xlim(0, 100)
  ax.set_xlabel("% of investable household assets")
  ax.set_title("The bond account in context: household asset mix",
               fontweight="bold")
  ax.legend(ncol=5, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.3))
  _save(fig, out)


def plot_yield_menu(items: Dict[str, float], out: str) -> None:
  """Horizontal bars of what each asset pays today."""
  s = pd.Series(items).sort_values()
  fig, ax = plt.subplots(figsize=(10, 5.5))
  colors = ["#9B2226" if "S&P" in k else "#2A9D8F" for k in s.index]
  ax.barh(s.index, s.values, color=colors)
  for i, v in enumerate(s.values):
    ax.text(v + 0.05, i, f"{v:.2f}%", va="center", fontsize=9)
  ax.set_xlabel("Yield (%)")
  ax.set_title("What each asset pays you today (S&P in red)", fontweight="bold")
  _save(fig, out)


def plot_decision_tree(out: str) -> None:
  """Action flow for money leaving the bond account / new contributions."""
  nodes = {
      "root": {
          "pos": (0.62, 1.0),
          "label": "Dollar leaving the Wealthfront bond account\n"
                   "(or a new contribution)",
          "color": "#D9E2EC",
          "size": 10
      },
      "q1": {
          "pos": (0.62, 0.78),
          "label": "Needed within ~2 years\n(emergency fund / known spend)?",
          "color": "#F9F1C8",
          "size": 9
      },
      "cash": {
          "pos": (0.15, 0.56),
          "label": "Keep cash-like:\nT-bills / SGOV / money market ≈4.2%\n"
                   "(HYSA 3.8% fine for simplicity)",
          "color": "#CDE7D8",
          "size": 9
      },
      "q2": {
          "pos": (0.62, 0.56),
          "label": "Taxable account?",
          "color": "#F9F1C8",
          "size": 9
      },
      "equity": {
          "pos": (0.38, 0.34),
          "label": "Yes → broad equity index (VTI / VOO)\n"
                   "Tax-efficient; bonds belong in the 401k",
          "color": "#CDE7D8",
          "size": 9
      },
      "bond401k": {
          "pos": (0.9, 0.34),
          "label": "401k / IRA → Total Bond Market\n"
                   "Raise 85:15 → 75:25 now, → 70:30 by Q1-27\n"
                   "(2–3 tranches, not a lump)",
          "color": "#CDE7D8",
          "size": 9
      },
      "pause": {
          "pos": (0.62, 0.12),
          "label": "Pause tranche 2 if: 10Y > 5.5% or\n"
                   "Fed signals ≥2 more hikes",
          "color": "#F6D6D6",
          "size": 8.5
      },
      "accel": {
          "pos": (1.08, 0.12),
          "label": "Accelerate if: HY spread > 4.5%,\n"
                   "unemployment ≥ 4.6% or first Fed cut",
          "color": "#CDE7D8",
          "size": 8.5
      },
  }
  edges = [("root", "q1"), ("q1", "cash"), ("q1", "q2"), ("q2", "equity"),
           ("q2", "bond401k"), ("bond401k", "pause"), ("bond401k", "accel")]
  labels = {
      ("q1", "cash"): "yes",
      ("q1", "q2"): "no",
      ("q2", "equity"): "taxable",
      ("q2", "bond401k"): "tax-advantaged",
  }
  ru.draw_matplotlib_decision_tree(nodes,
                                   edges,
                                   "Where should the next dollar go?",
                                   out,
                                   edge_labels=labels,
                                   figsize=(15, 9))


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def discover_household_tsvs(portfolios_dir: str) -> Dict[str, str]:
  """Lists per-account TSV exports (skips combined / example files)."""
  out: Dict[str, str] = {}
  for p in sorted(glob.glob(os.path.join(portfolios_dir, "*.tsv"))):
    name = os.path.basename(p)
    if name.startswith("_combined") or name.startswith("example_"):
      continue
    out[name[:-4]] = p
  return out


def _pct(x: float) -> str:
  return f"{x:.2f}%"


def build_markdown(metrics: Dict[str, Any], tables: Dict[str,
                                                         pd.DataFrame]) -> str:
  """Renders the metric tables to markdown for inclusion in REPORT.md."""
  parts = [f"# Bond metrics ({metrics['asof']})", ""]
  for name, t in tables.items():
    parts.append(f"## {name}")
    parts.append("")
    parts.append(
        tabulate(t.reset_index().to_dict(orient="list"),
                 headers="keys",
                 tablefmt="github",
                 showindex=False,
                 floatfmt=".2f"))
    parts.append("")
  parts.append("## Key numbers")
  parts.append("")
  parts.append("```json")
  parts.append(
      json.dumps({
          k: v for k, v in metrics.items() if k != "tables"
      },
                 indent=2,
                 default=str))
  parts.append("```")
  return "\n".join(parts) + "\n"


def run(account_tsv: str,
        out_dir: str,
        prefix: str,
        asof: Optional[str] = None,
        retirement_tsv: Optional[str] = None,
        portfolios_dir: Optional[str] = None,
        lookback_days: int = 183,
        advisory_fee_bps: float = 25.0,
        federal_rate: float = 0.37,
        state_rate: float = 0.0,
        equity_index: str = "SPY") -> Dict[str, Any]:
  """Generates all plots and metrics for a bond-account report.

  Args:
    account_tsv (str): Bond account TSV export.
    out_dir (str): Report directory (plots go to ``<out_dir>/plots``).
    prefix (str): Plot filename prefix, e.g. ``10_13``.
    asof (Optional[str]): Analysis date (default: latest macro date).
    retirement_tsv (Optional[str]): 401k TSV for the rebalance table.
    portfolios_dir (Optional[str]): Folder of account TSVs for the
      household roll-up (default ``portfolios/tsvs``).
    lookback_days (int): Window for the "what happened" analysis.
    advisory_fee_bps (float): Robo-advisor fee drag on the account.
    federal_rate (float): Marginal federal rate for after-tax yields.
    state_rate (float): Marginal state rate for after-tax yields.
    equity_index (str): Ticker used for the stock-vs-bond comparison.

  Returns:
    Dict[str, Any]: Metrics dictionary (also written to JSON / MD).
  """
  ru.setup_plot_aesthetics()
  plots = os.path.join(out_dir, "plots")
  os.makedirs(plots, exist_ok=True)
  tickers_dir = config.TICKERS_DIR
  macro = ru.load_macro_frame(config.DATA_DIR)
  asof_ts = pd.Timestamp(asof) if asof else macro.index.max()
  row = ru.macro_asof(macro, asof_ts)
  start_ts = asof_ts - pd.Timedelta(days=lookback_days)
  metrics: Dict[str, Any] = {
      "asof": str(asof_ts.date()),
      "window_start": str(start_ts.date())
  }
  tables: Dict[str, pd.DataFrame] = {}

  # 1. Rates picture -------------------------------------------------------
  dates = {
      f"Today ({asof_ts:%b %d})": asof_ts,
      "1M ago": asof_ts - pd.DateOffset(months=1),
      "3M ago": asof_ts - pd.DateOffset(months=3),
      "6M ago": asof_ts - pd.DateOffset(months=6),
  }
  curve = ru.curve_snapshot(macro, dates)
  tables["Treasury curve snapshots (%)"] = curve
  plot_curve_shift(curve, float(row["FEDFUNDS_UPPER"]),
                   os.path.join(plots, f"{prefix}_curve_shift.png"))
  change = ru.rates_change_table(macro, start_ts, asof_ts)
  tables[f"Rates & spreads: {start_ts:%Y-%m-%d} → {asof_ts:%Y-%m-%d}"] = change
  plot_yield_drivers(macro, asof_ts,
                     os.path.join(plots, f"{prefix}_yield_drivers.png"))
  hp = ru.hike_pricing(row)
  metrics["hike_pricing"] = {k: round(v, 2) for k, v in hp.items()}
  cpi = macro["CPI"].dropna()
  cpi_yoy = float(cpi.iloc[-1] /
                  cpi.loc[:cpi.index[-1] - pd.DateOffset(years=1)].iloc[-1] -
                  1) * 100
  metrics["cpi_yoy"] = round(cpi_yoy, 2)
  metrics["real_10y_vs_cpi"] = round(float(row["US10Y"]) - cpi_yoy, 2)
  u10 = macro["US10Y"].dropna()
  prior = u10[(u10 >= float(row["US10Y"])) &
              (u10.index < asof_ts - pd.DateOffset(months=12))]
  metrics["us10y_last_this_high"] = str(
      prior.index.max().date()) if len(prior) else "n/a"
  r10 = macro["US10Y_REAL"].dropna()
  prior_r = r10[(r10 >= float(row["US10Y_REAL"])) &
                (r10.index < asof_ts - pd.DateOffset(months=12))]
  metrics["real_10y_last_this_high"] = str(
      prior_r.index.max().date()) if len(prior_r) else "n/a"
  metrics["snapshot"] = {
      k: round(float(row[k]), 2)
      for k in ("FEDFUNDS_UPPER", "SOFR", "US03M", "US01Y", "US02Y", "US05Y",
                "US10Y", "US30Y", "US10Y_REAL", "BREAKEVEN_10Y",
                "TERM_PREMIUM_10Y", "HY_SPREAD", "HY_YIELD", "CORP_YIELD",
                "CORP_SPREAD", "BAA_SPREAD", "WTI_CRUDE", "UNRATE",
                "UMICH_SENTIMENT", "RECESSION_PROB")
      if k in row.index and pd.notna(row[k])
  }

  # 2. The account ---------------------------------------------------------
  acct = enrich_bond_holdings(load_bond_account(account_tsv), macro,
                              tickers_dir, asof_ts)
  stats = portfolio_bond_stats(acct)
  net_yield = stats["fwd_yield"] - stats["expense_ratio"] - (advisory_fee_bps /
                                                             100.0)
  treasury_share = stats["credit_mix"].get("Treasury", 0) / 100.0
  stats["net_yield_after_fees"] = net_yield
  stats["after_tax_yield"] = ru.after_tax_yield(net_yield, federal_rate,
                                                state_rate, treasury_share)
  stats["advisory_fee_bps"] = advisory_fee_bps
  metrics["account"] = {
      k: (round(v, 3) if isinstance(v, float) else v) for k, v in stats.items()
  }
  hold_cols = [
      "Ticker", "Name", "Bucket", "Credit", "Weight", "Duration", "Fwd_Yield",
      "Trailing_Yield", "Expense_Ratio", "Unrealized_PnL_Pct"
  ]
  tables["Account holdings"] = acct[[c for c in hold_cols if c in acct.columns
                                    ]].round(2).set_index("Ticker")
  plot_account_anatomy(acct, stats,
                       os.path.join(plots, f"{prefix}_account_anatomy.png"))

  # 3. What happened over the window ---------------------------------------
  bench_tickers = list(BENCHMARKS.values())
  px = load_adjusted_closes(
      list(acct["Ticker"]) + bench_tickers, tickers_dir, start_ts, asof_ts)
  weights = dict(zip(acct["Ticker"], acct["Current_Value"]))
  growth = growth_of_100(px, weights)
  show = ["Account"] + bench_tickers
  labels = {v: k for k, v in BENCHMARKS.items()}
  labels["Account"] = "Bond account (today's weights)"
  plot_total_return(
      growth[[c for c in show if c in growth.columns]], labels,
      f"Total return since {start_ts:%b %d, %Y} "
      "(dividends reinvested)",
      os.path.join(plots, f"{prefix}_total_return_window.png"))
  window_tr = (growth.iloc[-1] - 100).round(2)
  tr_table = pd.DataFrame({"Window_TR_%": window_tr})
  tr_table["Label"] = [labels.get(i, i) for i in tr_table.index]
  tables[f"Total return {start_ts:%Y-%m-%d} → {asof_ts:%Y-%m-%d} (%)"] = (
      tr_table[["Label", "Window_TR_%"]])
  ytd_px = load_adjusted_closes(show[1:] + list(acct["Ticker"]), tickers_dir,
                                pd.Timestamp(asof_ts.year, 1, 1), asof_ts)
  ytd = (growth_of_100(ytd_px, weights).iloc[-1] - 100).round(2)
  metrics["ytd_total_return"] = {
      labels.get(str(k), str(k)): float(v) for k, v in ytd.items() if k in show
  }
  metrics["window_total_return"] = {
      labels.get(str(k), str(k)): float(v)
      for k, v in window_tr.items()
      if k in show
  }

  # 4. Rate shocks & scenarios ---------------------------------------------
  instruments = {
      f"Account (dur {stats['duration']:.1f}y)":
          (stats["fwd_yield"], stats["duration"])
  }
  for t in SHOCK_CURVE_TICKERS:
    ref = BOND_ETF_REFERENCE[t]
    instruments[f"{ref['name']} ({t})"] = (forward_yield_estimate(
        t, row, tickers_dir) or 0.0, ref["duration"])
  grid = ru.rate_shock_grid(instruments, BOND_SHOCKS_BP)
  tables["12M total return vs. parallel shift (%)"] = grid
  plot_rate_shock_curves(grid, os.path.join(plots, f"{prefix}_rate_shock.png"))
  scen_acct = bond_scenario_table(acct, BOND_SCENARIOS)
  tables["Account scenarios (12M, %)"] = scen_acct
  bench = benchmark_frame(SCENARIO_BENCHMARKS, row, tickers_dir)
  scen_cmp = pd.DataFrame({"Account": scen_acct["Portfolio_TR_%"]})
  for _, b in bench.iterrows():
    one = bond_scenario_table(pd.DataFrame([b]), BOND_SCENARIOS)
    scen_cmp[f"{b['Ticker']}"] = one["Portfolio_TR_%"]
  scen_cmp.columns = [
      c if c == "Account" else f"{BOND_ETF_REFERENCE[c]['name']} ({c})"
      for c in scen_cmp.columns
  ]
  tables["Scenario comparison (12M, %)"] = scen_cmp
  plot_scenarios(scen_cmp, os.path.join(plots, f"{prefix}_scenarios.png"))

  # 5. History: starting yield → forward returns ----------------------------
  monthly = macro[["US10Y", "US05Y", "US03M", "FEDFUNDS",
                   "CPI"]].resample("MS").first()
  cash_rate = monthly["US03M"].fillna(monthly["FEDFUNDS"])
  t10 = ru.starting_yield_table(monthly["US10Y"].dropna(),
                                10,
                                cash_rate_pct=cash_rate)
  t5 = ru.starting_yield_table(monthly["US05Y"].dropna(),
                               5,
                               horizons=(1, 3, 5),
                               cash_rate_pct=cash_rate)
  cpi_yoy_m = monthly["CPI"].pct_change(12) * 100
  real10 = (monthly["US10Y"] - cpi_yoy_m).reindex(t10.index)
  cond = (t10["Start_Yield"] >= 5.0) & (real10 >= 1.5)
  post = t10.index >= "1985-01-01"
  base_tables = {
      "All months since 1962":
          ru.conditional_base_rates(t10, t10["Start_Yield"] > 0),
      "10Y ≥ 5% & real ≥ 1.5% (all)":
          ru.conditional_base_rates(t10, cond),
      "10Y ≥ 5% & real ≥ 1.5% (1985+)":
          ru.conditional_base_rates(t10, cond & post),
      "10Y ≥ 5% & real ≥ 1.5% (pre-1985)":
          ru.conditional_base_rates(t10, cond & ~post),
      "5Y ≥ 4.75% (all)":
          ru.conditional_base_rates(t5,
                                    t5["Start_Yield"] >= 4.75,
                                    horizons=(1, 3, 5)),
  }
  for k, v in base_tables.items():
    tables[f"Base rates — {k}"] = v
  fit = plot_starting_yield(
      t10, float(row["US10Y"]), 1985,
      os.path.join(plots, f"{prefix}_starting_yield_vs_forward.png"))
  metrics["starting_yield_fit"] = fit
  plot_base_rates(
      {
          k: base_tables[k]
          for k in ("All months since 1962", "10Y ≥ 5% & real ≥ 1.5% (1985+)",
                    "10Y ≥ 5% & real ≥ 1.5% (pre-1985)")
      }, os.path.join(plots, f"{prefix}_base_rates.png"))

  # 6. Credit --------------------------------------------------------------
  metrics["credit"] = plot_credit_spreads(
      macro, asof_ts, os.path.join(plots, f"{prefix}_credit_spreads.png"))

  # 7. Stocks vs bonds -----------------------------------------------------
  pe = ru.read_fundamental_metric(tickers_dir, equity_index, "trailingPE")
  dy = ru.read_fundamental_metric(tickers_dir, equity_index,
                                  "dividendYield") or 0.0
  if pe:
    val = ru.stock_bond_valuation(pe, row, dy)
    val["trailing_pe"] = pe
    val["expected_nominal_equity_return_naive"] = (val["earnings_yield"] +
                                                   float(row["BREAKEVEN_10Y"]))
    metrics["stock_bond_valuation"] = {k: round(v, 2) for k, v in val.items()}
    menu = {
        f"S&P 500 dividend yield":
            dy,
        f"S&P 500 earnings yield (1/PE {pe:.1f})":
            val["earnings_yield"],
        "3M T-bill / money market":
            float(row["US03M"]),
        "2Y Treasury":
            float(row["US02Y"]),
        "10Y Treasury":
            float(row["US10Y"]),
        "10Y TIPS (real)":
            float(row["US10Y_REAL"]),
        "Total Bond Market (est.)":
            forward_yield_estimate("BND", row, tickers_dir) or 0.0,
        "IG corporates":
            float(row["CORP_YIELD"]),
        "High yield":
            float(row["HY_YIELD"]),
        f"Bond account (fwd, gross)":
            stats["fwd_yield"],
    }
    plot_yield_menu(menu, os.path.join(plots, f"{prefix}_yield_menu.png"))

  # 8. Household context & the asset-location swap --------------------------
  tsvs = discover_household_tsvs(
      portfolios_dir or os.path.join(PROJECT_ROOT, "portfolios", "tsvs"))
  alloc = ru.household_allocation(tsvs)
  before = alloc.drop(columns=["Total"]).sum()
  metrics["household_pct"] = (before / before.sum() * 100).round(2).to_dict()
  acct_key = os.path.basename(account_tsv)[:-4]
  after = before.copy()
  if acct_key in alloc.index:
    acct_row = pd.Series(alloc.drop(columns=["Total"]).loc[acct_key])
    acct_val = float(acct_row.sum())
    for cls, v in acct_row.items():  # remove the account class-by-class
      after[str(cls)] = float(after.get(str(cls), 0.0)) - float(v)
  else:
    acct_val = stats["total_value"]
    after["Bond"] -= acct_val
  cash_keep = 0.20 * acct_val
  after["Cash"] = after.get("Cash", 0.0) + cash_keep
  after["Equity"] += acct_val - cash_keep
  retire: Dict[str, Any] = {}
  if retirement_tsv and os.path.exists(retirement_tsv):
    rk = os.path.basename(retirement_tsv)[:-4]
    r_total = float(alloc["Total"][rk])
    r_bond = float(alloc["Bond"][rk]) if "Bond" in alloc.columns else 0.0
    retire = {"total": r_total, "bond_pct_now": r_bond / r_total * 100}
    rows = []
    for target in (15, 25, 30, 35, 40):
      shift = target / 100 * r_total - r_bond
      rows.append({
          "Target_bond_pct":
              target,
          "Shift_to_bonds":
              round(shift),
          "Household_bond_pct_after_swap":
              round((after["Bond"] + shift) / after.sum() * 100, 2),
      })
    retire["targets"] = rows
    tables["401k rebalance options (after moving the bond account to "
           "equities)"] = pd.DataFrame(rows).set_index("Target_bond_pct")
    # Default illustration: 30% bonds in the retirement account.
    after["Bond"] += 0.30 * r_total - r_bond
    after["Equity"] -= 0.30 * r_total - r_bond
  metrics["retirement"] = retire
  metrics["household_pct_after"] = (after / after.sum() *
                                    100).round(2).to_dict()
  plot_household(before, after,
                 os.path.join(plots, f"{prefix}_household_allocation.png"))
  plot_decision_tree(os.path.join(plots, f"{prefix}_decision_tree.png"))

  # 9. Persist ---------------------------------------------------------------
  metrics["tables"] = {
      k: v.reset_index().to_dict(orient="records") for k, v in tables.items()
  }
  with open(os.path.join(out_dir, "bond_metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2, default=str)
  with open(os.path.join(out_dir, "bond_metrics.md"), "w") as f:
    f.write(build_markdown(metrics, tables))
  logger.info("Wrote metrics to %s", out_dir)
  return metrics


def main() -> None:
  logging.basicConfig(level=logging.INFO, format="%(message)s")
  p = argparse.ArgumentParser(description="Bond account report generator")
  p.add_argument("--account", required=True, help="Bond account TSV")
  p.add_argument("--out", required=True, help="Report directory")
  p.add_argument("--prefix",
                 default=datetime.date.today().strftime("%m_%d"),
                 help="Plot filename prefix (default MM_DD)")
  p.add_argument("--asof", default=None, help="Analysis date YYYY-MM-DD")
  p.add_argument("--retirement", default=None, help="401k TSV (optional)")
  p.add_argument("--portfolios-dir",
                 default=None,
                 help="Folder with account TSVs for the household roll-up")
  p.add_argument("--lookback-days", type=int, default=183)
  p.add_argument("--advisory-fee-bps", type=float, default=25.0)
  p.add_argument("--federal-rate", type=float, default=0.37)
  p.add_argument("--state-rate", type=float, default=0.0)
  p.add_argument("--equity-index", default="SPY")
  a = p.parse_args()
  run(a.account, a.out, a.prefix, a.asof, a.retirement, a.portfolios_dir,
      a.lookback_days, a.advisory_fee_bps, a.federal_rate, a.state_rate,
      a.equity_index)


if __name__ == "__main__":
  main()
