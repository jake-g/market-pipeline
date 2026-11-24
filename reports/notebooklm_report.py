#!/usr/bin/env python3
import argparse
import asyncio
from datetime import datetime
from datetime import timedelta
import glob
import hashlib
import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_fetcher import MarketFetcher
from reports.notebooklm_client import looks_like_studio_stub
from reports.notebooklm_client import MarketNewsClient
from reports.notebooklm_client import matches_source_title
from reports.notebooklm_client import NotebookLMQuotaError
from reports.notebooklm_client import title_date
from reports.report_utils import clean_md

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- NOTEBOOKLM PROMPT CONSTANTS ---

# Shared tail for every synthesis prompt. The first rule exists because
# NotebookLM's chat now sometimes "publishes" a Studio report and answers
# with a one-paragraph confirmation instead of the text.
OUTPUT_RULES = """
OUTPUT RULES (non-negotiable):
1. Return the COMPLETE report as markdown text in this chat reply. Do NOT create a Studio report, note, document or file, and do NOT reply with a summary of what you created.
2. Every price/return number MUST come from the AUTHORITATIVE QUANTITATIVE SNAPSHOT and "Quantitative Price Action Summary" (e.g. "+4.71%"), never words like "Strong Rebound". NEVER write "n/a" for SPY, QQQ, SOXX, or any Watchlist / Winner / Loser ticker whose exact percentage is listed in the quantitative snapshot.
3. Cite inline with [n] and end with a numbered "## References" appendix mapping every [n] to the exact Source Headline and URL from the uploaded text. No uncited claims about events.
4. Be dense: short declarative sentences, bullets over prose, no filler, no restating the prompt, no disclaimers.
5. If qualitative news for a specific ticker is thin, still report its exact quantitative return and note "no company-specific news" rather than writing "n/a" for its return.
"""

PRIORITY_WATCHLIST = ("NVDA", "TSM", "AMD", "AVGO", "MRVL", "MU", "ANET",
                      "COHR", "WDC", "SMH", "SOXX", "IONQ", "CRWV", "IREN",
                      "AAPL", "AMZN", "GOOG", "TSLA", "PANW", "HOOD", "NLR",
                      "CCJ", "NVT", "VST", "CEG", "IBIT", "BMNR", "RKLB", "STM",
                      "ENTG", "MRK")

REGIME_BENCHMARKS = ("SPY", "QQQ", "SOXX", "SMH", "IWM", "DIA", "TLT", "^VIX",
                     "^TNX", "BTC-USD", "GC=F", "CL=F")

WATCHLIST_HINT = (
    "Priority tickers when choosing what to cover (these are held "
    "or tracked): " + ", ".join(PRIORITY_WATCHLIST) +
    ", plus SPY/QQQ/SOXX as benchmarks.")

PROMPT_DAILY = """You are a buy-side analyst writing the daily market intelligence note for {date}.

DATA PRIORITY: the source titled "{date} Daily Market Feed" and "{date} Daily Market Feed - Quantitative Price Action Summary" are the foundation. Use "Historical Context" only to note how a theme evolved; never summarise prior reports.

""" + WATCHLIST_HINT + """

STRUCTURE (use these exact headers):
## Regime Dashboard
One compact markdown table: SPY, QQQ, SOXX 1-day % (from the summary); the single most important macro print or event of the day; and a one-word risk posture (Risk-On / Neutral / Risk-Off) with a 1-sentence justification.

## Top AI Thematic Insights
3-4 themes max. For each: "### <Theme> (<tickers>)" then 2-3 bullets: what happened (with numbers), why it matters, what it changes going forward. Prefer themes that touch the priority tickers. Finish with "### Expert Forward Projection": 3 bullets, each a falsifiable near-term expectation with the trigger to watch.

## Quantitative Market Action & Specific Equities
Two markdown tables, "Top Winners" and "Top Losers", from TODAY'S summary: columns Ticker | 1-Day % | Catalyst (with citation). 5-8 rows each. Exact percentages only.

## Watchlist Check
A table for every priority ticker that appears in today's feed or summary: Ticker | 1-Day % | One-line read (continuation / reversal / news-driven / no news). Omit tickers with no data rather than guessing.
""" + OUTPUT_RULES

PROMPT_WEEKLY = """You are a macro strategist writing the weekly synthesis for {start_date} to {end_date}.

DATA PRIORITY: the "{start_date} to {end_date} Market Synthesis" source and its "Quantitative Price Action Summary" are the foundation; the uploaded daily reports for the week provide the day-by-day arc. Zoom out: thematic shifts, sector rotation and weekly aggregates, not single-day noise.

""" + WATCHLIST_HINT + """

STRUCTURE (use these exact headers):
## Week in One Table
Markdown table: SPY, QQQ, SOXX weekly % (from the summary) | best and worst sector/theme of the week with % | the macro event that mattered most | risk posture for next week (Risk-On / Neutral / Risk-Off).

## Top AI Thematic Insights
3-5 themes. "### <Theme> (<tickers>)" then bullets: the weekly narrative arc (Mon→Fri where visible), the numbers, and what it changes. Explicitly flag any theme that REVERSED versus the prior week's report. Finish with "### Expert Forward Projection": 3-4 falsifiable expectations for the coming 1-3 weeks, each with the data point or event that would confirm or refute it.

## Quantitative Market Action & Specific Equities
Two markdown tables, "Top Winners" and "Top Losers", from the WEEKLY summary: Ticker | Week % | Catalyst (with citation). 6-10 rows each. Exact percentages only.

## Watchlist Check
Table for every priority ticker with a weekly number: Ticker | Week % | vs SPY (pct-pts) | Read (leading / lagging / event-driven). Then 3 bullets: "What I would do differently going into next week" framed as trims, adds and cash, no options or leverage.
""" + OUTPUT_RULES

PROMPT_MONTHLY = """You are a macroeconomic analyst powered by NotebookLM. Write a highly detailed, insightful, and data-driven monthly synthesis report for {month_year}.

FOCUS strictly on structural economic trends, monthly narrative arcs, and major macro pivots. Tell a unified story of the month, summarizing the aggregate narrative rather than a daily log of details.

STRUCTURE THE REPORT EXACTLY AS FOLLOWS:
## Top AI Thematic Insights
Write a highly structured, deeply analytical executive summary grouping exactly the major themes and catalysts that defined this month. Highlight structural shifts or trends, drawing benchmarks against previous uploaded continuous context tracking. Break the broader market narrative and key events down chronologically into a Week-by-Week timeline here. Conclude this section with an **Expert Forward Projection**, offering institutional-level forecasts for the coming months based on the data. Provide expansive context and tell the story of the month.

## Quantitative Market Action & Specific Equities
Extract and rigorously analyze the top quantitative winners and losers provided in the Price Action Summary for the month. Correlate those specific stock returns to the uploaded qualitative news. Dig into the specific earnings reports, upgrades, or macro events driving those tickers for the month.
You MUST format this section using clean Markdown Tables (one for Top Winners, one for Top Losers) with columns for Ticker, Performance, and Detailed News Catalyst explaining the move.

CRITICAL FORMATTING RULES:
1. Provide deep, institutional-grade insights. Be highly actionable but do not sacrifice detail for brevity. Avoid generic fluff. Use terse bullet points and numerical tables for structure, but write thick paragraphs for analysis.
2. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown.""" + OUTPUT_RULES

PROMPT_YEARLY = """You are a macroeconomic analyst powered by NotebookLM. Write a highly detailed, data-driven yearly synthesis report for {year}.

STRUCTURE THE REPORT EXACTLY AS FOLLOWS:

## Executive Summary: The Year in Review
Write a highly structured, authoritative executive summary grouping the major overarching themes, stock market performance, and catalysts that defined the year. Highlight major structural shifts or tech trends.

## Quarterly Chronology
Break the overarching market narrative and structural economic shifts down chronologically into a Quarter-by-Quarter timeline (Q1-Q4). Summarize the defining moments, market reactions, and major geopolitical/macro events for each distinct quarter.

## Quantitative Market Action & Specific Equities
Extract and rigorously analyze the top quantitative winners and losers provided in the Price Action Summary. Correlate those specific stock returns ($, +%) to events from the qualitative news text where applicable.
You MUST format this section using clean Markdown Tables (one for Top Winners, one for Top Losers) with columns for Ticker, Performance, and News Catalyst explaining the move.

CRITICAL FORMATTING RULES:
1. Be extremely actionable and data-driven. Avoid fluff and wordiness. Use terse bullet points and numerical tables.
2. Highlight major defining moments of the year and provide concrete, numerical evidence when available.
3. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown.""" + OUTPUT_RULES

PROMPT_YEARLY_PROSPECTIVE = """You are a macroeconomic analyst powered by NotebookLM. Write a highly detailed, data-driven prospective synthesis report for {year}.

STRUCTURE THE REPORT EXACTLY AS FOLLOWS:

## Executive Summary: Outlook for {year}
Write a highly structured, authoritative executive summary grouping the major overarching themes, stock market forecasts, and potential catalysts expected for the year. Highlight major structural shifts or tech trends anticipated by experts.

## Key Forecasts & Major Events
Summarize the defining predictions, market expectations, and major geopolitical/macro events to watch for over the next 12 months.

## Sectors to Watch & Predictive Scenarios
Highlight which sectors or specific fields (e.g., AI, Energy) are expected to overperform or underperform and provide the rationale.
You MUST format this section cleanly, focusing on actionable insights.

CRITICAL FORMATTING RULES:
1. Be extremely actionable and data-driven. Avoid fluff and wordiness. Use terse bullet points.
2. Highlight major anticipated moments of the year and provide concrete, numerical evidence when available.
3. You MUST include a numbered '## References' appendix at the very end of your response. Map every single inline citation (e.g., [1], [2]) to the exact Source URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown.""" + OUTPUT_RULES

PROMPT_PORTFOLIO = """You are an elite portfolio manager powered by NotebookLM. Review the provided tabular text data representing my exact stock holdings, their recent performance metrics, and the latest news context to answer a basic question based on the portfolio report.

Provide actionable, single-account specific trade advice (Buy/Sell/Exchange) for the Active Trading Portfolios section, categorized by High, Medium, or Low priority.

PRIORITIZE analyzing the **Active Trading Portfolios** section. This is my short-term/tactical allocation where I deploy active liquidity buffers.

Write a concise tactical summary focusing heavily on the Active portfolio's health.
Identify the top 3 most overextended names (ripe for profit-taking) and the top 3 deepest value traps in the Active section.
Identify any key portfolio concentrations within the Active holdings.
Crucially, provide actionable, single-account specific trade advice (buy/sell/hold) for this week and near term regarding the Active positions.

CRITICAL INSTRUCTIONS:
1. MAX 50 words per paragraph. NO FLUFF. Use numbers and terse bullet points.
2. Ensure strict logical consistency between your advice and the provided data tables. If a stock is up 200%, do not call it a value play.
3. 🚫 DO NOT suggest Options, Puts, Calls, or Margin trading.
4. ⚖️ Suggest trades to either deploy known liquid reserve or sell to raise more liquidity.
5. 🧭 Explicitly call back to the provided decision trees. Agree or contradict the main report's branches based on your analysis.
6. Keep the output extremely concise and format it using valid Markdown headers. Include a numbered '## References' appendix mapping inline citations (e.g., [1]) to the exact Source Headline and URL provided.""" + OUTPUT_RULES

PROMPT_EARNINGS = """You are an elite equity research analyst powered by NotebookLM. Review the provided tabular data, historical price action, Implied Volatility (IV) crush metrics, and the latest news context for this specific earnings event.

Write a HIGHLY CONCISE, zoomed-out tactical and macro analysis focused strictly on this particular ticker and its surrounding industry context.

CRITICAL INSTRUCTIONS:
1. MAX 50 words per paragraph. NO FLUFF. Use numbers and terse bullet points.
2. Provide predictive scenarios based strictly on the provided quantitative data (historical gap fades, post-earnings drift) and support them with qualitative catalysts from the news.
3. Contrast this ticker's earnings narrative with broader macroeconomic or sector-wide trends mentioned in the news to provide deeper, zoomed-out insights. Focus heavily on price trends and historical data. Do NOT mention random portfolio allocation or other tickers unless directly used to contrast the primary ticker's performance or ecosystem.
4. You MUST include a numbered '## References' appendix at the very end. Map every single inline citation (e.g., [1], [2]) to the exact Source Headline and URL provided in the uploaded text so the reader can find the original article. Strictly format as Markdown.""" + OUTPUT_RULES


def _read_fundamental_metrics(ticker_path: str) -> Dict[str, str]:
  """Reads key valuation metrics (Fwd P/E, Mkt Cap) from fundamentals.tsv."""
  fpath = os.path.join(ticker_path, "fundamentals.tsv")
  out: Dict[str, str] = {"FwdPE": "-", "MktCap": "-"}
  if not os.path.exists(fpath):
    return out
  try:
    df = pd.read_csv(fpath, sep="\t")
    if "Metric" not in df.columns or "Value" not in df.columns:
      return out
    kv = dict(zip(df["Metric"].astype(str), df["Value"].astype(str)))
    pe_raw = kv.get("forwardPE") or kv.get("trailingPE")
    if pe_raw and pe_raw.lower() not in ("none", "nan"):
      out["FwdPE"] = f"{float(pe_raw):.1f}x"
    mc_raw = kv.get("marketCap")
    if mc_raw and mc_raw.lower() not in ("none", "nan"):
      mc = float(mc_raw)
      if mc >= 1e12:
        out["MktCap"] = f"${mc / 1e12:.2f}T"
      elif mc >= 1e9:
        out["MktCap"] = f"${mc / 1e9:.1f}B"
      elif mc >= 1e6:
        out["MktCap"] = f"${mc / 1e6:.0f}M"
  except Exception:
    pass
  return out


def _compute_price_records(market_data_dir: str, start_date: Optional[datetime],
                           end_date: Optional[datetime]) -> pd.DataFrame:
  """Computes exact return, price, 5D trend, and valuation rows for tickers."""
  tickers_dir = os.path.join(market_data_dir, "tickers")
  if not os.path.exists(tickers_dir):
    return pd.DataFrame()

  start_norm = (pd.Timestamp(start_date).tz_localize(None).normalize()
                if start_date else None)
  end_norm = (pd.Timestamp(end_date).tz_localize(None).normalize()
              if end_date else None)
  is_single_day = (start_norm is not None and end_norm is not None and
                   start_norm == end_norm)
  watchlist_set = set(PRIORITY_WATCHLIST) | set(REGIME_BENCHMARKS)

  results: List[Dict[str, Any]] = []
  for ticker_path in glob.glob(os.path.join(tickers_dir, "*")):
    if not os.path.isdir(ticker_path):
      continue
    ticker = os.path.basename(ticker_path)
    if " " in ticker:
      continue  # Skip legacy trust directories with NaN placeholders.
    prices_file = os.path.join(ticker_path, "prices.tsv")
    if not os.path.exists(prices_file):
      continue

    try:
      df = pd.read_csv(prices_file, sep="\t")
      if "Date" not in df.columns or "Close" not in df.columns:
        continue
      df = df.dropna(subset=["Close"]).copy()
      if df.empty:
        continue
      df["ParsedDate"] = (pd.to_datetime(
          df["Date"], utc=True).dt.tz_localize(None).dt.normalize())
      df = df.sort_values("ParsedDate").reset_index(drop=True)

      mask = pd.Series(True, index=df.index)
      if start_norm is not None:
        mask = mask & (df["ParsedDate"] >= start_norm)
      if end_norm is not None:
        mask = mask & (df["ParsedDate"] <= end_norm)
      df_range = df[mask]

      # Holiday / intraday pre-close fallback on single-day lookups: use the
      # most recent trading session within 4 days <= end_norm.
      if df_range.empty and is_single_day and end_norm is not None:
        recent = df[(df["ParsedDate"] <= end_norm) &
                    (df["ParsedDate"] >= end_norm - pd.Timedelta(days=4))]
        df_range = recent.tail(1)

      if df_range.empty:
        continue

      first_pos = int(df_range.index[0])
      last_pos = int(df_range.index[-1])
      end_price = float(df.iloc[last_pos]["Close"])
      as_of_date = df.iloc[last_pos]["ParsedDate"].strftime("%Y-%m-%d")

      # Always anchor period return to the prior trading session's close so
      # Monday moves are included in Mon-Fri weekly windows.
      if first_pos > 0:
        start_price = float(df.iloc[first_pos - 1]["Close"])
      elif len(df_range) > 1:
        start_price = float(df_range.iloc[0]["Close"])
      elif "Open" in df_range.columns and pd.notna(df_range.iloc[0]["Open"]):
        start_price = float(df_range.iloc[0]["Open"])
      else:
        continue

      if start_price <= 0:
        continue

      high_price = (float(df_range["High"].max())
                    if "High" in df_range.columns else end_price)
      low_price = (float(df_range["Low"].min())
                   if "Low" in df_range.columns else end_price)
      return_pct = ((end_price - start_price) / start_price) * 100.0

      ret_5d: Optional[float] = None
      if last_pos >= 5 and float(df.iloc[last_pos - 5]["Close"]) > 0:
        p5 = float(df.iloc[last_pos - 5]["Close"])
        ret_5d = ((end_price - p5) / p5) * 100.0

      fund = (_read_fundamental_metrics(ticker_path)
              if ticker in watchlist_set else {
                  "FwdPE": "-",
                  "MktCap": "-"
              })
      results.append({
          "Ticker": ticker,
          "As_Of": as_of_date,
          "Return_Pct": return_pct,
          "Ret_5D": ret_5d,
          "Start_Price": start_price,
          "End_Price": end_price,
          "High": high_price,
          "Low": low_price,
          "FwdPE": fund["FwdPE"],
          "MktCap": fund["MktCap"],
      })
    except Exception:
      continue

  if not results:
    return pd.DataFrame()
  out_df = pd.DataFrame(results)
  if is_single_day:
    spy_rows = out_df[out_df["Ticker"] == "SPY"]
    if not spy_rows.empty:
      session_as_of = str(spy_rows.iloc[0]["As_Of"])
      keep_mask = (out_df["As_Of"] >= session_as_of) | (
          out_df["Ticker"].isin(REGIME_BENCHMARKS))
      out_df = out_df[keep_mask]
  return out_df.sort_values("Return_Pct",
                            ascending=False).reset_index(drop=True)


def _filter_equity_movers(res_df: pd.DataFrame) -> pd.DataFrame:
  """Filters price records to clean equities/ETFs for Winner/Loser rankings."""
  if res_df.empty:
    return res_df

  def _is_eligible(ticker: str) -> bool:
    if ticker in {"VIXY", "MUZ"}:
      return False
    if ticker.startswith("^") or "=F" in ticker or ticker.endswith("-USD"):
      return False
    if len(ticker) == 5 and ticker.endswith("X"):
      return False
    return True

  filtered = res_df[res_df["Ticker"].map(_is_eligible)]
  return filtered if not filtered.empty else res_df


def _build_macro_political_snapshot(market_data_dir: str,
                                    end_date: Optional[datetime]) -> str:
  """Builds a compact macro (FRED), shipping, and Polymarket snapshot."""
  end_bound = (pd.Timestamp(end_date).tz_localize(None).normalize()
               if end_date else pd.Timestamp.now().normalize())
  lines: List[str] = []

  macro_path = os.path.join(market_data_dir, "macro", "economic_indicators.tsv")
  if os.path.exists(macro_path):
    try:
      mdf = pd.read_csv(macro_path, sep="\t")
      date_col = "DATE" if "DATE" in mdf.columns else mdf.columns[0]
      mdf["_dt"] = pd.to_datetime(mdf[date_col], errors="coerce")
      mdf = mdf[mdf["_dt"] <= end_bound]
      wanted_macro = [
          "US10Y", "US02Y", "FEDFUNDS", "HY_SPREAD", "WTI_CRUDE", "USD_INDEX",
          "CPI", "UNRATE"
      ]
      parts = []
      for col in wanted_macro:
        if col in mdf.columns:
          valid = mdf[[date_col, col]].dropna()
          if not valid.empty:
            val = float(valid.iloc[-1][col])
            parts.append(f"{col}={val:.2f}")
      if parts:
        lines.append("FRED Macro: " + ", ".join(parts))
    except Exception:
      pass

  ship_path = os.path.join(market_data_dir, "shipping",
                           "chokepoint_metrics.tsv")
  if os.path.exists(ship_path):
    try:
      sdf = pd.read_csv(ship_path, sep="\t")
      sdf["_dt"] = pd.to_datetime(sdf["Date"], errors="coerce")
      sdf = sdf[sdf["_dt"] <= end_bound]
      if not sdf.empty:
        expected = sdf["Chokepoint_Name"].nunique()
        by_dt = sdf.groupby("_dt")["Chokepoint_Name"].nunique()
        comp = by_dt[by_dt >= expected]
        best_dt = comp.index.max() if not comp.empty else sdf["_dt"].max()
        sub = sdf[sdf["_dt"] == best_dt].sort_values("Chokepoint_Name")
        items = [
            f"{r['Chokepoint_Name']}={int(r['Vessel_Count'])}v "
            f"({float(r['Congestion_Index']):.2f}x)" for _, r in sub.iterrows()
        ]
        lines.append(f"Chokepoints (as of {best_dt.strftime('%Y-%m-%d')}): " +
                     ", ".join(items))
    except Exception:
      pass

  pol_path = os.path.join(market_data_dir, "political", "political_odds.tsv")
  if os.path.exists(pol_path):
    try:
      pdf = pd.read_csv(pol_path, sep="\t")
      if {"Date", "Key", "Outcome", "Prob"}.issubset(pdf.columns):
        pdf["_dt"] = pd.to_datetime(pdf["Date"], errors="coerce")
        pdf = pdf[pdf["_dt"] <= end_bound]
        if not pdf.empty:
          latest_pol = pdf[pdf["_dt"] == pdf["_dt"].max()]
          focus_keys = ("fed_decision_dec_2026", "fed_cuts_2026",
                        "us_recession_2026", "china_tariff_2026",
                        "ai_bubble_burst", "hormuz_traffic_normal")
          pol_items = []
          for key in focus_keys:
            kdf = latest_pol[latest_pol["Key"] == key].sort_values(
                "Prob", ascending=False)
            if not kdf.empty:
              top = kdf.iloc[0]
              prob_pct = float(
                  top["Prob"]) * (100.0 if float(top["Prob"]) <= 1.0 else 1.0)
              pol_items.append(f"{key}[{top['Outcome']}]={prob_pct:.0f}%")
          if pol_items:
            lines.append("Polymarket Odds: " + ", ".join(pol_items))
    except Exception:
      pass

  return "\n".join(lines)


def build_price_analysis_blob(market_data_dir: str,
                              start_date: Optional[datetime],
                              end_date: Optional[datetime]) -> str:
  """Builds a comprehensive quantitative price, watchlist, and macro summary."""
  res_df = _compute_price_records(market_data_dir, start_date, end_date)
  if res_df.empty:
    return ""

  by_ticker = {r["Ticker"]: r for _, r in res_df.iterrows()}
  spy_ret = by_ticker["SPY"]["Return_Pct"] if "SPY" in by_ticker else 0.0
  as_of = str(res_df["As_Of"].max())

  from tabulate import tabulate
  blob = f"### QUANTITATIVE PRICE ACTION SUMMARY (As of {as_of})\n\n"

  # 1. Regime Benchmarks Table
  bench_rows = []
  for b in REGIME_BENCHMARKS:
    if b in by_ticker:
      r = by_ticker[b]
      r5 = f"{r['Ret_5D']:+.2f}%" if pd.notna(r["Ret_5D"]) else "-"
      bench_rows.append([
          b, f"{r['Return_Pct']:+.2f}%", r5, f"${r['Start_Price']:.2f}",
          f"${r['End_Price']:.2f}", f"${r['Low']:.2f}-${r['High']:.2f}"
      ])
  if bench_rows:
    blob += "#### Regime Benchmarks & Cross-Asset Indicators\n"
    blob += tabulate(
        bench_rows,
        headers=["Benchmark", "Period %", "5D %", "Start", "Close", "Range"],
        tablefmt="pipe") + "\n\n"

  # 2. Priority Watchlist Table (with vs-SPY & Valuation)
  watch_rows = []
  for w in PRIORITY_WATCHLIST:
    if w in by_ticker:
      r = by_ticker[w]
      vs_spy = r["Return_Pct"] - spy_ret
      r5 = f"{r['Ret_5D']:+.2f}%" if pd.notna(r["Ret_5D"]) else "-"
      watch_rows.append([
          w, f"{r['Return_Pct']:+.2f}%", f"{vs_spy:+.2f}pp", r5,
          f"${r['End_Price']:.2f}", r["FwdPE"], r["MktCap"]
      ])
  if watch_rows:
    blob += "#### Priority Watchlist Performance & Valuation\n"
    blob += tabulate(watch_rows,
                     headers=[
                         "Ticker", "Period %", "vs SPY", "5D %", "Close",
                         "Fwd P/E", "Mkt Cap"
                     ],
                     tablefmt="pipe") + "\n\n"

  # 3. Top 15 Winners & Top 15 Losers (clean equities/ETFs only)
  eq_df = _filter_equity_movers(res_df)

  blob += "#### Top 15 Winners\n"
  for _, row in eq_df.head(15).iterrows():
    blob += (
        f"- {row['Ticker']}: {row['Return_Pct']:+.2f}% "
        f"(Start: ${row['Start_Price']:.2f}, Close: ${row['End_Price']:.2f}, "
        f"High: ${row['High']:.2f})\n")

  blob += "\n#### Top 15 Losers\n"
  losers_df = eq_df.sort_values("Return_Pct", ascending=True).head(15)
  for _, row in losers_df.iterrows():
    blob += (
        f"- {row['Ticker']}: {row['Return_Pct']:+.2f}% "
        f"(Start: ${row['Start_Price']:.2f}, Close: ${row['End_Price']:.2f}, "
        f"Low: ${row['Low']:.2f})\n")

  # 4. Macro, Shipping & Political Snapshot
  macro_snap = _build_macro_political_snapshot(market_data_dir, end_date)
  if macro_snap:
    blob += f"\n#### Macro, Shipping & Prediction Market Pulse\n{macro_snap}\n"

  # 5. Full Ticker Lookup Table
  blob += "\n### FULL TICKER LOOKUP TABLE\n"
  display_df = res_df[["Ticker", "Return_Pct", "Start_Price",
                       "End_Price"]].copy()
  display_df["Return_Pct"] = display_df["Return_Pct"].map(
      lambda x: f"{x:+.2f}%")
  display_df["Start_Price"] = display_df["Start_Price"].map(
      lambda x: f"${x:.2f}")
  display_df["End_Price"] = display_df["End_Price"].map(lambda x: f"${x:.2f}")
  blob += tabulate(display_df.values.tolist(),
                   headers=["Ticker", "Return %", "Start", "End"],
                   tablefmt="pipe") + "\n"
  return blob


def build_prompt_quant_brief(market_data_dir: str,
                             start_date: Optional[datetime],
                             end_date: Optional[datetime]) -> str:
  """Builds a compact (~1.8KB) ground-truth data block injected into prompts."""
  res_df = _compute_price_records(market_data_dir, start_date, end_date)
  if res_df.empty:
    return ""

  by_ticker = {r["Ticker"]: r for _, r in res_df.iterrows()}
  spy_ret = by_ticker["SPY"]["Return_Pct"] if "SPY" in by_ticker else 0.0
  as_of = str(res_df["As_Of"].max())

  bench_parts = [
      f"{b} {by_ticker[b]['Return_Pct']:+.2f}% (${by_ticker[b]['End_Price']:.2f})"
      for b in REGIME_BENCHMARKS
      if b in by_ticker
  ]
  watch_parts = [
      f"{w} {by_ticker[w]['Return_Pct']:+.2f}% "
      f"(vs SPY {by_ticker[w]['Return_Pct'] - spy_ret:+.2f}pp, "
      f"${by_ticker[w]['End_Price']:.2f})"
      for w in PRIORITY_WATCHLIST
      if w in by_ticker
  ]
  eq_df = _filter_equity_movers(res_df)
  win_parts = [
      f"{r['Ticker']} {r['Return_Pct']:+.2f}% (${r['End_Price']:.2f})"
      for _, r in eq_df.head(10).iterrows()
  ]
  lose_parts = [
      f"{r['Ticker']} {r['Return_Pct']:+.2f}% (${r['End_Price']:.2f})" for _, r
      in eq_df.sort_values("Return_Pct", ascending=True).head(10).iterrows()
  ]

  lines = [
      f"\nAUTHORITATIVE QUANTITATIVE SNAPSHOT (As of {as_of} — exact exchange "
      "closes from market_data; use these exact numbers, NEVER write 'n/a'):",
      "Benchmarks: " + " | ".join(bench_parts),
      "Priority Watchlist: " + " | ".join(watch_parts),
      "Top 10 Winners: " + " | ".join(win_parts),
      "Top 10 Losers: " + " | ".join(lose_parts),
  ]
  macro_snap = _build_macro_political_snapshot(market_data_dir, end_date)
  if macro_snap:
    lines.append(macro_snap)
  return "\n".join(lines) + "\n"


async def list_notebooklm_projects(filter_keyword: Optional[str] = None):
  """Lists NotebookLM projects and their sources, optionally filtering by project name."""
  logger.info("Connecting to NotebookLM to list projects...")
  try:
    async with MarketNewsClient(
        project_name="Market Pipeline: Daily Data") as db:
      if not db.client:
        raise ValueError("Client instantiation failed.")
      notebooks = await db.client.notebooks.list()

      print("\n=== NotebookLM Projects Overview ===")
      count = 0
      for nb in notebooks:
        if filter_keyword and filter_keyword.lower() not in nb.title.lower():
          continue
        count += 1
        sources = await db.client.sources.list(nb.id)
        print(f"\nProject Name: {nb.title}")
        print(f"Project ID:   {nb.id}")
        print(f"Source Count: {len(sources)}")
        if sources:
          print("Sources:")
          for src in sources:
            print(f"  - [{src.id}] {src.title}")
        print("-" * 50)

      print(f"\nTotal Exported Projects: {count}\n")

  except Exception as e:
    logger.error(f"Failed to list projects: {e}")


async def list_notebooklm_sources(target_project: str):
  """Prints a list of all uploaded sources for a specific project."""
  logging.basicConfig(level=logging.INFO)
  try:
    async with MarketNewsClient(project_name=target_project) as db:
      await db.connect()
      if not db.notebook_id:
        logger.error(f"Could not connect to or find project: {target_project}")
        return

      if db.client and hasattr(db.client, 'sources'):
        sources = await db.client.sources.list(db.notebook_id)
        if hasattr(sources, '__iter__'):
          source_list = list(sources)
          logger.info(f"\n{'='*50}\nProject: {target_project}\n{'='*50}")
          logger.info(f"Total Sources Found: {len(source_list)}\n")
          for idx, src in enumerate(source_list):
            title = getattr(src, 'title', 'Untitled Source')
            id_val = getattr(src, 'id', 'Unknown ID')
            logger.info(f"{idx+1}. {title} (ID: {id_val})")
        else:
          logger.error(
              f"Invalid sources structure returned for {target_project}")
      else:
        logger.error("Client or sources not available.")
  except Exception as e:
    logger.error(f"Error checking project {target_project}: {e}")


def _sha256(path: str) -> str:
  h = hashlib.sha256()
  with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
      h.update(chunk)
  return h.hexdigest()


def _manifest_path(project_name: str) -> str:
  safe = re.sub(r"[^a-z0-9]+", "_", project_name.lower()).strip("_")
  return os.path.join(
      os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs",
      f".notebooklm_manifest_{safe}.json")


async def upload_directory_to_notebooklm(dir_path: str,
                                         project_name: str = "Market Reports",
                                         limit: int = 40):
  """Syncs rendered PDFs to a NotebookLM project, uploading only deltas.

  A sha256 manifest (``logs/.notebooklm_manifest_<project>.json``) records
  what was last uploaded. Unchanged files are skipped with no RPCs; files
  whose content changed (e.g. a regenerated report) replace the existing
  source of the same title; duplicate titles are collapsed; pruning runs
  once before the batch instead of before every upload.

  Args:
    dir_path (str): Directory containing PDFs (searched recursively).
    project_name (str): Target NotebookLM notebook title.
    limit (int): Structural + newest calendar PDFs considered for sync.
  """
  if not os.path.exists(dir_path):
    logger.error("Directory not found: %s", dir_path)
    return

  manifest_file = _manifest_path(project_name)
  manifest: Dict[str, str] = {}
  if os.path.exists(manifest_file):
    try:
      with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    except (OSError, ValueError):
      manifest = {}

  pinned_tags = (
      "MONTHLY_REPORT",
      "YEARLY_REPORT",
      "PROSPECTIVE_REPORT",
      "MACRO_REPORT",
      "POLITICAL_REPORT",
      "SHIPPING_REPORT",
      "PORTFOLIO_REPORT",
  )
  pdf_files = []
  for root, _, files in os.walk(dir_path):
    for file in files:
      if file.endswith(".pdf"):
        path = os.path.join(root, file)
        is_pinned = 1 if any(t in file for t in pinned_tags) else 0
        t_dt = title_date(file)
        dt_ord = t_dt.toordinal() if t_dt else 0
        pdf_files.append(
            (path, file, (is_pinned, dt_ord, os.path.getmtime(path))))
  pdf_files.sort(key=lambda x: x[2], reverse=True)
  latest = pdf_files[:limit]

  to_upload = [(p, f) for p, f, _ in latest if manifest.get(f) != _sha256(p)]
  if not to_upload:
    logger.info("sync-reports: all %d recent PDFs unchanged; nothing to do.",
                len(latest))
    return

  logger.info("Connecting to NotebookLM '%s' project...", project_name)
  async with MarketNewsClient(project_name=project_name) as db:
    await db.connect()
    if not (db.client and hasattr(db.client, "sources")):
      logger.error("NotebookLM sources API unavailable.")
      return

    existing = await db.client.sources.list(db.notebook_id)
    by_title: Dict[str, List[Any]] = {}
    for src in existing:
      title = getattr(src, "title", "")
      if title:
        by_title.setdefault(title, []).append(src)

    # 1. Collapse duplicate titles (keep one).
    dup_ids = [s.id for srcs in by_title.values() for s in srcs[1:]]
    # 2. Changed files replace their existing source.
    replace_ids = [by_title[f][0].id for _, f in to_upload if f in by_title]
    stale_ids = list(dict.fromkeys(dup_ids + replace_ids))
    if stale_ids:
      logger.info("Deleting %d stale/duplicate sources before upload",
                  len(stale_ids))
      try:
        await db.client.sources.delete_many(db.notebook_id, stale_ids)
      except Exception as e:  # pylint: disable=broad-except
        logger.warning("delete_many failed (%s); falling back", e)
        for sid in stale_ids:
          try:
            await db.client.sources.delete(db.notebook_id, sid)
          except Exception:  # pylint: disable=broad-except
            pass

    # 3. Prune once, leaving headroom for the whole batch.
    await db._prune_sources_if_needed(  # pylint: disable=protected-access
        threshold=max(10, 95 - len(to_upload)))

    # 4. Upload deltas (library caps concurrency at 4).
    sem = asyncio.Semaphore(4)

    async def _one(path: str, name: str) -> None:
      async with sem:
        await db.upload_file(path, prune=False)
        manifest[name] = _sha256(path)
        logger.info("Uploaded %s", name)

    await asyncio.gather(*(_one(p, f) for p, f in to_upload))

  os.makedirs(os.path.dirname(manifest_file), exist_ok=True)
  with open(manifest_file, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=1, sort_keys=True)
  logger.info("sync-reports: uploaded %d, manifest -> %s", len(to_upload),
              manifest_file)


# pylint: disable=too-many-return-statements
async def generate_report(market_data_dir: str,
                          mode: str,
                          start_date_str: Optional[str] = None,
                          end_date_str: Optional[str] = None,
                          dir_path: Optional[str] = None,
                          backfill_news: bool = True):
  """
    Unified entry point for NotebookLM report generation.
    Supports 'daily', 'weekly', 'monthly', 'yearly', 'feed_upload', and 'report_upload' modes.
    """
  urls_to_fetch: List[str] = []

  # State tracking for retrospective sweeps
  sync_file = os.path.join(
      os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs",
      ".notebooklm_last_sync.txt")
  last_sync_date = pd.to_datetime('2000-01-01').tz_localize(
      None)  # Default faraway past
  if mode == 'retrospective' and os.path.exists(sync_file):
    try:
      with open(sync_file, 'r') as f:
        date_str = f.read().strip()
        last_sync_date = pd.to_datetime(date_str).tz_localize(None)
        logger.info(f"Loaded retrospective sync state: {last_sync_date}")
    except Exception as e:
      logger.warning(f"Could not read sync state: {e}")

  if mode == 'report_upload':
    logger.info(f"Uploading rendered PDF reports to NotebookLM Market Reports")
    # Hardcode project name and target directory specifically for this mode
    rendered_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'rendered')
    if not os.path.exists(rendered_dir):
      logger.warning(f"Rendered directory does not exist: {rendered_dir}")
      return
    await upload_directory_to_notebooklm(rendered_dir, "Market Reports")
    return

  if mode == 'upload':
    if not dir_path:
      raise ValueError("Generic upload mode requires a --dir argument.")
    logger.info(f"Uploading directory to NotebookLM: {dir_path}")
    await upload_directory_to_notebooklm(dir_path)
    return

  if mode == 'daily':
    if start_date_str:
      date_obj = pd.to_datetime(start_date_str).tz_localize(None)
      date_m_d = date_obj.strftime("%m-%d")
      full_date_str = date_obj.strftime("%Y-%m-%d")
    else:
      date_obj = pd.Timestamp.now()
      date_m_d = date_obj.strftime("%m-%d")
      full_date_str = date_obj.strftime("%Y-%m-%d")

    project_name = "Market Feed"
    report_filename = f"{date_m_d}_DAILY_REPORT.md"
    prompt = PROMPT_DAILY.format(date=full_date_str)
    feed_title = f"{full_date_str} Daily Market Feed"  # Define feed_title for summary naming
  elif mode == 'weekly':
    if not start_date_str or not end_date_str:
      raise ValueError("Weekly mode requires start_date and end_date.")
    start_date = pd.to_datetime(start_date_str).tz_localize(None)
    end_date = pd.to_datetime(end_date_str).tz_localize(None)
    project_name = "Market Feed"
    report_filename = f"{end_date.strftime('%m-%d')}_WEEKLY_REPORT.md"
    prompt = PROMPT_WEEKLY.format(start_date=start_date_str,
                                  end_date=end_date_str)
  elif mode == 'monthly':
    if not start_date_str or not end_date_str:
      raise ValueError("Monthly mode requires start_date and end_date.")
    start_date = pd.to_datetime(start_date_str).tz_localize(None)
    end_date = pd.to_datetime(end_date_str).tz_localize(None)
    project_name = "Market Feed"
    report_filename = f"{start_date.strftime('%m')}_MONTHLY_REPORT.md"
    prompt = PROMPT_MONTHLY.format(month_year=start_date.strftime('%B %Y'))
  elif mode == 'yearly':
    if not start_date_str or not end_date_str:
      raise ValueError("Yearly mode requires start_date and end_date.")
    start_date = pd.to_datetime(start_date_str).tz_localize(None)
    end_date = pd.to_datetime(end_date_str).tz_localize(None)
    project_name = "Market Feed"
    report_filename = f"{start_date.strftime('%Y')}_YEARLY_REPORT.md"
    prompt = PROMPT_YEARLY.format(year=start_date.strftime('%Y'))
  elif mode == 'yearly_prospective':
    if not start_date_str or not end_date_str:
      raise ValueError(
          "Yearly prospective mode requires start_date and end_date.")
    start_date = pd.to_datetime(start_date_str).tz_localize(None)
    end_date = pd.to_datetime(end_date_str).tz_localize(None)
    project_name = "Market Feed"
    report_filename = f"{start_date.strftime('%Y')}_PROSPECTIVE_REPORT.md"
    prompt = PROMPT_YEARLY_PROSPECTIVE.format(year=start_date.strftime('%Y'))
  elif mode == 'portfolio':
    if not dir_path or not os.path.exists(dir_path):
      raise ValueError(
          "Portfolio mode requires a valid --dir pointing to the markdown report."
      )
    project_name = "Market Pipeline: Portfolio Synthesis"
    report_filename = os.path.basename(dir_path)
    prompt = PROMPT_PORTFOLIO
  elif mode == 'earnings':
    if not dir_path or not os.path.exists(dir_path):
      raise ValueError(
          "Earnings mode requires a valid --dir pointing to the markdown report."
      )
    project_name = "Market Pipeline: Earnings Synthesis"
    report_filename = os.path.basename(dir_path)
    prompt = PROMPT_EARNINGS
  elif mode == 'feed_upload':
    project_name = "Market Feed"
    report_filename = None  # No direct prompt/file output, just archiving raw data
    prompt = None
  elif mode == 'check_auth':
    project_name = "Market Reports"
    report_filename = None
    prompt = None
  else:
    raise ValueError(f"Unknown mode: {mode}")

  logger.info(
      f"Initializing NotebookLM Client: Mode={mode}, Project={project_name}")

  try:
    async with MarketNewsClient(project_name=project_name) as db:
      await db.connect()

      if mode == 'check_auth':
        logger.info("✅ NotebookLM Auth Valid")
        return

      # Clear sources only for one-off temp projects to ensure freshness
      if mode in ['portfolio', 'earnings']:
        await db.clear_sources()

      # Gather TSVs
      full_texts = []

      # Processing Logic
      if mode in ['portfolio', 'earnings']:
        if dir_path:
          # For portfolio mode, just upload the exact markdown tabular document we are targeting
          with open(dir_path, 'r') as f:
            await db.upload_news_text(
                f.read(), title=f"Raw {mode.capitalize()} Data Tables")
      elif mode in ['feed_upload', 'daily']:
        target_date_obj = pd.to_datetime(start_date_str).tz_localize(
            None) if start_date_str else datetime.now()
        feed_title = f"{target_date_obj.strftime('%Y-%m-%d')} Daily Market Feed"

        # Check if the feed already exists in the notebook
        feed_exists = False
        if db.client and hasattr(db.client, 'sources'):
          logger.info("Checking if '%s' is already in Market Feed...",
                      feed_title)
          existing_sources = await db.client.sources.list(db.notebook_id)
          for src in existing_sources:
            if matches_source_title(getattr(src, 'title', ''), feed_title):
              logger.info("Source '%s' already exists.", feed_title)
              feed_exists = True
              break

        if not feed_exists:
          from reports.report_utils import build_daily_news_digest
          text_blob, combined_df = build_daily_news_digest(
              market_data_dir,
              target_date=target_date_obj,
              backfill_news=backfill_news)

          if not text_blob or combined_df.empty:
            logger.warning(
                f"No recent news found for {target_date_obj.strftime('%Y-%m-%d')}."
            )
          else:
            urls_to_fetch = []
            if 'URL' in combined_df.columns:
              # Sort to get the most relevant
              if 'Sentiment' in combined_df.columns:
                top_df = combined_df.sort_values(by='Sentiment',
                                                 ascending=False)
              else:
                top_df = combined_df

              urls_to_fetch = [
                  str(row.get('URL', '')).strip()
                  for _, row in top_df.iterrows()
                  if str(row.get('URL', '')).strip().startswith('http')
              ][:15]

            # Deep Fetch (Concurrent)
            logger.info(
                f"Scraping deep context for {len(urls_to_fetch)} URLs concurrently..."
            )
            tasks = [
                MarketFetcher.fetch_article_text(url, max_paragraphs=30)
                for url in urls_to_fetch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for idx, text in enumerate(results):
              if isinstance(text, str) and text and len(text) > 100:
                full_texts.append(
                    f"FULL ARTICLE CONTEXT {idx+1}:\n{text[:3000]}\n")

            feed_quant = build_prompt_quant_brief(market_data_dir,
                                                  target_date_obj,
                                                  target_date_obj)
            final_market_feed_doc = (
                f"# {feed_title}\n{feed_quant}\n{text_blob}\n\n")
            if full_texts:
              final_market_feed_doc += "====== COMBINED DEEP CONTEXT ======\n\n" + "\n\n".join(
                  full_texts)
            if await db.upload_news_text(final_market_feed_doc,
                                         title=feed_title):
              logger.info("✅ Uploaded single aggregated file: %s", feed_title)
            else:
              logger.error("❌ Failed to upload aggregated file: %s", feed_title)

        if mode == 'feed_upload':
          return

      elif mode in ['weekly', 'monthly', 'yearly', 'yearly_prospective']:
        # Ensure strings are not None for type checker
        if not start_date_str or not end_date_str:
          raise ValueError(
              "start_date and end_date cannot be None for periodic reports")
        target_start = pd.to_datetime(start_date_str).tz_localize(None)
        target_end = pd.to_datetime(end_date_str).tz_localize(None)
        feed_title = f"{target_start.strftime('%Y-%m-%d')} to {target_end.strftime('%Y-%m-%d')} Market Synthesis"

        text_blob = None
        if mode == 'yearly_prospective':
          raw_year_file = os.path.join(
              os.path.dirname(os.path.abspath(__file__)), "news",
              f".{target_start.strftime('%Y')}_prospective_raw.md")
        else:
          raw_year_file = os.path.join(
              os.path.dirname(os.path.abspath(__file__)), "news",
              f".{target_start.strftime('%Y')}_raw.md")

        combined_df = None
        if mode in ['yearly', 'yearly_prospective'
                   ] and os.path.exists(raw_year_file):
          logger.info(f"Injecting deep raw context from: {raw_year_file}")
          with open(raw_year_file, "r") as f:
            text_blob = f.read()

          # Also append TSV data if it exists for the year (e.g. 2025+)
          if target_start.year >= 2025:
            from reports.report_utils import build_daily_news_digest
            tsv_blob, combined_df = build_daily_news_digest(
                market_data_dir,
                start_date=target_start,
                target_date=target_end,
                backfill_news=backfill_news)
            if tsv_blob:
              logger.info(
                  "Appending scraped TSV market data to deep history context")
              text_blob += f"\n\n--- ADDITIONAL SCRAPED MARKET DATA ({target_start.year}) ---\n\n{tsv_blob}\n"
        else:
          from reports.report_utils import build_daily_news_digest
          text_blob, combined_df = build_daily_news_digest(
              market_data_dir,
              start_date=target_start,
              target_date=target_end,
              backfill_news=backfill_news)

        if text_blob:
          # Deep Fetching for Periodic Reports
          urls_to_fetch = []
          full_texts = []
          if combined_df is not None and not combined_df.empty and 'URL' in combined_df.columns:
            # Sort to get the most relevant
            if 'Sentiment' in combined_df.columns:
              top_df = combined_df.sort_values(by='Sentiment', ascending=False)
            else:
              top_df = combined_df

            urls_to_fetch = [
                str(row.get('URL', '')).strip()
                for _, row in top_df.iterrows()
                if str(row.get('URL', '')).strip().startswith('http')
            ][:15]

            if urls_to_fetch:
              logger.info(
                  f"Scraping deep context for {len(urls_to_fetch)} top URLs "
                  "concurrently...")
              tasks = [
                  MarketFetcher.fetch_article_text(url, max_paragraphs=30)
                  for url in urls_to_fetch
              ]
              scraped = await asyncio.gather(*tasks, return_exceptions=True)
              for idx, text in enumerate(scraped):
                if isinstance(text, str) and text and len(text) > 100:
                  full_texts.append(
                      f"FULL ARTICLE CONTEXT {idx+1}:\n{text[:3000]}\n")

          period_quant = build_prompt_quant_brief(market_data_dir,
                                                  target_start.to_pydatetime(),
                                                  target_end.to_pydatetime())
          final_market_feed_doc = (
              f"# {feed_title} News Digest\n{period_quant}\n{text_blob}\n\n")
          if full_texts:
            final_market_feed_doc += "====== COMBINED DEEP CONTEXT ======\n\n" + "\n\n".join(
                full_texts)

          if db.client and hasattr(db.client, 'sources'):
            logger.info(
                f"Deduplicating old '{feed_title}' in project '{project_name}'..."
            )
            try:
              sources = await db.client.sources.list(db.notebook_id)
              for src in sources:
                if matches_source_title(getattr(src, 'title', ''), feed_title):
                  logger.info("Deleting old periodic feed source (ID: %s)",
                              src.id)
                  await db.client.sources.delete(db.notebook_id, src.id)
            except Exception as e:
              logger.warning(
                  f"Could not deduplicate old periodic feed source: {e}")
          if await db.upload_news_text(final_market_feed_doc, title=feed_title):
            logger.info("✅ Uploaded bounded news text: %s", feed_title)
          else:
            logger.error("❌ Failed to upload bounded news text: %s", feed_title)

      # Final Prompting
      if prompt:

        # Build and Upload Quantitative summary for periodic reports
        if mode in [
            'daily', 'weekly', 'monthly', 'yearly', 'yearly_prospective'
        ]:
          # Use previously parsed target_start/target_end for weekly/monthly/yearly
          # Or parse anew if daily
          ts = pd.to_datetime(start_date_str).tz_localize(
              None).to_pydatetime() if start_date_str else None
          te = pd.to_datetime(end_date_str).tz_localize(
              None).to_pydatetime() if end_date_str else None

          if mode == 'daily':
            # For daily, we want 1-day return (comparison to previous close)
            if te is None:
              te = ts if ts is not None else datetime.now()
            ts = te  # Single day; build_price_analysis_blob looks back 1 row

          quant_summary = build_price_analysis_blob(market_data_dir, ts, te)
          quant_brief = build_prompt_quant_brief(market_data_dir, ts, te)
          if quant_brief:
            prompt = f"{prompt}\n{quant_brief}"

          # Deduplicate Quantitative Summary
          summary_title = f"{feed_title} - Quantitative Price Action Summary" if 'feed_title' in locals(
          ) else f"Quantitative Price Action Summary {datetime.now().strftime('%Y-%m-%d')}"

          if db.client and hasattr(db.client, 'sources'):
            logger.info(
                f"Deduplicating old '{summary_title}' in project '{project_name}'..."
            )
            try:
              sources = await db.client.sources.list(db.notebook_id)
              for src in sources:
                if matches_source_title(getattr(src, 'title', ''),
                                        summary_title):
                  logger.info("Deleting old summary (ID: %s)", src.id)
                  await db.client.sources.delete(db.notebook_id, src.id)
            except Exception as e:
              logger.warning(f"Could not deduplicate old summaries: {e}")

          if quant_summary:
            await db.upload_news_text(quant_summary, title=summary_title)

          # Inject recent historical reports to provide longitudinal context
          historical_context = ""

          if mode in ['weekly', 'monthly', 'yearly', 'yearly_prospective']:
            logger.info(
                f"Scanning for {mode} recursive sub-reports to inject as context..."
            )
            reports_dir = os.path.dirname(os.path.abspath(__file__))
            news_reports_dir = os.path.join(reports_dir, 'news')

            # Read from reports/news if it exists, otherwise fallback to reports root during transition
            scan_dirs = [news_reports_dir, reports_dir]
            recent_reports = []

            for scan_dir in scan_dirs:
              if not os.path.exists(scan_dir):
                continue
              for report_file in os.listdir(scan_dir):
                if report_file.endswith(
                    ".md") and report_file != "PORTFOLIO_REPORT.md":
                  filepath = os.path.join(scan_dir, report_file)
                  if os.path.isfile(filepath):
                    # For recursive injection, we check if the file falls within our bounds based on name or timeframe
                    # A naive approach: just inject files whose timestamp falls into the window
                    mtime_dt = datetime.fromtimestamp(
                        os.path.getmtime(filepath))

                    if target_start and target_end:
                      if target_start <= mtime_dt <= target_end:
                        recent_reports.append((filepath, report_file))
                      elif "DAILY" in report_file and mode == "weekly":
                        date_str = report_file.split("_")[0]  # MM-DD
                        year = target_start.year
                        try:
                          report_dt = datetime.strptime(f"{year}-{date_str}",
                                                        "%Y-%m-%d")
                          if target_start <= report_dt <= target_end:
                            recent_reports.append((filepath, report_file))
                        except:
                          pass
                      elif "WEEKLY" in report_file and mode == "monthly":
                        date_str = report_file.split("_")[0]  # MM-DD
                        year = target_start.year
                        try:
                          report_dt = datetime.strptime(f"{year}-{date_str}",
                                                        "%Y-%m-%d")
                          if target_start <= report_dt <= target_end:
                            recent_reports.append((filepath, report_file))
                        except:
                          pass
                      elif mode in ['yearly', 'yearly_prospective'
                                   ] and ("MONTHLY" in report_file or
                                          "WEEKLY" in report_file):
                        # Simple naive check: if the file contains the year or was modified in the year
                        if target_start.strftime(
                            "%Y"
                        ) in report_file or mtime_dt.year == target_start.year:
                          recent_reports.append((filepath, report_file))

            # Deduplicate just to be safe
            unique_reports = []
            seen_files = set()
            for rp in recent_reports:
              if rp[1] not in seen_files:
                seen_files.add(rp[1])
                unique_reports.append(rp)
            recent_reports = unique_reports

          else:
            logger.info(
                "Scanning for recent historical reports to inject as context..."
            )
            reports_dir = os.path.dirname(os.path.abspath(__file__))
            news_reports_dir = os.path.join(reports_dir, 'news')
            recent_reports = []

            scan_dirs = [news_reports_dir, reports_dir]
            for scan_dir in scan_dirs:
              if not os.path.exists(scan_dir):
                continue
              for report_file in os.listdir(scan_dir):
                if report_file.endswith(
                    ".md") and report_file != "PORTFOLIO_REPORT.md":
                  filepath = os.path.join(scan_dir, report_file)
                  if os.path.isfile(filepath):
                    match = re.match(r"(\d{2}-\d{2})_", report_file)
                    if match:
                      file_date_str = match.group(1)
                      try:
                        target_year = te.year if te else datetime.now().year
                        file_date = datetime.strptime(
                            f"{target_year}-{file_date_str}", "%Y-%m-%d")
                        ref_date = te if te else datetime.now()
                        if file_date < ref_date and (ref_date -
                                                     file_date).days <= 7:
                          recent_reports.append((filepath, report_file))
                      except ValueError:
                        pass

          # Deduplicate before uploading
          if recent_reports:
            history_title = "Historical Context: Recent Periodic Reports"
            if db.client and hasattr(db.client, 'sources'):
              logger.info(
                  f"Deduplicating '{history_title}' in project '{project_name}'..."
              )
              try:
                sources = await db.client.sources.list(db.notebook_id)
                for src in sources:
                  if matches_source_title(getattr(src, 'title', ''),
                                          history_title):
                    await db.client.sources.delete(db.notebook_id, src.id)
              except Exception as e:
                logger.warning(f"Could not deduplicate historical context: {e}")

            for filepath, report_file in recent_reports:
              with open(filepath, 'r') as f:
                body = f.read()
              if looks_like_studio_stub(body):
                logger.warning("Skipping stub report in context: %s",
                               report_file)
                continue
              historical_context += (
                  f"\n\n--- Content from {report_file} ---\n\n{body}")

            if historical_context:
              await db.upload_news_text(historical_context, title=history_title)

        # Scope retrieval to this period's sources (+ a few recent feeds for
        # continuity). Querying all ~95 sources through a 200-turn
        # conversation took ~5 min per report and produced Studio stubs.
        scoped_ids: List[str] = []
        required_markers: Optional[List[str]] = None
        if mode in [
            'daily', 'weekly', 'monthly', 'yearly', 'yearly_prospective'
        ]:
          wanted_titles = [
              feed_title, f"{feed_title} - Quantitative Price Action Summary",
              "Historical Context: Recent Periodic Reports"
          ]
          await asyncio.sleep(3)
          scoped_ids = await db.find_source_ids(wanted_titles)
          if mode == 'weekly':
            for sid in await db.recent_feed_source_ids(days=3):
              if sid not in scoped_ids:
                scoped_ids.append(sid)
          required_markers = ["## References"]
          if mode in ['daily', 'weekly']:
            required_markers.append("## Top AI Thematic Insights")

        logger.info("Requesting LLM Synthesis for %s (%d scoped sources)...",
                    mode, len(scoped_ids))
        report_content = await db.synthesize_report(
            prompt,
            source_ids=scoped_ids or None,
            required_markers=required_markers)
        if not report_content or len(report_content.strip()) < 200:
          raise RuntimeError(
              f"Empty or stub synthesis returned for {mode} "
              f"({report_filename}); refusing to write empty report file.")

        if mode in ['portfolio', 'earnings'] and dir_path:
          output_path: str = dir_path
        else:
          # Daily / Periodic Report output routing
          reports_dir = os.path.dirname(os.path.abspath(__file__))

          if mode in [
              'daily', 'weekly', 'monthly', 'yearly', 'yearly_prospective'
          ]:
            news_dir = os.path.join(reports_dir, 'news')
            os.makedirs(news_dir, exist_ok=True)
            output_path = os.path.join(news_dir, report_filename or "report.md")
          else:
            output_path = os.path.join(reports_dir, report_filename or
                                       "report.md")

        # For portfolios: prepend the AI summary to the existing file
        if mode in ['portfolio', 'earnings']:
          with open(output_path, 'r') as f:
            original_content = f.read()
          with open(output_path, "w") as f:
            new_content = (
                f"{original_content}\n\n---\n\n# AI Tactical Summary\n"
                f"> **[View Primary Active Reports Archive directly in NotebookLM](https://notebooklm.google.com/notebook/8bc24a30-b417-4a6e-acdf-1b5588c04bae)**\n\n"
                f"{report_content}")
            f.write(clean_md(new_content))
        else:
          # Write the generated report content directly
          raw_content = (
              f"# Market Intelligence Report\n*(Generated via NotebookLM "
              f"Integration on {datetime.now().strftime('%Y-%m-%d')})*\n"
              f"> **[View Primary Active Reports Archive directly in "
              f"NotebookLM](https://notebooklm.google.com/notebook/8bc24a30-b417-4a6e-acdf-1b5588c04bae)**\n\n"
              + report_content)
          with open(output_path, "w") as f:
            f.write(clean_md(raw_content))

        # Automatically compile the Markdown into a PDF with embedded charts
        from reports.report_utils import render_markdown_to_pdf
        pdf_path = render_markdown_to_pdf(output_path)

        logger.info(f"✅ Saved MD report to {output_path}")
        logger.info(f"✅ Rendered PDF report to {pdf_path}")
        logger.info(f"✅ Ready for bulk upload later.")

        # Clean up ONLY for portfolio and earnings (since they use temp projects)
        if mode in ['portfolio', 'earnings']:
          logger.info(f"Wiping temporary NotebookLM project: {project_name}...")
          await db.delete_project()

      elif mode == 'feed_upload':
        # Safely write the sync state after a successful run
        try:
          os.makedirs(os.path.dirname(sync_file), exist_ok=True)
          with open(sync_file, 'w') as f:
            f.write(datetime.now().isoformat())
        except Exception as e:
          logger.warning(f"Could not save sync state: {e}")
        logger.info("✅ Feed sync complete.")

  except NotebookLMQuotaError:
    raise
  except Exception as e:
    logger.error(f"Failed to run via NotebookLM: {e}")

    # Try to safely clean up any stranded projects during a crash
    if mode in ['portfolio', 'earnings'] and 'db' in locals():
      try:
        logger.info(
            f"Attempting to wipe crashed NotebookLM project: {project_name}...")
        await db.delete_project()
      except:
        pass

    if "login" in str(e).lower() or "authentication" in str(e).lower():
      logger.error(
          "Please run `notebooklm login` from your terminal to authenticate.")
    sys.exit(1)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="NotebookLM Report Generator")
  parser.add_argument("--mode",
                      choices=[
                          'daily', 'weekly', 'monthly', 'yearly',
                          'yearly_prospective', 'feed_upload', 'report_upload',
                          'upload', 'list', 'list_sources', 'portfolio',
                          'earnings', 'check_auth'
                      ],
                      required=True,
                      help="Type of operation or 'list' to view projects")
  parser.add_argument(
      "--start", help="Start date (YYYY-MM-DD) for weekly/monthly/yearly mode")
  parser.add_argument(
      "--end", help="End date (YYYY-MM-DD) for weekly/monthly/yearly mode")
  parser.add_argument("--dir",
                      help="Directory path to upload for 'upload' mode")
  parser.add_argument("--filter-projects",
                      help="Keyword to filter projects in 'list' mode")
  parser.add_argument("--project",
                      default="Market Reports",
                      help="Target project name for 'list_sources' mode")

  args = parser.parse_args()

  if args.mode == 'list':
    asyncio.run(list_notebooklm_projects(args.filter_projects))
  elif args.mode == 'list_sources':
    asyncio.run(list_notebooklm_sources(args.project))
  else:
    root_market_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'market_data')
    asyncio.run(
        generate_report(root_market_data_dir, args.mode, args.start, args.end,
                        args.dir))
