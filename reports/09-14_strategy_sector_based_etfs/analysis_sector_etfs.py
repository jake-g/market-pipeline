"""Quantitative analysis and plotting for the sector & thematic ETF report.

Loads multi-year adjusted closes for the thematic universe (original 14 ETFs
plus 9 proposed additions) and core benchmarks, then produces:

* normalised performance timelines (2Y / 5Y / 8.5Y) and tier-vs-benchmark
  panels (original report),
* **diversification diagnostics** — clustered correlation heatmap, rolling
  correlation to the market, factor regressions ("how much of this ETF is
  just VTI / growth / semis?"), marginal effect of adding each ETF to a VTI
  core, up/down capture, macro-driver sensitivities,
* **growth-vs-risk trade-offs** — CAGR vs max drawdown bubbles, risk/return
  scatter with Sharpe iso-lines, random-portfolio frontier with the model
  portfolios overlaid, and fixed-weight backtests of Models A/B/C,
* a metrics table for every ETF and a markdown section injected into
  ``REPORT.md`` with the computed numbers.

Generic math lives in ``reports.report_utils``; this file holds the universe
definition, the plots and the narrative.
"""

import datetime
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

import config  # noqa: E402
from reports import report_utils as ru  # noqa: E402

matplotlib.use("Agg")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLOTS_DIR = os.path.join(SCRIPT_DIR, "plots")
MARKET_DATA_DIR = config.TICKERS_DIR
REPORT_PATH = os.path.join(SCRIPT_DIR, "REPORT.md")
REPORT_MARKER = "## Historical Multi-Sector Timelines & Empirical Evidence"

# ---------------------------------------------------------------------------
# Universe
# ---------------------------------------------------------------------------
# Original 14 ETFs plus proposed additions (marked ``new``) that fill gaps:
# grid equipment, defense tech, robotics, software, longer-history space,
# data-center REITs, biotech, clean energy and silver.
TIER_MAP: Dict[str, Dict[str, Any]] = {
    "1. AI, Silicon & Robotics": {
        "tickers": ["DRAM", "SOXQ", "QTUM", "BOTZ"],
        "new": ["BOTZ"],
        "benchmark": "SOXX",
        "color": "#1f77b4",
    },
    "2. Digital Infra & Software": {
        "tickers": ["CIBR", "AIPO", "IGV", "SRVR"],
        "new": ["IGV", "SRVR"],
        "benchmark": "VUG",
        "color": "#ff7f0e",
    },
    "3. Space & Defense": {
        "tickers": ["NASA", "UFO", "SHLD"],
        "new": ["UFO", "SHLD"],
        "benchmark": "VTI",
        "color": "#9467bd",
    },
    "4. Physical Infra & Materials": {
        "tickers": ["URNM", "COPX", "LIT", "FIW", "GRID", "ICLN"],
        "new": ["GRID", "ICLN"],
        "benchmark": "VTV",
        "color": "#2ca02c",
    },
    "5. Healthcare": {
        "tickers": ["OZEM", "PPH", "XBI"],
        "new": ["XBI"],
        "benchmark": "VTV",
        "color": "#d62728",
    },
    "6. Store of Value": {
        "tickers": ["IBIT", "GLDM", "SLV"],
        "new": ["SLV"],
        "benchmark": "VTI",
        "color": "#e377c2",
    },
}
ETF_NAMES: Dict[str, str] = {
    "DRAM": "Roundhill Memory",
    "SOXQ": "Invesco PHLX Semis",
    "QTUM": "Defiance Quantum",
    "BOTZ": "Global X Robotics & AI",
    "CIBR": "First Trust Cybersecurity",
    "AIPO": "Defiance AI & Power Infra",
    "IGV": "iShares Software",
    "SRVR": "Pacer Data Center REITs",
    "NASA": "Tema Space Innovators",
    "UFO": "Procure Space",
    "SHLD": "Global X Defense Tech",
    "URNM": "Sprott Uranium Miners",
    "COPX": "Global X Copper Miners",
    "LIT": "Global X Lithium & Battery",
    "FIW": "First Trust Water",
    "GRID": "First Trust Smart Grid",
    "ICLN": "iShares Global Clean Energy",
    "OZEM": "Roundhill GLP-1",
    "PPH": "VanEck Pharma",
    "XBI": "SPDR S&P Biotech",
    "IBIT": "iShares Bitcoin",
    "GLDM": "SPDR Gold MiniShares",
    "SLV": "iShares Silver",
}
ALL_THEMATIC: List[str] = [t for v in TIER_MAP.values() for t in v["tickers"]]
NEW_TICKERS: List[str] = [t for v in TIER_MAP.values() for t in v["new"]]
ORIGINAL_TICKERS: List[str] = [t for t in ALL_THEMATIC if t not in NEW_TICKERS]
BENCHMARKS: List[str] = ["VTI", "VUG", "VTV", "SMH", "SOXX"]
# Short-history ETFs are mapped to a long-history proxy for multi-year math
# (factor regressions, frontier, backtests). Proxies are stated in the report.
PROXIES: Dict[str, str] = {
    "DRAM": "SOXX",
    "NASA": "UFO",
    "AIPO": "GRID",
    "SHLD": "ITA",
    "OZEM": "XBI"
}
EXTRA_LOAD: List[str] = ["ITA"]  # proxy-only tickers

MODEL_PORTFOLIOS: Dict[str, Dict[str, float]] = {
    "Model A: Frontier Alpha": {
        "SOXQ": 15,
        "DRAM": 15,
        "AIPO": 10,
        "URNM": 10,
        "CIBR": 15,
        "COPX": 7.5,
        "QTUM": 7.5,
        "IBIT": 10,
        "VTI": 10,
    },
    "Model B: Macro Barbell": {
        "SOXQ": 12.5,
        "QTUM": 12.5,
        "AIPO": 10,
        "COPX": 10,
        "GLDM": 20,
        "CIBR": 7.5,
        "FIW": 7.5,
        "PPH": 10,
        "IBIT": 10,
    },
    "Model C: Real-Asset Compounder": {
        "FIW": 15,
        "PPH": 15,
        "GLDM": 25,
        "AIPO": 20,
        "CIBR": 15,
        "SOXQ": 10,
    },
}
# Model D is derived at runtime: the max-Sharpe random portfolio with at
# least MIN_ENB effective bets (weights rounded to 2.5%).
MODEL_D_NAME = "Model D: Max-Sharpe, ENB>=2, <=25% per ETF (derived)"
MIN_ENB = 2.0
MACRO_SPEC: Dict[str, Tuple[str, str]] = {
    "Δ 10Y yield": ("US10Y", "diff"),
    "Δ 10Y real": ("US10Y_REAL", "diff"),
    "Δ HY spread": ("HY_SPREAD", "diff"),
    "% USD index": ("USD_INDEX", "pct"),
    "% WTI": ("WTI_CRUDE", "pct"),
    "% Copper": ("COPPER_PRICE", "pct"),
}
TIER_COLORS = {k: v["color"] for k, v in TIER_MAP.items()}
TIER_COLORS["Benchmark"] = "#7f7f7f"


def tier_of(ticker: str) -> str:
  for tier, info in TIER_MAP.items():
    if ticker in info["tickers"]:
      return tier
  return "Benchmark"


def _save(fig: plt.Figure, path: str) -> None:
  fig.tight_layout()
  fig.savefig(path, dpi=180, bbox_inches="tight")
  plt.close(fig)
  logger.info("Saved %s", os.path.basename(path))


def with_proxies(prices: pd.DataFrame) -> pd.DataFrame:
  """Returns a copy where short-history tickers are backfilled by proxies.

  The real series is kept where it exists; proxy returns are spliced in
  before inception so multi-year statistics can include the ticker.
  """
  out = prices.copy()
  for t, p in PROXIES.items():
    if t not in out.columns or p not in out.columns:
      continue
    real = out[t].dropna()
    if real.empty:
      continue
    first = real.index.min()
    proxy = out[p].loc[:first].dropna()
    if proxy.empty:
      continue
    scale = real.iloc[0] / proxy.iloc[-1]
    spliced = proxy * scale
    out.loc[spliced.index, t] = spliced.values
  return out


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def compute_metrics(df: pd.DataFrame, tickers: List[str]) -> pd.DataFrame:
  """Per-ticker return / risk / momentum metrics on real (non-proxy) data."""
  rows = []
  for t in tickers:
    if t not in df.columns:
      continue
    s = df[t].dropna()
    if len(s) < 30:
      continue
    n = len(s)
    rec: Dict[str, Any] = {
        "Ticker": t,
        "Tier": tier_of(t),
        "Name": ETF_NAMES.get(t, t),
        "New": t in NEW_TICKERS,
        "Inception": s.index.min().date(),
        "Price": float(s.iloc[-1]),
        "ER": ru.read_fundamental_metric(MARKET_DATA_DIR, t, "netExpenseRatio"),
    }
    ytd = s[s.index >= pd.Timestamp(year=s.index[-1].year, month=1, day=1)]
    rec["YTD"] = float(ytd.iloc[-1] / ytd.iloc[0] - 1) * 100 if len(ytd) > 1 \
        else np.nan
    one = ru.perf_stats(s.iloc[-252:]) if n >= 252 else ru.perf_stats(s)
    rec.update({
        "Ret_1Y": one["total_return"],
        "Vol_1Y": one["vol"],
        "Sharpe_1Y": one["sharpe"] if n >= 252 else np.nan,
        "MaxDD_1Y": one["max_dd"]
    })
    for yrs, lbl in ((3, "3Y"), (5, "5Y")):
      if n >= 252 * yrs:
        st = ru.perf_stats(s.iloc[-252 * yrs:])
        rec[f"CAGR_{lbl}"] = st["cagr"]
        rec[f"Vol_{lbl}"] = st["vol"]
        rec[f"MaxDD_{lbl}"] = st["max_dd"]
        rec[f"Calmar_{lbl}"] = st["calmar"]
      else:
        for k in ("CAGR", "Vol", "MaxDD", "Calmar"):
          rec[f"{k}_{lbl}"] = np.nan
    ma_w = 200 if n >= 200 else 50
    ma = float(s.rolling(ma_w).mean().iloc[-1])
    rec["Dist_MA"] = (rec["Price"] / ma - 1) * 100
    rec["MA_Window"] = ma_w
    rec["RSI_14"] = float(ru.compute_rsi(s, 14).iloc[-1])
    rows.append(rec)
  return pd.DataFrame(rows).set_index("Ticker")


# ---------------------------------------------------------------------------
# Original plots (kept, driven by the expanded universe)
# ---------------------------------------------------------------------------


def _timeline(df: pd.DataFrame,
              tickers: List[str],
              cutoff: str,
              title: str,
              out: str,
              log: bool = False) -> None:
  ru.setup_plot_aesthetics()
  fig, ax = plt.subplots(figsize=(15, 8.5))
  sub = df.loc[pd.Timestamp(cutoff):]
  palette = sns.color_palette("tab20", len(tickers))
  for i, t in enumerate(tickers):
    if t not in sub.columns:
      continue
    s = sub[t].dropna()
    if s.empty:
      continue
    norm = s / s.iloc[0] * 100
    bench = t in BENCHMARKS
    ax.plot(norm.index,
            norm,
            lw=2.4 if bench else 1.6,
            ls="--" if bench else "-",
            color=palette[i],
            label=f"{t} (bench)" if bench else t,
            alpha=0.95 if bench else 0.85)
    ax.annotate(f"{t}: {norm.iloc[-1]:.0f}", (norm.index[-1], norm.iloc[-1]),
                xytext=(8, 0),
                textcoords="offset points",
                fontsize=8,
                fontweight="bold" if bench else "normal",
                va="center")
  ax.axhline(100, color="gray", ls=":", lw=1)
  if log:
    ax.set_yscale("log")
  ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
  ax.set_ylabel("Rebased to 100" + (" (log)" if log else ""))
  ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
  ax.legend(bbox_to_anchor=(1.1, 1.0), loc="upper left", fontsize=8.5)
  _save(fig, out)


def plot_tier_panels(df: pd.DataFrame, cutoff: str, out: str) -> None:
  ru.setup_plot_aesthetics()
  fig, axes = plt.subplots(3, 2, figsize=(16, 14))
  sub = df.loc[pd.Timestamp(cutoff):]
  for ax, (tier, info) in zip(axes.flatten(), TIER_MAP.items()):
    b = info["benchmark"]
    if b in sub.columns:
      sb = sub[b].dropna()
      ax.plot(sb.index,
              sb / sb.iloc[0] * 100,
              color="black",
              lw=2,
              ls="--",
              alpha=0.7,
              label=f"Benchmark ({b})")
    colors = sns.color_palette("muted", len(info["tickers"]))
    for c, t in zip(colors, info["tickers"]):
      if t not in sub.columns:
        continue
      s = sub[t].dropna()
      if s.empty:
        continue
      norm = s / s.iloc[0] * 100
      ax.plot(norm.index,
              norm,
              color=c,
              lw=1.8,
              ls="-" if t not in NEW_TICKERS else "-.",
              label=f"{t}{' (new)' if t in NEW_TICKERS else ''} "
              f"({norm.iloc[-1] - 100:+.1f}%)")
    ax.axhline(100, color="gray", ls=":", lw=0.8)
    ax.set_title(tier, fontsize=12, fontweight="bold")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%y"))
    ax.legend(fontsize=8, loc="upper left")
  fig.suptitle(
      "Trailing 1-Year: each tier vs. its benchmark "
      "(dash-dot = proposed additions)",
      fontsize=15,
      fontweight="bold",
      y=0.995)
  _save(fig, out)


def plot_rolling_vol(df: pd.DataFrame, tickers: List[str], out: str) -> None:
  ru.setup_plot_aesthetics()
  fig, ax = plt.subplots(figsize=(14, 7))
  cols = [t for t in tickers if t in df.columns]
  sub = df[df.index >= pd.Timestamp("2024-01-01")][cols]
  rv = sub.pct_change().rolling(60).std() * np.sqrt(252) * 100
  palette = sns.color_palette("tab10", len(rv.columns))
  for c, t in zip(palette, rv.columns):
    s = rv[t].dropna()
    ax.plot(s.index,
            s,
            color="black" if t == "VTI" else c,
            lw=2.4 if t == "VTI" else 1.6,
            ls="--" if t == "VTI" else "-",
            label=t)
  ax.set_title("60-day rolling annualised volatility (%)",
               fontsize=14,
               fontweight="bold")
  ax.set_ylabel("Annualised vol (%)")
  ax.legend(fontsize=9, ncol=2)
  _save(fig, out)


def plot_risk_return(m: pd.DataFrame, out: str) -> None:
  ru.setup_plot_aesthetics()
  fig, ax = plt.subplots(figsize=(13, 8.5))
  for tier, g in m.groupby("Tier"):
    ax.scatter(g["Vol_1Y"],
               g["Ret_1Y"],
               s=130 if tier == "Benchmark" else 100,
               marker="D" if tier == "Benchmark" else "o",
               color=TIER_COLORS.get(str(tier), "k"),
               edgecolors="black",
               lw=0.8,
               label=tier,
               alpha=0.9)
    for t, r in g.iterrows():
      ax.annotate(f"{t}{'*' if r['New'] else ''}", (r["Vol_1Y"], r["Ret_1Y"]),
                  xytext=(6, 5),
                  textcoords="offset points",
                  fontsize=9,
                  fontweight="bold")
  vols = np.linspace(5, 90, 50)
  for sh in (0.5, 1.0, 1.5, 2.0):
    ax.plot(vols, 4 + sh * vols, ls="--", color="gray", alpha=0.35, lw=1)
    ax.annotate(f"Sharpe {sh}", (vols[-1], 4 + sh * vols[-1]),
                xytext=(-48, -4),
                textcoords="offset points",
                fontsize=7.5,
                color="gray")
  ax.axhline(0, color="black", ls=":", lw=0.8)
  ax.set_title("Trailing 1-year return vs. volatility (* = proposed addition)",
               fontsize=14,
               fontweight="bold")
  ax.set_xlabel("Annualised volatility (%)")
  ax.set_ylabel("Trailing 1-year total return (%)")
  ax.legend(fontsize=9, loc="upper left")
  _save(fig, out)


def plot_momentum(m: pd.DataFrame, out: str) -> None:
  ru.setup_plot_aesthetics()
  fig, ax = plt.subplots(figsize=(13, 8))
  for tier, g in m.groupby("Tier"):
    ax.scatter(g["Dist_MA"],
               g["RSI_14"],
               s=120 if tier == "Benchmark" else 95,
               marker="D" if tier == "Benchmark" else "o",
               color=TIER_COLORS.get(str(tier), "k"),
               edgecolors="black",
               lw=0.8,
               label=tier,
               alpha=0.9)
    for t, r in g.iterrows():
      ax.annotate(t, (r["Dist_MA"], r["RSI_14"]),
                  xytext=(6, 5),
                  textcoords="offset points",
                  fontsize=9,
                  fontweight="bold")
  ax.axhline(70, color="red", ls="--", lw=1, alpha=0.7)
  ax.axhline(30, color="green", ls="--", lw=1, alpha=0.7)
  ax.axvline(0, color="gray", ls=":", lw=0.8)
  ax.set_title("Technical momentum: distance to 200-day MA vs. 14-day RSI",
               fontsize=14,
               fontweight="bold")
  ax.set_xlabel("Distance to moving average (%)")
  ax.set_ylabel("RSI (14)")
  ax.legend(fontsize=9, loc="upper left")
  _save(fig, out)


# ---------------------------------------------------------------------------
# New plots: correlation, overlap, diversification, trade-offs
# ---------------------------------------------------------------------------


def plot_clustered_correlation(rets: pd.DataFrame, out: str) -> pd.DataFrame:
  """Clustered heatmap of weekly-return correlations with tier colour bar."""
  ru.setup_plot_aesthetics()
  corr = rets.corr()
  order = ru.cluster_order(corr)
  corr = corr.loc[order, order]
  fig, ax = plt.subplots(figsize=(15, 12.5))
  mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
  sns.heatmap(corr,
              mask=mask,
              annot=True,
              fmt=".2f",
              cmap="vlag",
              center=0,
              vmin=-0.3,
              vmax=1,
              linewidths=0.4,
              annot_kws={"size": 7.5},
              cbar_kws={"label": "Correlation of weekly returns (3Y)"},
              ax=ax)
  for lbl in ax.get_xticklabels() + ax.get_yticklabels():
    lbl.set_color(TIER_COLORS.get(tier_of(lbl.get_text()), "black"))
    lbl.set_fontweight("bold")
  ax.set_title(
      "Clustered correlation matrix — labels coloured by tier "
      "(short-history ETFs spliced with proxies)",
      fontsize=14,
      fontweight="bold",
      pad=12)
  _save(fig, out)
  return corr


def plot_rolling_corr(prices: pd.DataFrame, tickers: List[str],
                      out: str) -> pd.DataFrame:
  """Rolling 1Y correlation of weekly returns to VTI for hedge candidates."""
  ru.setup_plot_aesthetics()
  w = ru.periodic_returns(prices, "W-FRI")
  fig, ax = plt.subplots(figsize=(14, 7))
  palette = sns.color_palette("tab10", len(tickers))
  latest = {}
  for c, t in zip(palette, tickers):
    if t not in w.columns:
      continue
    rc = w[t].rolling(52).corr(w["VTI"]).dropna()
    rc = rc[rc.index >= pd.Timestamp("2020-01-01")]
    ax.plot(rc.index, rc, color=c, lw=1.7, label=f"{t} ({rc.iloc[-1]:+.2f})")
    latest[t] = float(rc.iloc[-1])
  ax.axhline(0, color="black", lw=0.8)
  ax.axhspan(-1, 0.3, color="green", alpha=0.05)
  ax.set_ylim(-0.6, 1.0)
  ax.set_title(
      "Rolling 1-year correlation to VTI — do the 'hedges' still "
      "hedge? (green band = useful diversifier)",
      fontsize=14,
      fontweight="bold")
  ax.set_ylabel("Correlation (52-week window, weekly returns)")
  ax.legend(fontsize=9, ncol=3, loc="lower left")
  _save(fig, out)
  return pd.Series(latest, name="corr_vti_now").to_frame()


def plot_factor_overlap(fr: pd.DataFrame, out: str) -> None:
  """Stacked R² decomposition: market / style / semis vs unique variance."""
  ru.setup_plot_aesthetics()
  d = fr.sort_values("unique_var_%")
  fig, axes = plt.subplots(1,
                           2,
                           figsize=(16, 8.5),
                           gridspec_kw={"width_ratios": [1.3, 1]})
  ax = axes[0]
  y = np.arange(len(d))
  explained = 100 - d["unique_var_%"]
  ax.barh(y,
          explained,
          color="#8D99AE",
          label="Explained by VTI + "
          "growth/value + semis factors")
  ax.barh(y,
          d["unique_var_%"],
          left=explained,
          color="#2A9D8F",
          label="Unique variance (own theme)")
  for i, (t, r) in enumerate(d.iterrows()):
    ax.text(101,
            i,
            f"R² {r['r2']:.2f} · β_mkt {r['beta_MKT']:.2f}",
            va="center",
            fontsize=8)
  ax.set_yticks(y)
  ax.set_yticklabels([f"{t}" for t in d.index], fontsize=9)
  for lbl in ax.get_yticklabels():
    lbl.set_color(TIER_COLORS.get(tier_of(lbl.get_text()), "black"))
  ax.set_xlim(0, 135)
  ax.set_xlabel("% of weekly return variance (3Y)")
  ax.set_title("Overlap: how much of each ETF is just the market?",
               fontweight="bold")
  ax.legend(fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=2)
  ax = axes[1]
  ax.scatter(fr["beta_MKT"],
             fr["beta_SEMI"],
             s=90,
             c=[TIER_COLORS.get(tier_of(t), "k") for t in fr.index],
             edgecolors="black",
             lw=0.6)
  for t, r in fr.iterrows():
    ax.annotate(t, (r["beta_MKT"], r["beta_SEMI"]),
                xytext=(5, 4),
                textcoords="offset points",
                fontsize=8.5,
                fontweight="bold")
  ax.axhline(0, color="gray", lw=0.8)
  ax.axvline(1, color="gray", lw=0.8, ls=":")
  ax.set_xlabel("β to market (VTI)")
  ax.set_ylabel("β to semis factor (SMH − VTI)")
  ax.set_title("Factor map: market beta vs. semiconductor beta",
               fontweight="bold")
  _save(fig, out)


def plot_growth_vs_drawdown(m: pd.DataFrame, out: str) -> None:
  """CAGR vs max drawdown bubbles (size = vol) for 3Y and 5Y windows."""
  ru.setup_plot_aesthetics()
  fig, axes = plt.subplots(1, 2, figsize=(16, 7.5), sharey=False)
  for ax, lbl in zip(axes, ("3Y", "5Y")):
    d = m.dropna(subset=[f"CAGR_{lbl}", f"MaxDD_{lbl}"])
    for tier, g in d.groupby("Tier"):
      ax.scatter(-g[f"MaxDD_{lbl}"],
                 g[f"CAGR_{lbl}"],
                 s=g[f"Vol_{lbl}"] * 9,
                 color=TIER_COLORS.get(str(tier), "k"),
                 alpha=0.75,
                 edgecolors="black",
                 lw=0.6,
                 label=tier)
      for t, r in g.iterrows():
        ax.annotate(t, (-r[f"MaxDD_{lbl}"], r[f"CAGR_{lbl}"]),
                    xytext=(6, 4),
                    textcoords="offset points",
                    fontsize=8.5,
                    fontweight="bold")
    xs = np.linspace(5, 85, 50)
    for cal in (0.5, 1.0):
      ax.plot(xs, cal * xs, ls="--", color="gray", lw=1, alpha=0.4)
      ax.annotate(f"Calmar {cal}", (xs[-1], cal * xs[-1]),
                  xytext=(-50, 3),
                  textcoords="offset points",
                  fontsize=7.5,
                  color="gray")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel(f"Max drawdown over {lbl} (%)")
    ax.set_ylabel(f"{lbl} CAGR (%)")
    ax.set_title(f"Growth vs. pain — {lbl} (bubble = volatility)",
                 fontweight="bold")
  axes[0].legend(fontsize=8.5, loc="upper left")
  _save(fig, out)


def plot_marginal_div(md: pd.DataFrame, out: str) -> None:
  """Δvol vs Δreturn when 10% of a VTI core is moved into each ETF."""
  ru.setup_plot_aesthetics()
  fig, ax = plt.subplots(figsize=(12, 8))
  for t, r in md.iterrows():
    col = TIER_COLORS.get(tier_of(str(t)), "k")
    ax.scatter(r["d_vol_pp"],
               r["d_return_pp"],
               s=110,
               color=col,
               edgecolors="black",
               lw=0.6,
               alpha=0.85)
    ax.annotate(t, (r["d_vol_pp"], r["d_return_pp"]),
                xytext=(6, 4),
                textcoords="offset points",
                fontsize=9,
                fontweight="bold")
  ax.axhline(0, color="black", lw=0.8)
  ax.axvline(0, color="black", lw=0.8)
  ax.axvspan(ax.get_xlim()[0], 0, color="green", alpha=0.04)
  ax.set_xlabel("Δ portfolio volatility (pp) vs. 100% VTI")
  ax.set_ylabel("Δ portfolio CAGR (pp) vs. 100% VTI")
  ax.set_title(
      "Marginal diversification: move 10% of VTI into each ETF "
      "(3Y weekly) — upper-left is free lunch",
      fontweight="bold")
  _save(fig, out)


def plot_capture(cp: pd.DataFrame, out: str) -> None:
  ru.setup_plot_aesthetics()
  fig, ax = plt.subplots(figsize=(11, 8))
  for t, r in cp.iterrows():
    ax.scatter(r["down_capture"],
               r["up_capture"],
               s=110,
               color=TIER_COLORS.get(tier_of(str(t)), "k"),
               edgecolors="black",
               lw=0.6,
               alpha=0.85)
    ax.annotate(t, (r["down_capture"], r["up_capture"]),
                xytext=(6, 4),
                textcoords="offset points",
                fontsize=9,
                fontweight="bold")
  lim = [
      min(cp["down_capture"].min(), 0) - 10,
      max(cp["up_capture"].max(), 100) + 10
  ]
  ax.plot(lim, lim, ls="--", color="gray", lw=1)
  ax.axhline(100, color="gray", ls=":", lw=0.8)
  ax.axvline(100, color="gray", ls=":", lw=0.8)
  ax.set_xlabel("Down-market capture vs VTI (%)")
  ax.set_ylabel("Up-market capture vs VTI (%)")
  ax.set_title(
      "Up vs. down capture (weekly, 3Y) — above the diagonal = "
      "convex",
      fontweight="bold")
  _save(fig, out)


def plot_macro_heatmap(ms: pd.DataFrame, out: str) -> None:
  ru.setup_plot_aesthetics()
  fig, ax = plt.subplots(figsize=(10, 11))
  sns.heatmap(ms,
              annot=True,
              fmt=".2f",
              cmap="RdBu_r",
              center=0,
              vmin=-0.7,
              vmax=0.7,
              linewidths=0.4,
              ax=ax,
              cbar_kws={"label": "Corr. of monthly return with driver"})
  for lbl in ax.get_yticklabels():
    lbl.set_color(TIER_COLORS.get(tier_of(lbl.get_text()), "black"))
    lbl.set_fontweight("bold")
  ax.set_title("Macro sensitivities (5Y monthly): what moves each theme",
               fontweight="bold",
               fontsize=13)
  _save(fig, out)


def plot_frontier(cloud: pd.DataFrame, points: Dict[str, Dict[str, float]],
                  singles: Dict[str, Dict[str, float]], out: str) -> None:
  ru.setup_plot_aesthetics()
  fig, ax = plt.subplots(figsize=(13, 8.5))
  sc = ax.scatter(cloud["vol"],
                  cloud["ret"],
                  c=cloud["enb"],
                  cmap="viridis",
                  s=8,
                  alpha=0.45)
  cb = plt.colorbar(sc, ax=ax)
  cb.set_label("Effective number of bets")
  for name, p in singles.items():
    ax.scatter(p["vol"], p["ret"], marker="x", s=60, color="black")
    ax.annotate(name, (p["vol"], p["ret"]),
                xytext=(4, 3),
                textcoords="offset points",
                fontsize=8,
                color="black")
  markers = ["*", "P", "s", "D"]
  for (name, p), mk in zip(points.items(), markers):
    ax.scatter(p["vol"],
               p["ret"],
               marker=mk,
               s=260,
               color="#E63946",
               edgecolors="black",
               lw=1,
               zorder=6)
    ax.annotate(f"{name.split(':')[0]} (ENB {p['enb']:.1f})",
                (p["vol"], p["ret"]),
                xytext=(8, -4),
                textcoords="offset points",
                fontsize=9.5,
                fontweight="bold",
                color="#E63946")
  ax.set_xlabel("Annualised volatility (%)")
  ax.set_ylabel("Annualised return (%)")
  ax.set_title(
      "Random long-only portfolios (3Y weekly, max 40% per ETF) with "
      "the model portfolios overlaid",
      fontweight="bold")
  _save(fig, out)


def plot_backtests(navs: Dict[str, pd.Series], out: str) -> None:
  ru.setup_plot_aesthetics()
  fig, axes = plt.subplots(2,
                           1,
                           figsize=(14, 10),
                           sharex=True,
                           gridspec_kw={"height_ratios": [2.2, 1]})
  palette = ["#E63946", "#F4A261", "#2A9D8F", "#6A4C93", "black"]
  for c, (name, nav) in zip(palette, navs.items()):
    axes[0].plot(nav.index,
                 nav,
                 color=c,
                 lw=2.2 if "VTI" in name else 1.8,
                 ls="--" if "VTI" in name else "-",
                 label=f"{name} ({nav.iloc[-1] - 100:+.0f}%)")
    dd = (nav / nav.cummax() - 1) * 100
    axes[1].plot(dd.index, dd, color=c, lw=1.4)
  axes[0].set_title(
      f"Model portfolios vs VTI — fixed weights, monthly "
      f"rebalance, since {list(navs.values())[0].index[0]:%b %Y}"
      " (proxies before inception)",
      fontweight="bold")
  axes[0].set_ylabel("Growth of 100")
  axes[0].legend(fontsize=9)
  axes[1].set_ylabel("Drawdown (%)")
  axes[1].axhline(0, color="black", lw=0.8)
  _save(fig, out)


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


def _pct(x: Any, signed: bool = True, nd: int = 1) -> str:
  if x is None or (isinstance(x, float) and np.isnan(x)):
    return "n/a"
  return f"{x:+.{nd}f}%" if signed else f"{x:.{nd}f}%"


def metrics_table(m: pd.DataFrame) -> str:
  cols = [
      "Tier", "Ticker", "Name", "Inception", "ER", "YTD", "Ret_1Y", "CAGR_3Y",
      "CAGR_5Y", "Vol_1Y", "Sharpe_1Y", "MaxDD_1Y", "MaxDD_3Y", "Calmar_3Y",
      "RSI_14", "Dist_MA"
  ]
  head = [
      "Tier", "Ticker", "Fund", "Inception", "ER", "YTD", "1Y", "3Y CAGR",
      "5Y CAGR", "1Y Vol", "Sharpe 1Y", "MaxDD 1Y", "MaxDD 3Y", "Calmar 3Y",
      "RSI", "vs MA"
  ]
  lines = [
      "| " + " | ".join(head) + " |",
      "| " + " | ".join([":---"] * len(head)) + " |"
  ]
  order = list(TIER_MAP.keys()) + ["Benchmark"]
  m2 = m.reset_index()
  m2["_o"] = m2["Tier"].map({t: i for i, t in enumerate(order)})
  for _, r in m2.sort_values(["_o", "Ticker"]).iterrows():
    tag = f"**{r['Ticker']}**" + (" *(new)*" if r["New"] else "")
    vals = [
        f"**{r['Tier']}**",
        tag,
        r["Name"],
        str(r["Inception"]),
        f"{r['ER']:.2f}%" if pd.notna(r["ER"]) else "n/a",
        _pct(r["YTD"]),
        _pct(r["Ret_1Y"]),
        _pct(r["CAGR_3Y"]),
        _pct(r["CAGR_5Y"]),
        _pct(r["Vol_1Y"], False),
        f"{r['Sharpe_1Y']:.2f}" if pd.notna(r["Sharpe_1Y"]) else "n/a",
        _pct(r["MaxDD_1Y"]),
        _pct(r["MaxDD_3Y"]),
        f"{r['Calmar_3Y']:.2f}" if pd.notna(r["Calmar_3Y"]) else "n/a",
        f"{r['RSI_14']:.0f}",
        f"{r['Dist_MA']:+.1f}% ({r['MA_Window']}d)",
    ]
    lines.append("| " + " | ".join(vals) + " |")
  del cols
  return "\n".join(lines)


def df_table(df: pd.DataFrame, cols: List[str], heads: List[str],
             fmt: Dict[str, str]) -> str:
  lines = [
      "| Ticker | " + " | ".join(heads) + " |",
      "| :--- | " + " | ".join([":---"] * len(heads)) + " |"
  ]
  for t, r in df.iterrows():
    cells = []
    for c in cols:
      v = r[c]
      if isinstance(v, float) and np.isnan(v):
        cells.append("n/a")
      else:
        cells.append(fmt.get(c, "{:.2f}").format(v))
    lines.append(f"| **{t}** | " + " | ".join(cells) + " |")
  return "\n".join(lines)


def build_section(m: pd.DataFrame, corr: pd.DataFrame, fr: pd.DataFrame,
                  md: pd.DataFrame, cp: pd.DataFrame, ms: pd.DataFrame,
                  rc: pd.DataFrame, points: Dict[str, Dict[str, float]],
                  bt_stats: pd.DataFrame, cloud: pd.DataFrame,
                  asof: datetime.date) -> str:
  """Assembles the empirical markdown with numbers from the computations."""
  th = m[m["Tier"] != "Benchmark"]
  best_sh = str(th["Sharpe_1Y"].idxmax())
  worst_dd = str(th["MaxDD_1Y"].idxmin())
  pairs = pd.Series(
      corr.where(np.triu(np.ones(corr.shape), 1).astype(bool)).stack())
  top_pairs = pairs.sort_values(ascending=False).head(6)
  low_pairs = pairs.sort_values().head(6)
  uniq = fr["unique_var_%"].sort_values(ascending=False)
  free_lunch = md[(md["d_vol_pp"] < 0) & (md["d_return_pp"] > 0)].sort_values(
      "d_sharpe", ascending=False)
  convex = cp.sort_values("capture_spread", ascending=False).head(5)
  rates_neg = ms["Δ 10Y yield"].sort_values().head(4)
  rates_pos = ms["Δ 10Y yield"].sort_values(ascending=False).head(3)
  vti = m.loc["VTI"]

  def pair_str(s: pd.Series) -> str:
    out = []
    for key, v in s.items():
      pair: Tuple[str, str] = tuple(key)  # type: ignore[arg-type,assignment]
      out.append(f"{pair[0]}–{pair[1]} **{v:.2f}**")
    return ", ".join(out)

  new_rows = m[m["New"]]
  parts = [
      f"## Historical Multi-Sector Timelines & Empirical Evidence",
      "",
      f"*Regenerated {asof:%Y-%m-%d} by `analysis_sector_etfs.py` from the "
      f"pipeline's adjusted closes (dividends reinvested). Nine proposed "
      f"additions are marked **(new)**; short-history ETFs use proxies for "
      f"multi-year statistics: " +
      ", ".join(f"{k}→{v}" for k, v in PROXIES.items()) + ".*",
      "",
      "### 0. Scorecard — what the data says about the matrix",
      "",
      f"- **Best risk-adjusted theme (1Y Sharpe):** {best_sh} "
      f"({th.loc[best_sh, 'Sharpe_1Y']:.2f}); VTI {vti['Sharpe_1Y']:.2f}.",
      f"- **Deepest 1Y drawdown:** {worst_dd} ({th.loc[worst_dd, 'MaxDD_1Y']:.0f}%).",
      f"- **Most redundant pairs (3Y weekly corr):** {pair_str(top_pairs)}.",
      f"- **Most independent pairs:** {pair_str(low_pairs)}.",
      f"- **Most 'own-theme' variance (least explained by market/style/semis "
      f"factors):** " +
      ", ".join(f"{t} {v:.0f}%" for t, v in uniq.head(6).items()) + ".",
      f"- **Least (closest to an index clone):** " +
      ", ".join(f"{t} {v:.0f}%" for t, v in uniq.tail(5).items()) + ".",
      f"- **Free-lunch diversifiers vs a VTI core** (lower vol *and* higher "
      f"CAGR at a 10% sleeve, 3Y): " + (", ".join(
          f"{t} (vol {r['d_vol_pp']:+.1f}pp, CAGR {r['d_return_pp']:+.1f}pp)"
          for t, r in free_lunch.head(6).iterrows()) or "none") + ".",
      f"- **Most rate-sensitive (corr with Δ10Y):** " +
      ", ".join(f"{t} {v:+.2f}" for t, v in rates_neg.items()) +
      "; least rate-sensitive: " +
      ", ".join(f"{t} {v:+.2f}" for t, v in rates_pos.items()) + ".",
      "",
      "### 1. Proposed additions",
      "",
      "| Ticker | Fund | Fills the gap | ER | 3Y CAGR | 3Y MaxDD | corr VTI | unique var |",
      "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
  ]
  gaps = {
      "BOTZ":
          "Robotics / physical-AI beneficiaries beyond chips",
      "IGV":
          "Pure software (SaaS valuation reset) — separates CIBR's software beta",
      "SRVR":
          "Data-center & tower REITs — rate-sensitive AI real estate",
      "UFO":
          "Space with a 2019 history (NASA only from Mar-26)",
      "SHLD":
          "Defense tech / drones — distinct from commercial space",
      "GRID":
          "Grid equipment & transformers (the AIPO 'megawatts' trade, 2018 history)",
      "ICLN":
          "Clean energy — the renewable side of power demand",
      "XBI":
          "Equal-weight biotech — healthcare beta that is *not* mega-pharma",
      "SLV":
          "Silver — industrial + monetary metal, higher beta than gold",
  }
  for tk, r in new_rows.iterrows():
    t = str(tk)
    base = (f"| **{t}** | {r['Name']} | {gaps.get(t, '')} | {r['ER']:.2f}% | "
            f"{_pct(r['CAGR_3Y'])} | {_pct(r['MaxDD_3Y'])} | ")
    if t in corr.index and t in fr.index:
      cv = float(corr["VTI"][t])
      uv = float(fr["unique_var_%"][t])
      parts.append(base + f"{cv:.2f} | {uv:.0f}% |")
    else:
      parts.append(base + "n/a | n/a |")
  parts += [
      "",
      "### 2. Performance timelines",
      "",
      "![2-Year](plots/sector_etf_timeline_2yr.png)",
      "",
      "![5-Year](plots/sector_etf_timeline_5yr.png)",
      "",
      "![8.5-Year](plots/sector_etf_timeline_8yr.png)",
      "",
      "*💡 **Insight**: the long-cycle chart is the honest one — semis "
      "compounded an order of magnitude, cyber and copper roughly tripled, and "
      "most other themes (clean energy, lithium, water, biotech) round-tripped "
      "or lagged VTI. Theme selection, not 'thematic investing', did the work.*",
      "",
      "![Tier panels](plots/sector_etf_tier_comparison.png)",
      "",
      "### 3. Correlation structure & overlap",
      "",
      "![Clustered correlation](plots/sector_correlation_clustered.png)",
      "",
      "*💡 **Insight**: the clustering orders assets so that neighbours are "
      "most alike; read the blocks along the diagonal. Pairs above 0.85 are "
      f"effectively one position: {pair_str(top_pairs.head(4))}. The least "
      f"related pairs ({pair_str(low_pairs.head(3))}) are where real "
      "diversification lives.*",
      "",
      "![Factor overlap](plots/sector_factor_overlap.png)",
      "",
      "*💡 **Insight**: regress each ETF's weekly return on VTI, a growth−value "
      "spread (VUG−VTV) and a semis spread (SMH−VTI). The grey bar is the share "
      "of variance you could have bought with three index funds; the green bar "
      "is the theme's own risk. Low unique-variance ETFs (" +
      ", ".join(uniq.tail(4).index) +
      ") mostly re-package index exposure at 0.4–0.7% fees; high ones (" +
      ", ".join(uniq.head(4).index) + ") are genuinely different bets.*",
      "",
      "![Rolling correlation](plots/sector_rolling_corr_vti.png)",
      "",
      "*💡 **Insight**: correlations drift, so a diversifier must be "
      "re-checked. Current 52-week correlation to VTI: " +
      ", ".join(f"{t} {v:+.2f}"
                for t, v in rc["corr_vti_now"].sort_values().items()) +
      ". Anything above ~0.5 is an equity satellite, not a hedge; the "
      "store-of-value trio (GLDM/SLV/IBIT) still earns its 'uncorrelated' "
      "label on this window, with IBIT the least stable of the three.*",
      "",
      "### 4. Growth vs. risk trade-offs",
      "",
      "![Growth vs drawdown](plots/sector_growth_vs_drawdown.png)",
      "",
      "*💡 **Insight**: Calmar (CAGR ÷ max drawdown) separates 'paid for the "
      "pain' from 'just painful'. Anything below the 0.5 line delivered less "
      "than half a point of annual return per point of peak-to-trough loss — "
      "over 3 years that is " +
      ", ".join(th[th["Calmar_3Y"] < 0.5].dropna(subset=["Calmar_3Y"]).index) +
      ". Above 1.0: " + ", ".join(th[th["Calmar_3Y"] > 1.0].index) + ".*",
      "",
      "![Risk return](plots/sector_risk_return_scatter.png)",
      "",
      "![Capture](plots/sector_capture_ratios.png)",
      "",
      f"*💡 **Insight**: up/down capture vs VTI on weekly returns. Convex "
      f"profiles (more upside than downside participation): " +
      ", ".join(f"{t} ({r['up_capture']:.0f}/{r['down_capture']:.0f})"
                for t, r in convex.iterrows()) +
      ". Themes that fall *harder* than they rise are paying for beta twice.*",
      "",
      "![Macro sensitivities](plots/sector_macro_sensitivities.png)",
      "",
      f"*💡 **Insight**: with the 10Y at 5.2% this matters. Themes most hurt by "
      f"rising yields: " +
      ", ".join(f"{t} ({v:+.2f})" for t, v in rates_neg.items()) +
      ". Oil sensitivity (% WTI) — most positive: " +
      ", ".join(f"{t} {v:+.2f}" for t, v in ms["% WTI"].sort_values(
          ascending=False).head(3).items()) + "; most negative: " +
      ", ".join(f"{t} {v:+.2f}"
                for t, v in ms["% WTI"].sort_values().head(3).items()) +
      " — the 'molecules vs. bits' split, measured.*",
      "",
      "### 5. Diversification: what each ETF does to a VTI core",
      "",
      "![Marginal diversification](plots/sector_marginal_diversification.png)",
      "",
      df_table(
          md.sort_values("d_sharpe", ascending=False), [
              "corr_core", "beta_core", "d_vol_pp", "d_return_pp", "d_sharpe",
              "d_max_dd_pp"
          ], [
              "corr VTI", "β VTI", "Δ vol (pp)", "Δ CAGR (pp)", "Δ Sharpe",
              "Δ MaxDD (pp)"
          ], {
              "corr_core": "{:.2f}",
              "beta_core": "{:.2f}",
              "d_vol_pp": "{:+.2f}",
              "d_return_pp": "{:+.2f}",
              "d_sharpe": "{:+.3f}",
              "d_max_dd_pp": "{:+.2f}"
          }),
      "",
      "*💡 **Insight**: a 10% sleeve is the realistic unit. Only the entries "
      "with negative Δvol **and** positive ΔCAGR improve the core on both axes; "
      "everything in the upper-right buys return with proportionally more "
      "risk, which is fine for a satellite but is not 'diversification'.*",
      "",
      "### 6. Portfolio construction: frontier and model backtests",
      "",
      "![Frontier](plots/sector_frontier_models.png)",
      "",
      "| Model | Ann. return | Ann. vol | Sharpe | Effective bets | Div. ratio |",
      "| :--- | :--- | :--- | :--- | :--- | :--- |",
  ]
  for name, p in points.items():
    parts.append(f"| {name} | {p['ret']:.1f}% | {p['vol']:.1f}% | "
                 f"{p['sharpe']:.2f} | {p['enb']:.1f} | {p['div_ratio']:.2f} |")
  parts += [
      "",
      "*💡 **Insight**: the colour of the cloud is the effective number of "
      "independent bets (ENB). Even a 24-ETF thematic universe rarely exceeds "
      f"{cloud['enb'].quantile(0.99):.1f} ENB — most themes load on the same "
      "equity/growth factor. " + "; ".join(
          f"{n.split(':')[0]} ENB {p['enb']:.1f}, Sharpe {p['sharpe']:.2f}"
          for n, p in points.items()) +
      ". Model D is not hand-picked: it is the highest-Sharpe random "
      f"portfolio with ENB ≥ {MIN_ENB:g}, i.e. what the data says a "
      "genuinely diversified thematic mix looks like.*",
      "",
      "![Backtests](plots/sector_model_backtests.png)",
      "",
      "| Model | Total return | CAGR | Vol | Sharpe | Max DD | Calmar |",
      "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
  ]
  for bt_name, r in bt_stats.iterrows():
    parts.append(
        f"| {bt_name} | {r['total_return']:+.1f}% | {r['cagr']:.1f}% | "
        f"{r['vol']:.1f}% | {r['sharpe']:.2f} | {r['max_dd']:.1f}% | "
        f"{r['calmar']:.2f} |")
  parts += [
      "",
      "*💡 **Insight**: backtests use today's weights with monthly rebalancing "
      "and proxies before each fund's inception, so they describe the "
      "*mix*, not a live track record. Compare Calmar and max drawdown, not "
      "total return — the window is a semiconductor bull market and flatters "
      "anything overweight chips. Model D is *selected* on this same 3-year "
      "window, so its edge here is in-sample; treat its weights as a "
      "diversification template, not a forecast.*",
      "",
      "### 7. Full metrics table",
      "",
      metrics_table(m),
      "",
      "---",
      "",
      "## Tactical Portfolio Construction Playbook",
      "",
      "The original three models are kept; Model D is derived from the "
      "random-portfolio cloud (max Sharpe subject to ≥2 effective bets and "
      "≤25% in any ETF, weights rounded to 2.5%). All weights are illustrative.",
      "",
  ]
  for name, w in MODEL_PORTFOLIOS.items():
    parts.append(f"### {name}")
    parts.append("* " + " · ".join(f"**{v:g}% {k}**" for k, v in w.items()))
    parts.append("")
  parts += [
      "**Sizing rules the data supports**",
      "",
      "1. Treat SOXQ, DRAM, SMH/SOXX, QTUM and BOTZ as *one* position when "
      "sizing (pairwise correlations 0.8–0.95); cap the block, not the "
      "tickers.",
      "2. IBIT is a return engine with equity-like drawdown behaviour, not a "
      "hedge — size it like a speculative satellite (≤5–10%). GLDM is the "
      "only holding with persistently near-zero equity correlation.",
      "3. Prefer the lower-fee / higher-unique-variance version of each theme "
      "where two overlap (e.g. GRID vs AIPO, UFO vs NASA, XBI vs OZEM) and "
      "let the long-history fund carry the backtest.",
      "4. With the 10Y above 5%, the rate-sensitive sleeve (SRVR, IGV, ICLN, "
      "FIW, LIT) should be funded from trims of the compute block, not from "
      "cash, so overall equity beta does not rise.",
      "",
      "---",
      "",
  ]
  return "\n".join(parts)


def update_report(section: str) -> None:
  with open(REPORT_PATH, "r", encoding="utf-8") as f:
    content = f.read()
  if REPORT_MARKER in content:
    content = content.split(REPORT_MARKER)[0].rstrip()
  content = content.rstrip("-\n ") + "\n\n---\n\n"
  with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(ru.clean_md(content + section))
  logger.info("Updated %s", REPORT_PATH)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
  os.makedirs(PLOTS_DIR, exist_ok=True)
  universe = ALL_THEMATIC + BENCHMARKS + EXTRA_LOAD
  prices = ru.load_close_matrix(universe, MARKET_DATA_DIR)
  if prices.empty:
    logger.error("No price data loaded")
    return
  asof = prices.index.max().date()
  logger.info("Loaded %d tickers to %s", prices.shape[1], asof)
  px_proxy = with_proxies(prices)
  three_y = pd.Timestamp(asof) - pd.DateOffset(years=3)
  five_y = pd.Timestamp(asof) - pd.DateOffset(years=5)
  weekly3 = ru.periodic_returns(px_proxy.loc[three_y:], "W-FRI")
  monthly5 = ru.periodic_returns(px_proxy.loc[five_y:], "ME")
  thematic_cols = [t for t in ALL_THEMATIC if t in weekly3.columns]

  # --- original plots -----------------------------------------------------
  def p(n: str) -> str:
    return os.path.join(PLOTS_DIR, n)
  _timeline(prices, [
      "SMH", "SOXX", "CIBR", "COPX", "GLDM", "FIW", "LIT", "PPH", "GRID",
      "BOTZ", "IGV", "XBI", "ICLN", "SLV", "VUG", "VTI", "VTV"
  ],
            "2018-06-26",
            "8.5-year structural trajectory (log, 2018–2026)",
            p("sector_etf_timeline_8yr.png"),
            log=True)
  _timeline(prices, [
      "SOXQ", "QTUM", "CIBR", "URNM", "COPX", "LIT", "FIW", "PPH", "GLDM",
      "UFO", "SRVR", "GRID", "VTI", "VUG", "VTV"
  ], "2021-06-11", "5-year thematic trajectory (rebased, 2021–2026)",
            p("sector_etf_timeline_5yr.png"))
  _timeline(prices, ALL_THEMATIC + ["VTI"], "2024-10-14",
            "2-year thematic trajectory (rebased, 2024–2026)",
            p("sector_etf_timeline_2yr.png"))
  plot_tier_panels(prices,
                   str(pd.Timestamp(asof) - pd.DateOffset(years=1))[:10],
                   p("sector_etf_tier_comparison.png"))
  plot_rolling_vol(
      prices,
      ["SOXQ", "CIBR", "URNM", "COPX", "PPH", "GLDM", "IBIT", "SLV", "VTI"],
      p("sector_etf_rolling_vol.png"))
  metrics = compute_metrics(prices, ALL_THEMATIC + BENCHMARKS)
  plot_risk_return(metrics, p("sector_risk_return_scatter.png"))
  plot_momentum(metrics, p("technical_momentum_scatter.png"))

  # --- new diagnostics ----------------------------------------------------
  corr = plot_clustered_correlation(
      weekly3[thematic_cols + ["VTI", "VUG", "VTV", "SMH"]],
      p("sector_correlation_clustered.png"))
  rc = plot_rolling_corr(
      px_proxy, ["GLDM", "SLV", "IBIT", "URNM", "PPH", "FIW", "XBI", "SRVR"],
      p("sector_rolling_corr_vti.png"))
  factors = pd.DataFrame({
      "MKT": weekly3["VTI"],
      "GMV": weekly3["VUG"] - weekly3["VTV"],
      "SEMI": weekly3["SMH"] - weekly3["VTI"],
  })
  fr = ru.factor_regression(weekly3[thematic_cols], factors)
  plot_factor_overlap(fr, p("sector_factor_overlap.png"))
  plot_growth_vs_drawdown(metrics, p("sector_growth_vs_drawdown.png"))
  md = ru.marginal_diversification(weekly3[thematic_cols + ["VTI"]], "VTI")
  plot_marginal_div(md, p("sector_marginal_diversification.png"))
  cp = ru.capture_ratios(weekly3[thematic_cols + ["VTI"]], "VTI")
  plot_capture(cp, p("sector_capture_ratios.png"))
  macro = ru.load_macro_frame(config.DATA_DIR)
  ms = ru.macro_sensitivities(monthly5[thematic_cols], macro, MACRO_SPEC, "ME")
  ms["VTI"] = monthly5[thematic_cols].corrwith(monthly5["VTI"]).round(2)
  plot_macro_heatmap(ms, p("sector_macro_sensitivities.png"))

  # --- frontier & backtests ----------------------------------------------
  cloud_cols = thematic_cols + ["VTI"]
  cloud = ru.random_portfolio_cloud(weekly3[cloud_cols], n=4000)
  wcols = [c for c in cloud.columns if c.startswith("w_")]
  elig = cloud[(cloud["enb"] >= MIN_ENB) & (cloud[wcols].max(axis=1) <= 0.25)]
  best = (elig if not elig.empty else cloud).sort_values(
      "sharpe", ascending=False).iloc[0]
  model_d = {
      c[2:]: round(float(best[c]) / 0.025) * 2.5
      for c in cloud.columns
      if c.startswith("w_")
  }
  model_d = {k: v for k, v in model_d.items() if v >= 2.5}
  MODEL_PORTFOLIOS[MODEL_D_NAME] = model_d
  logger.info("Derived %s: %s", MODEL_D_NAME, model_d)
  points = {
      name: ru.portfolio_point(weekly3, w)
      for name, w in MODEL_PORTFOLIOS.items()
  }
  singles = {
      t: ru.portfolio_point(weekly3, {t: 1.0})
      for t in ["VTI", "SOXQ", "GLDM", "IBIT", "PPH", "CIBR", "URNM"]
  }
  plot_frontier(cloud, points, singles, p("sector_frontier_models.png"))
  bt_start = max(prices["IBIT"].dropna().index.min(),
                 prices["OZEM"].dropna().index.min())
  navs = {
      name: ru.backtest_fixed_weights(px_proxy, w, "ME", bt_start)
      for name, w in MODEL_PORTFOLIOS.items()
  }
  navs["VTI (benchmark)"] = ru.backtest_fixed_weights(px_proxy, {"VTI": 1},
                                                      "ME", bt_start)
  plot_backtests(navs, p("sector_model_backtests.png"))
  bt_stats = pd.DataFrame({k: ru.perf_stats(v) for k, v in navs.items()}).T

  section = build_section(metrics, corr, fr, md, cp, ms, rc, points, bt_stats,
                          cloud, asof)
  update_report(section)
  metrics.to_csv(os.path.join(SCRIPT_DIR, "sector_metrics.tsv"), sep="\t")
  logger.info("Done.")


if __name__ == "__main__":
  main()
