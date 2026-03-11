# pylint: disable=duplicate-code
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.append(PROJECT_ROOT)
MARKET_DATA_DIR = os.path.join(PROJECT_ROOT, "market_data")

from reports.report_utils import analyze_earnings_movement
from reports.report_utils import format_num

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
MARKET_DATA_DIR = os.path.join(PROJECT_ROOT, "market_data")


def generate_orcl_fade_plot(orcl_df):
  if orcl_df is None or orcl_df.empty:
    return
  df = orcl_df.tail(12)
  plt.figure(figsize=(10, 6))
  sns.set_theme(style="whitegrid")
  plot_df = df.dropna(
      subset=['Open_Change_Pct', 'High_Change_Pct', 'Close_Change_Pct'])

  dates = plot_df['Earnings_Date'].astype(str).tolist()
  plt.plot(dates,
           plot_df['Open_Change_Pct'],
           marker='o',
           label='Open (Gap Up/Down)',
           color='green',
           linewidth=2)
  plt.plot(dates,
           plot_df['High_Change_Pct'],
           marker='^',
           label='Peak (Intraday High)',
           color='orange',
           linestyle='--',
           linewidth=2)
  plt.plot(dates,
           plot_df['Close_Change_Pct'],
           marker='s',
           label='Close (The Fade)',
           color='red',
           linewidth=2)

  plt.title("ORCL Post-Earnings Price Action (T+1): Intraday Fade",
            fontsize=14,
            fontweight='bold')
  plt.ylabel("Percentage Change from T0 Close (%)", fontsize=12)
  plt.xlabel("Earnings Date", fontsize=12)
  plt.xticks(rotation=45)
  plt.axhline(0, color='black', linewidth=1, linestyle='-')
  plt.legend(loc="upper left")
  plt.tight_layout()

  plots_dir = os.path.join(os.path.dirname(__file__), "plots")
  os.makedirs(plots_dir, exist_ok=True)
  output_path = os.path.join(plots_dir, "orcl_fade_pattern.png")
  plt.savefig(output_path, dpi=300)
  plt.close()


def generate_orcl_surprise_scatter_plot(orcl_df):
  if orcl_df is None or orcl_df.empty:
    return
  df = orcl_df.tail(12)
  df['Year'] = pd.to_datetime(df['Earnings_Date']).dt.year
  df = df[df['Year'] >= 2022]

  plt.figure(figsize=(10, 6))
  sns.set_theme(style="whitegrid")
  plot_df = df.dropna(subset=['Surprise_Pct', 'Close_Change_Pct'])

  sns.scatterplot(x='Surprise_Pct',
                  y='Close_Change_Pct',
                  data=plot_df,
                  s=150,
                  color='purple',
                  alpha=0.8)

  sns.regplot(x='Surprise_Pct',
              y='Close_Change_Pct',
              data=plot_df,
              scatter=False,
              color='gray',
              line_kws={"linestyle": "--"},
              seed=42)
  plt.title("ORCL EPS Surprise vs. Post-Earnings Close (T+1)",
            fontsize=14,
            fontweight='bold')
  plt.ylabel("Close Percentage Change (%)", fontsize=12)
  plt.xlabel("EPS Surprise (%)", fontsize=12)
  plt.axhline(0, color='black', linewidth=1, linestyle='-')

  for i, row in plot_df.iterrows():
    date_str = str(row['Earnings_Date'])
    plt.annotate(date_str, (row['Surprise_Pct'], row['Close_Change_Pct']),
                 textcoords="offset points",
                 xytext=(0, 10),
                 ha='center',
                 fontsize=8,
                 color='k')

  plt.tight_layout()

  plots_dir = os.path.join(os.path.dirname(__file__), "plots")
  os.makedirs(plots_dir, exist_ok=True)
  output_path = os.path.join(plots_dir, "orcl_surprise_scatter.png")
  plt.savefig(output_path, dpi=300)
  plt.close()


def calculate_iv_crush_metrics(orcl_df):
  """Calculates the options premium decay from Intraday Peak to Final Close."""
  if orcl_df is None or orcl_df.empty:
    return pd.DataFrame()

  recent = orcl_df.tail(12)
  results = []

  for _, row in recent.iterrows():
    edate = row['Earnings_Date']
    peak = row['High_Change_Pct']
    close = row['Close_Change_Pct']

    # Premium decay is the percentage points lost from the absolute peak to the close
    decay = close - peak

    results.append({
        'Earnings Date': edate,
        'Intraday Peak (High)': format_num(peak, is_pct=True, is_signed=True),
        'T+1 Final Close': format_num(close, is_pct=True, is_signed=True),
        'Premium Decay (Crush)': format_num(decay, is_pct=True, is_signed=True)
    })

  return pd.DataFrame(results)


def generate_orcl_iv_crush_plot(iv_df):
  if iv_df is None or iv_df.empty:
    return
  plt.figure(figsize=(10, 6))
  sns.set_theme(style="whitegrid")
  df = iv_df.copy()
  # Drop TBD rows before plotting
  df = df[df['Premium Decay (Crush)'] != 'TBD']
  df['Decay'] = df['Premium Decay (Crush)'].str.replace('%', '').astype(float)
  sns.barplot(x='Earnings Date', y='Decay', data=df, color='crimson')
  plt.axhline(0, color='black', linewidth=1)
  plt.title("ORCL Implied Volatility (IV) Crush Decay",
            fontsize=14,
            fontweight='bold')
  plt.ylabel("Premium Decay from Peak to Close (%)", fontsize=12)
  plt.xticks(rotation=45)
  plt.tight_layout()
  plots_dir = os.path.join(os.path.dirname(__file__), "plots")
  os.makedirs(plots_dir, exist_ok=True)
  out_path = os.path.join(plots_dir, "orcl_iv_crush.png")
  plt.savefig(out_path, dpi=300)
  plt.close()


def generate_intraday_ground_truth_plot():
  try:
    import yfinance as yf

    # Fetch 5-minute interval data for Mar 9 and Mar 10
    df = yf.download("ORCL",
                     start="2026-03-09",
                     end="2026-03-11",
                     interval="5m",
                     prepost=True)
    if df.empty:
      return

    if isinstance(df.columns, pd.MultiIndex):
      df.columns = df.columns.get_level_values(0)

    plt.figure(figsize=(12, 6))
    sns.set_theme(style="darkgrid")

    if df.index.tz is None:
      df.index = df.index.tz_localize('UTC').tz_convert('US/Eastern')
    else:
      df.index = df.index.tz_convert('US/Eastern')

    close_series = df['Close'].squeeze()
    plt.plot(df.index, close_series, color='black', linewidth=1.5)

    earnings_time = pd.to_datetime('2026-03-09 16:20:00').tz_localize(
        'US/Eastern')
    plt.axvline(x=earnings_time,
                color='red',
                linestyle='--',
                linewidth=2,
                label='Q3 Earnings Print')

    t0_close_time = pd.to_datetime('2026-03-09 16:00:00').tz_localize(
        'US/Eastern')
    t1_open_time = pd.to_datetime('2026-03-10 09:30:00').tz_localize(
        'US/Eastern')
    t1_close_time = pd.to_datetime('2026-03-10 16:00:00').tz_localize(
        'US/Eastern')

    def annotate_price(t_time, label, color):
      if t_time in df.index:
        price = close_series.loc[t_time]
      else:
        # Find nearest
        if len(df.index) > 0:
          idx = df.index.get_indexer([t_time], method='nearest')[0]
          if idx >= 0:
            price = close_series.iloc[idx]
            t_time = df.index[idx]
            plt.scatter(t_time, price, color=color, s=100, zorder=5)
            plt.annotate(f"{label}\n${price:.2f}", (t_time, price),
                         textcoords="offset points",
                         xytext=(0, 10),
                         ha='center',
                         fontsize=9,
                         fontweight='bold',
                         color=color)

    annotate_price(t0_close_time, 'T0 Close', 'blue')
    annotate_price(t1_open_time, 'T1 Open', 'orange')
    annotate_price(t1_close_time, 'T1 Close', 'purple')

    plt.title("ORCL Ground Truth Intraday Trajectory (Mar 9 - Mar 10)",
              fontsize=14,
              fontweight='bold')
    plt.ylabel("Price ($)", fontsize=12)
    plt.xlabel("Time (EST)", fontsize=12)
    plt.legend(loc='upper right')
    plt.tight_layout()

    plots_dir = os.path.join(os.path.dirname(__file__), "plots")
    os.makedirs(plots_dir, exist_ok=True)
    out_path = os.path.join(plots_dir, "orcl_intraday_ground_truth.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
  except Exception as e:
    print(f"Failed to generate intraday plot: {e}")


def generate_trajectory_prediction_plot():
  try:
    import yfinance as yf

    t0 = pd.to_datetime('2026-03-09 16:00:00').tz_localize('US/Eastern')
    t_now = pd.Timestamp.now(tz='US/Eastern')
    t_end = pd.to_datetime('2026-03-13 16:00:00').tz_localize('US/Eastern')

    print("Generating Trajectory Prediction Plot...")

    # Start with standard hypothetical starting price based on T0 Close
    t0_price = 143.00  # Approximated T0 Close for projection baseline if yf fails
    last_price = 143.00
    last_time = t0

    df = yf.download("ORCL",
                     start="2026-03-09",
                     end="2026-03-14",
                     interval="5m",
                     prepost=True)

    plt.figure(figsize=(12, 7))
    sns.set_theme(style="whitegrid")

    if not df.empty:
      if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
      if df.index.tz is None:
        df.index = df.index.tz_localize('UTC').tz_convert('US/Eastern')
      else:
        df.index = df.index.tz_convert('US/Eastern')

      close_series = df['Close'].squeeze()

      # Plot actual history since T0
      history = close_series[close_series.index >= t0]
      if not history.empty:
        plt.plot(history.index,
                 history.values,
                 color='black',
                 linewidth=2.5,
                 label='Actual 5m Realtime Trend')
        last_price = history.iloc[-1]
        last_time = history.index[-1]

      if len(df.index) > 0:
        idx = df.index.get_indexer([t0], method='nearest')[0]
        if idx >= 0:
          t0_price = close_series.iloc[idx]

    # Create future projection space from the last known point
    future_times = pd.date_range(start=last_time, end=t_end, freq='1h')
    if len(future_times) == 0:
      future_times = [last_time]

    steps = len(future_times)
    np.random.seed(42)  # For reproducible random walk visually

    # Base variance cone that expands over time
    std_dev_base = np.linspace(0, last_price * 0.05,
                               steps)  # 5% variance by end

    # Scenario 1 (Green): AI Acceleration - drift up to +6% from current
    drift_1 = np.linspace(last_price, last_price * 1.06, steps)
    path_1 = drift_1 + np.random.normal(0, std_dev_base * 0.15, steps).cumsum()
    plt.plot(future_times,
             path_1,
             label='Scenario 1: AI Acceleration',
             color='green',
             linewidth=2)
    plt.fill_between(future_times,
                     drift_1 - std_dev_base * 0.8,
                     drift_1 + std_dev_base * 0.8,
                     color='green',
                     alpha=0.1)

    # Scenario 2 (Orange): Structural Fade - drift down to -2% from current
    drift_2 = np.linspace(last_price, last_price * 0.98, steps)
    path_2 = drift_2 + np.random.normal(0, std_dev_base * 0.15, steps).cumsum()
    plt.plot(future_times,
             path_2,
             label='Scenario 2: Structural Fade',
             color='orange',
             linestyle='--',
             linewidth=2)
    plt.fill_between(future_times,
                     drift_2 - std_dev_base * 0.9,
                     drift_2 + std_dev_base * 0.9,
                     color='orange',
                     alpha=0.1)

    # Scenario 3 (Red): Siphon Rotation - drift down to -6% from current
    drift_3 = np.linspace(last_price, last_price * 0.94, steps)
    path_3 = drift_3 + np.random.normal(0, std_dev_base * 0.15, steps).cumsum()
    plt.plot(future_times,
             path_3,
             label='Scenario 3: Siphon Rotation',
             color='red',
             linestyle=':',
             linewidth=2)
    plt.fill_between(future_times,
                     drift_3 - std_dev_base * 1.1,
                     drift_3 + std_dev_base * 1.1,
                     color='red',
                     alpha=0.1)

    plt.axhline(t0_price,
                color='blue',
                linewidth=1.5,
                linestyle='-.',
                label='T0 Close Baseline')
    plt.axvline(last_time,
                color='purple',
                linewidth=2,
                linestyle='--',
                label='Current Time')

    # Target Buy Zone Annotation for the Baseline Fade
    plt.axhspan(
        t0_price * 0.94,
        t0_price * 0.96,
        color='gold',
        alpha=0.3,
        label=f'Fade Buy Target (~${t0_price * 0.94:.0f}-${t0_price * 0.96:.0f})'
    )

    plt.title(
        "ORCL Predictive Trajectory Model (With Realtime Trend & Confidence Cones)",
        fontsize=14,
        fontweight='bold')
    plt.ylabel("Projected Value ($)", fontsize=12)
    plt.xlabel("Timeline", fontsize=12)
    plt.xticks(rotation=45)
    plt.legend(loc="upper left")
    plt.tight_layout()

    plots_dir = os.path.join(os.path.dirname(__file__), "plots")
    os.makedirs(plots_dir, exist_ok=True)
    out_path = os.path.join(plots_dir, "orcl_trajectory_prediction.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
  except Exception as e:
    print(f"Failed to generate predictive plot: {e}")


def generate_decision_tree():
  try:
    from graphviz import Digraph

    from reports.report_utils import setup_decision_tree_aesthetics

    print("Generating Decision Tree...")
    dot = Digraph(comment='ORCL 0-Day Trade Decision Tree')
    setup_decision_tree_aesthetics(dot)

    dot.node('A',
             'Current State:\\n0 ORCL Shares\\nEarnings Gap Up',
             fillcolor='lightblue')

    dot.node('B1',
             'Wait for T1 Fade\\n(Buy pre-close Wed/Thu)',
             fillcolor='lightyellow')
    dot.node('B2', 'FOMO Buy Open\\n(High Risk)', fillcolor='lightcoral')

    dot.edge('A', 'B1', label='Base Case (Fade)')
    dot.edge('A', 'B2', label='AI Breakout')

    dot.node('C1',
             'Hold 1-2 Weeks\\nWait for AI rotation',
             fillcolor='lightgray')

    dot.node('D1',
             'Sell for +10% Profit\\nTarget: ~$160+',
             fillcolor='lightgreen')
    dot.node('D2', 'Stop Loss @ -5%\\nIf macro sours', fillcolor='lightcoral')

    dot.edge('B1', 'C1', label='Accumulate')
    dot.edge('C1', 'D1', label='Thesis Intact')
    dot.edge('C1', 'D2', label='Thesis Broken')

    dot.node('C2',
             'Sell immediately on\\nweakness (Quick flip)',
             fillcolor='lightyellow')
    dot.edge('B2', 'C2', label='Momentum fails')

    plots_dir = os.path.join(os.path.dirname(__file__), "plots")
    os.makedirs(plots_dir, exist_ok=True)
    out_path = os.path.join(plots_dir, "orcl_decision_tree")
    dot.render(out_path, format='png', cleanup=True)
  except Exception as e:
    print(f"Failed to generate decision tree: {e}")


def pre_fetch_data():
  try:
    print("Pre-fetching latest market data...")
    from market_fetcher import MarketFetcher
    fetcher = MarketFetcher(cache_dir=os.path.join(MARKET_DATA_DIR, ".cache"))
    tickers = ["ORCL", "MSFT", "AMZN", "NVDA"]

    # 1. Update Prices
    print("Updating prices...")
    fetcher.update_prices(tickers)

    # 2. Update News
    print("Updating news...")
    fetcher.update_news(tickers)
    # Also fetch full historical news premium for deep context
    from datetime import datetime
    from datetime import timedelta
    end_date_str = datetime.now().strftime('%Y-%m-%d')
    start_date_str = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    for ticker in tickers:
      try:
        fetcher.fetch_historical_news_premium(ticker,
                                              start_date=start_date_str,
                                              end_date=end_date_str)
      except Exception as e:
        print(f"Skipping premium news fetch: {e}")

    # 3. Handle Earnings (Conditional to not overwrite manual data if YF fails for 2026)
    orcl_earnings_path = os.path.join(MARKET_DATA_DIR,
                                      "tickers/ORCL/earnings.tsv")
    old_earnings = pd.DataFrame()
    if os.path.exists(orcl_earnings_path):
      old_earnings = pd.read_csv(orcl_earnings_path, sep='\t')

    print("Updating fundamentals (earnings)...")
    fetcher.update_fundamentals(["ORCL"])

    if os.path.exists(orcl_earnings_path):
      new_earnings = pd.read_csv(orcl_earnings_path, sep='\t')
      has_2026 = new_earnings['Earnings Date'].astype(str).str.contains(
          '2026').any()
      if not has_2026 and not old_earnings.empty:
        print(
            "No new 2026 earnings detected from Yahoo. Restoring manual data..."
        )
        old_earnings.to_csv(orcl_earnings_path, sep='\t', index=False)

    print("Pre-fetch complete.")
  except Exception as e:
    print(f"Failed to pre-fetch data: {e}")


def run_full_analysis():
  pre_fetch_data()
  print("Running ORCL Trade Analysis...")
  orcl_df = analyze_earnings_movement("ORCL", MARKET_DATA_DIR)

  report_path = os.path.join(os.path.dirname(__file__), "REPORT.md")
  os.makedirs(os.path.join(os.path.dirname(__file__), "plots"), exist_ok=True)

  # Ensure plots are generated
  if orcl_df is not None:
    generate_orcl_fade_plot(orcl_df)
    generate_orcl_surprise_scatter_plot(orcl_df)
  generate_intraday_ground_truth_plot()
  generate_trajectory_prediction_plot()
  generate_decision_tree()

  md_lines = []

  md_lines.append("# ORCL Q3 Earnings Trade Analysis\n\n")

  md_lines.append("## Executive Summary\n")
  md_lines.append(
      "> Oracle (ORCL) has pivoted aggressively from a legacy database software company to a massive Tier-1 Cloud Infrastructure provider. This report analyzes the recent earnings print and provides predictive scenarios for near-term price action.\n\n"
  )

  md_lines.append("## Intraday Ground Truth & Historical Context\n")
  md_lines.append(
      "Before looking forward, here is the immediate post-earnings price action:\n\n"
  )
  md_lines.append(
      "![ORCL Intraday Trajectory](./plots/orcl_intraday_ground_truth.png)\n\n")

  md_lines.append("## Predictive Scenario Bounds (48H)\n")
  md_lines.append(
      "Based on the technical data and historical fades, we project three viable paths for the next 48 hours:\n\n"
  )
  md_lines.append(
      "![ORCL Predictive Trajectory](./plots/orcl_trajectory_prediction.png)\n\n"
  )
  md_lines.append(
      "*   **Scenario 1: AI Acceleration** - Institutional buyers overwhelm normal fade patterns due to high OCI growth.\n"
  )
  md_lines.append(
      "*   **Scenario 2: Structural Fade** - The stock follows historical norms, fading the initial gap over 2-3 days.\n"
  )
  md_lines.append(
      "*   **Scenario 3: Siphon Rotation** - A broader market rejection pulls capital away from the extended gap.\n\n"
  )

  md_lines.append("## Short-Term Trading Decision Tree\n")
  md_lines.append(
      "For a portfolio currently holding 0 ORCL shares aiming for a short-term swing:\n\n"
  )
  md_lines.append("![ORCL Decision Tree](./plots/orcl_decision_tree.png)\n\n")

  if orcl_df is not None:
    md_lines.append("### Historical Earnings Reactions\n")
    recent = orcl_df.tail(12).copy()
    latest_date_str = recent['Earnings_Date'].astype(str).max()
    if latest_date_str:
      recent.loc[recent['Earnings_Date'].astype(str) == latest_date_str,
                 'Earnings_Date'] = f"{latest_date_str} (Latest Print)"

    cols_to_format = [
        'Surprise_Pct', 'Open_Change_Pct', 'High_Change_Pct', 'Close_Change_Pct'
    ]
    for col in cols_to_format:
      recent[col] = recent[col].map(
          lambda x: format_num(x, is_pct=True, is_signed=True))

    disp_df = recent[[
        'Earnings_Date', 'Surprise_Pct', 'Open_Change_Pct', 'High_Change_Pct',
        'Close_Change_Pct'
    ]]
    md_lines.append(disp_df.to_markdown(index=False) + "\n\n")

    avg_df = recent[~recent['Earnings_Date'].astype(str).str.
                    contains("Latest", na=False)]
    if not avg_df.empty:
      md_lines.append(
          f"*   **Historical Average Gap Up (Open):** `{avg_df['Open_Change_Pct'].str.replace('%', '').astype(float).mean():+.2f}%`\n"
      )
      md_lines.append(
          f"*   **Historical Average Intraday Peak:** `{avg_df['High_Change_Pct'].str.replace('%', '').astype(float).mean():+.2f}%`\n"
      )
      md_lines.append(
          f"*   **Historical Average Close:** `{avg_df['Close_Change_Pct'].str.replace('%', '').astype(float).mean():+.2f}%`\n\n"
      )

    md_lines.append("#### The 'Fade' Pattern\n")
    md_lines.append(
        "Historically, ORCL gaps up but fades through the week. The chart below illustrates the T1 Close relative to the Open/High:\n\n"
    )
    md_lines.append("![ORCL Fade Pattern](./plots/orcl_fade_pattern.png)\n\n")

    md_lines.append("#### EPS Surprise vs. Close\n")
    md_lines.append(
        "The scatter plot below highlights how the market reacts to the magnitude of the EPS surprise:\n\n"
    )
    md_lines.append(
        "![ORCL Surprise Scatter](./plots/orcl_surprise_scatter.png)\n\n")

    # Inject IV Crush Table
    md_lines.append("### Implied Volatility (IV) Crush Metrics\n")
    md_lines.append(
        "*The 'Gap Trap': Tracking options premium decay from the Intraday Peak (FOMO) to the Final Close.*\n\n"
    )
    iv_df = calculate_iv_crush_metrics(orcl_df)
    if not iv_df.empty:
      md_lines.append(iv_df.to_markdown(index=False) + "\n\n")
      generate_orcl_iv_crush_plot(iv_df)

    avg_iv_df = iv_df[~iv_df['Earnings Date'].astype(str).str.
                      contains("Latest", na=False)]
    if not avg_iv_df.empty:
      md_lines.append(
          f"*   **Average Premium Decay per Quarter:** `{avg_iv_df['Premium Decay (Crush)'].str.replace('%', '').astype(float).mean():+.2f}%`\n\n"
      )
      md_lines.append("![ORCL IV Crush](./plots/orcl_iv_crush.png)\n\n")

  try:
    from reports.report_utils import format_recent_news_markdown
    news_md = format_recent_news_markdown(
        topics={},
        market_data_dir=MARKET_DATA_DIR,
        tickers=["ORCL", "MSFT", "AMZN", "NVDA"],
        max_items=15)
    if news_md:
      md_lines.append("## Recent Industry News Context\n")
      md_lines.append(
          "> *Aggregated context to provide NotebookLM with the overarching industry narrative*\n\n"
      )
      md_lines.append(news_md)
      md_lines.append("\n")
  except Exception as e:
    print(f"Failed to append news context: {e}")

  # The AI Tactical Summary section is completely generated by NotebookLM.
  # We just write out the data above. NotebookLM script appends the final analysis to this file.

  with open(report_path, "w") as f:
    f.write("".join(md_lines))
  print(f"Updated {report_path}")


if __name__ == "__main__":
  run_full_analysis()
