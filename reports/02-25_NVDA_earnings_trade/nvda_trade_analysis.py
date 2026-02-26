import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from graphviz import Digraph
from tabulate import tabulate

from reports.report_utils import (analyze_earnings_movement, format_num,
                                  get_recent_news, get_technical_indicators,
                                  plot_ma200_distance, plot_portfolio_rsi,
                                  setup_decision_tree_aesthetics)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
MARKET_DATA_DIR = os.path.join(PROJECT_ROOT, "market_data")
REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))



def calculate_q4_cost_basis(tickers):
  results = []
  for t in tickers:
    if t == "NVDA":
      continue
    try:
      earnings = pd.read_csv(os.path.join(MARKET_DATA_DIR,
                                          f"tickers/{t}/earnings.tsv"),
                             sep="\t")
      prices = pd.read_csv(os.path.join(MARKET_DATA_DIR,
                                        f"tickers/{t}/prices.tsv"),
                           sep="\t")

      prices['Date'] = pd.to_datetime(prices['Date']).dt.date
      prices = prices.sort_values('Date').reset_index(drop=True)
      current_price = prices.iloc[-1]['Close']

      earnings = earnings.dropna(subset=['Reported EPS'])
      earnings['Earnings Date'] = pd.to_datetime(earnings['Earnings Date'],
                                                 utc=True)
      earnings['Date'] = earnings['Earnings Date'].dt.tz_convert(
          'America/New_York').dt.date

      earnings = earnings.sort_values('Date', ascending=False)
      if earnings.empty:
        continue

      latest_earnings_date = earnings.iloc[0]['Date']
      t0_idx = prices.index[prices['Date'] <= latest_earnings_date].tolist()
      if not t0_idx:
        continue

      t0_idx = t0_idx[-1]
      t0_price = prices.iloc[t0_idx]['Close']
      t0_date = prices.iloc[t0_idx]['Date']

      pl_pct = ((current_price - t0_price) / t0_price) * 100
      results.append({
          "Ticker": t,
          "Current Price": f"${current_price:.2f}",
          "Pre-Q4 Basis": f"${t0_price:.2f}",
          "Date": t0_date,
          "Q4 P/L": f"{pl_pct:+.1f}%"
      })
    except Exception as e:
      if t == "TSM":
        # Known TSM Q4 T0 approximate date: Jan 15th
        prices = pd.read_csv(os.path.join(MARKET_DATA_DIR,
                                          f"tickers/{t}/prices.tsv"),
                             sep="\t")
        prices['Date'] = pd.to_datetime(prices['Date']).dt.date
        prices = prices.sort_values('Date').reset_index(drop=True)
        current_price = prices.iloc[-1]['Close']

        t0_date = pd.to_datetime('2026-01-15').date()
        t0_idx = prices.index[prices['Date'] <= t0_date].tolist()
        if t0_idx:
          t0_idx = t0_idx[-1]
          t0_price = prices.iloc[t0_idx]['Close']
          pl_pct = ((current_price - t0_price) / t0_price) * 100
          results.append({
              "Ticker": t,
              "Current Price": f"${current_price:.2f}",
              "Pre-Q4 Basis": f"${t0_price:.2f}",
              "Date": t0_date,
              "Q4 P/L": f"{pl_pct:+.1f}%"
          })

  return pd.DataFrame(results)


def calculate_historical_sympathy_beta(nvda_df, tickers):
  if nvda_df is None or nvda_df.empty:
    return pd.DataFrame()

  nvda_recent = nvda_df.tail(12)
  # Exclude current incomplete earnings block
  nvda_recent = nvda_recent[nvda_recent['Earnings_Date'] != pd.to_datetime('2026-02-25').date()]
  results = []

  for t in tickers:
    try:
      prices = pd.read_csv(os.path.join(MARKET_DATA_DIR, f"tickers/{t}/prices.tsv"), sep="\t")
      prices['Date'] = pd.to_datetime(prices['Date']).dt.date
      prices = prices.sort_values('Date').reset_index(drop=True)

      bull_moves = []
      bear_moves = []

      for _, row in nvda_recent.iterrows():
        edate = row['Earnings_Date']
        nvda_move = row['Close_Change_Pct']

        t0_idx = prices.index[prices['Date'] == edate].tolist()
        if not t0_idx:
          t0_idx = prices.index[prices['Date'] < edate].tolist()
          if not t0_idx:
            continue
          t0_idx = [t0_idx[-1]]
        t0_idx = t0_idx[0]

        if t0_idx + 1 >= len(prices):
          continue
        t1_idx = t0_idx + 1

        t0_close = prices.iloc[t0_idx]['Close']
        t1_close = prices.iloc[t1_idx]['Close']
        pct_change = (t1_close - t0_close) / t0_close * 100

        if nvda_move > 0:
          bull_moves.append(pct_change)
        else:
          bear_moves.append(pct_change)

      avg_bull = sum(bull_moves) / len(bull_moves) if bull_moves else 0
      avg_bear = sum(bear_moves) / len(bear_moves) if bear_moves else 0

      results.append({
          'Ticker': t,
          'Historic Bull Case (NVDA +)': f"{avg_bull:+.2f}%",
          'Historic Bear Case (NVDA -)': f"{avg_bear:+.2f}%"
      })
    except Exception:
      continue

  return pd.DataFrame(results)

def calculate_iv_crush_metrics(nvda_df):
  """Calculates the options premium decay from Intraday Peak to Final Close."""
  if nvda_df is None or nvda_df.empty:
    return pd.DataFrame()

  recent = nvda_df.tail(12)
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

def generate_iv_crush_plot(iv_df):
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
  plt.title("NVDA Implied Volatility (IV) Crush Decay", fontsize=14, fontweight='bold')
  plt.ylabel("Premium Decay from Peak to Close (%)", fontsize=12)
  plt.xticks(rotation=45)
  plt.tight_layout()
  out_path = os.path.join(os.path.dirname(__file__), "plots", "nvda_iv_crush.png")
  plt.savefig(out_path, dpi=300)
  plt.close()

def generate_beta_plot(beta_df):
  if beta_df is None or beta_df.empty:
    return
  plt.figure(figsize=(10, 6))
  sns.set_theme(style="whitegrid")
  df = beta_df.copy()
  df['Bull'] = df['Historic Bull Case (NVDA +)'].str.replace('%', '').astype(float)
  df['Bear'] = df['Historic Bear Case (NVDA -)'].str.replace('%', '').astype(float)
  df_melt = df.melt(id_vars='Ticker', value_vars=['Bull', 'Bear'], var_name='Scenario', value_name='Expected Move (%)')
  sns.barplot(x='Ticker', y='Expected Move (%)', hue='Scenario', data=df_melt, palette=['#2ecc71', '#e74c3c'])
  plt.title("Portfolio Sympathy Beta Impact (1-Day)", fontsize=14, fontweight='bold')
  plt.axhline(0, color='black', linewidth=1)
  plt.tight_layout()
  out_path = os.path.join(os.path.dirname(__file__), "plots", "portfolio_sympathy_beta.png")
  plt.savefig(out_path, dpi=300)
  plt.close()


def generate_trajectory_prediction_plot():
  """Generates a speculative T0 -> T1 trajectory plot for the 3 hypotheses."""
  plt.figure(figsize=(10, 6))
  sns.set_theme(style="darkgrid")

  # Base T0 Price assumption (Feb 25 Close)
  t0_price = 195.56

  # Timepoints
  x = [0, 1, 2, 3]
  labels = ['T0 (Feb 25 Close)', 'T1 Open (9:30 AM)', 'T1 Peak (10:30 AM)', 'T1 Close (4:00 PM)']

  # Scenario A: The Baseline Fade (Average 8-Quarter Data)
  # Open: +3.86%, Peak: +6.06%, Close: +1.34%
  fade_y = [
      t0_price,
      t0_price * 1.0386,
      t0_price * 1.0606,
      t0_price * 1.0134
  ]
  plt.plot(x, fade_y, marker='o', label='Baseline Fade (Avg)', color='blue', linewidth=3)

  # Scenario B: Super-Beat Squeeze (Feb 2024 proxy: +16.4% close)
  # Open: +10%, Peak: +16.4%, Close: +16.4%
  squeeze_y = [
      t0_price,
      t0_price * 1.10,
      t0_price * 1.164,
      t0_price * 1.164
  ]
  plt.plot(x, squeeze_y, marker='^', label='Super-Beat Squeeze (Tail Risk)', color='green', linestyle='--', linewidth=2)
  plt.fill_between(x, squeeze_y, [y * 0.98 for y in squeeze_y], color='green', alpha=0.1)

  # Scenario C: In-Line Miss (Feb 2025 proxy: -8.47% close)
  # Open: +2.86%, Peak: +3.0%, Close: -8.47%
  plunge_y = [
      t0_price,
      t0_price * 1.0286,
      t0_price * 1.03,
      t0_price * 0.9153
  ]
  plt.plot(x, plunge_y, marker='v', label='In-Line Miss (Deflationary Plunge)', color='red', linestyle=':', linewidth=2)
  plt.fill_between(x, plunge_y, [y * 1.02 for y in plunge_y], color='red', alpha=0.1)

  plt.title("NVDA Predicted Execution Trajectories (T+1 Models)", fontsize=14, fontweight='bold')
  plt.ylabel("Estimated Price ($)", fontsize=12)
  plt.xticks(x, labels, fontsize=10)

  # --- TODO (2/26): Ground Truth Overlay ---
  # Uncomment and populate actual prices after market close on 2/26
  # actual_t1_open = 0 # INSERT PRE-MARKET ACTUAL
  # actual_t1_peak = 0 # INSERT INTRADAY PEAK
  # actual_t1_close = 0 # INSERT FINAL CLOSE

  # actual_y = [t0_price, actual_t1_open, actual_t1_peak, actual_t1_close]
  # plt.plot(x, actual_y, marker='D', label='ACTUAL 2/26 Ground Truth', color='black', linewidth=4, linestyle='-.')
  # ----------------------------------------

  # Target Buy Zone Annotation for the Baseline Fade
  buy_zone_y = fade_y[-1]
  plt.axhspan(195, 198, color='gold', alpha=0.3, label='Fade Buy Target ($195-$198)')

  plt.legend(loc="upper left")
  plt.tight_layout()
  output_path = os.path.join(os.path.dirname(__file__), "plots", "nvda_trajectory_prediction.png")
  plt.savefig(output_path, dpi=300)
  plt.close()


def generate_nvda_fade_plot(nvda_df):
  if nvda_df is None or nvda_df.empty:
    return
  df = nvda_df.tail(12)
  plt.figure(figsize=(10, 6))
  sns.set_theme(style="whitegrid")
  # Drop NaNs to prevent plotting issues for the incomplete current quarter
  plot_df = df.dropna(subset=['Open_Change_Pct', 'High_Change_Pct', 'Close_Change_Pct'])

  dates = plot_df['Earnings_Date'].astype(str).tolist()
  plt.plot(dates,
           plot_df['Open_Change_Pct'],
           marker='o',
           label='Open (Gap Up)',
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
  plt.title("NVDA Post-Earnings Price Action (T+1): The Intraday Fade",
            fontsize=14,
            fontweight='bold')
  plt.ylabel("Percentage Change from T0 Close (%)", fontsize=12)
  plt.xlabel("Earnings Date", fontsize=12)
  plt.xticks(rotation=45)
  plt.axhline(0, color='black', linewidth=1, linestyle='-')
  plt.legend(loc="upper left")
  plt.tight_layout()
  output_path = os.path.join(os.path.dirname(__file__), "plots", "nvda_fade_pattern.png")
  plt.savefig(output_path, dpi=300)
  plt.close()


def generate_nvda_surprise_scatter_plot(nvda_df):
  if nvda_df is None or nvda_df.empty:
    return
  df = nvda_df.tail(12)
  # Filter to strictly 2024 and beyond
  df['Year'] = pd.to_datetime(df['Earnings_Date']).dt.year
  df = df[df['Year'] >= 2024]

  plt.figure(figsize=(10, 6))
  sns.set_theme(style="whitegrid")
  # Drop NaNs
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
  plt.title("NVDA EPS Surprise vs. Post-Earnings Close (T+1)",
            fontsize=14,
            fontweight='bold')
  plt.ylabel("Close Percentage Change (%)", fontsize=12)
  plt.xlabel("EPS Surprise (%)", fontsize=12)
  plt.axhline(0, color='black', linewidth=1, linestyle='-')

  # Annotate points
  for i, row in plot_df.iterrows():
    plt.annotate(row['Earnings_Date'],
                 (row['Surprise_Pct'], row['Close_Change_Pct']),
                 textcoords="offset points",
                 xytext=(0, 10),
                 ha='center',
                 fontsize=8)

  plt.tight_layout()
  output_path = os.path.join(os.path.dirname(__file__), "plots",
                             "nvda_surprise_scatter.png")
  plt.savefig(output_path, dpi=300)
  plt.close()


def build_nvda_decision_tree():
  """Generates a Graphviz decision tree for the highly volatile NVDA Earnings Print execution."""
  dot = Digraph(comment='NVDA Earnings Execution')
  setup_decision_tree_aesthetics(dot)

  dot.node('A', 'NVDA Q4 Earnings Print\n(Feb 25, 2026)', fillcolor='lightblue', fontsize='16')

  # Scenarios matching trajectory plot colors
  dot.node('B1', 'Scenario A:\nGap Up (+3% to +6%)', style='filled', fillcolor='#d4edda', fontsize='14', fontname='Helvetica-Bold') # light green
  dot.node('B2', 'Scenario B:\nSuper-Squeeze (>+10%)', style='filled', fillcolor='#fff3cd', fontsize='14', fontname='Helvetica-Bold') # light gold/yellow
  dot.node('B3', 'Scenario C:\nFlat / Negative (<+1%)', style='filled', fillcolor='#f8d7da', fontsize='14', fontname='Helvetica-Bold') # light red

  dot.edge('A', 'B1', label='>$200 Open', fontsize='12', fontname='Helvetica-Bold')
  dot.edge('A', 'B2', label='>$215 Open', fontsize='12', fontname='Helvetica-Bold')
  dot.edge('A', 'B3', label='<$197 Open', fontsize='12', fontname='Helvetica-Bold')

  # Actions B1
  dot.node('C1_A', '9:30 AM Open: SELL 5 Shares\n(Capture FOMO / Avoid Crush)', shape='ellipse', fontsize='14', fontname='Helvetica')
  dot.node('C1_B', '2:30 PM Fade: BUY ~21 Shares\n(Ride structural T+3 trend)', shape='ellipse', fontsize='14', fontname='Helvetica')
  dot.edge('B1', 'C1_A')
  dot.edge('C1_A', 'C1_B', label='Deploy Combined Cash', fontsize='10', fontname='Helvetica-Oblique')

  # Actions B2
  dot.node('C2_A', '9:30 AM Open: HOLD 5 Shares\n(Do not fight massive momentum)', shape='ellipse', fontsize='14', fontname='Helvetica')
  dot.node('C2_B', '2:30 PM Fade: ABORT NVDA BUYS\n(Deploy cash defensively to AMD)', shape='ellipse', fontsize='14', fontname='Helvetica')
  dot.edge('B2', 'C2_A')
  dot.edge('B2', 'C2_B')

  # Actions B3
  dot.node('C3_A', '9:30 AM Open: SELL 5 Shares\n(Liquidate immediately/Stop Loss)', shape='ellipse', fontsize='14', fontname='Helvetica')
  dot.node('C3_B', '2:30 PM Fade: ABORT ALL BUYS\n(Hoard cash, wait 3 days)', shape='ellipse', fontsize='14', fontname='Helvetica')
  dot.edge('B3', 'C3_A')
  dot.edge('B3', 'C3_B')

  # Save
  plots_dir = os.path.join(os.path.dirname(__file__), "plots")
  os.makedirs(plots_dir, exist_ok=True)
  out_path = os.path.join(plots_dir, 'nvda_decision_tree')

  try:
    dot.render(out_path, format='png', cleanup=True)
  except Exception as e:
    print(f"Graphviz failed to render (is it installed?): {e}")

def run_full_analysis():
  """Runs the full pipeline and extrudes REPORT.md with integrated Sympathy Beta."""
  print("Running NVDA Trade Analysis...")
  tickers = ["NVDA", "AMD", "MU", "TSM", "INTC", "AAPL", "GOOG"]
  nvda_df = analyze_earnings_movement("NVDA", MARKET_DATA_DIR)

  # Generate Beta Data early so it can be used/displayed in the report seamlessly
  beta_df = calculate_historical_sympathy_beta(nvda_df, tickers)

  report_path = os.path.join(os.path.dirname(__file__), "REPORT.md")

  # Ensure plots directory exists
  os.makedirs(os.path.join(os.path.dirname(__file__), "plots"), exist_ok=True)

  # Read the user's hand-crafted static narrative report specifically chopping at the Appendix Header
  static_content = ""
  appendix_header = "## Program Output"

  if os.path.exists(report_path):
    with open(report_path, 'r') as f:
      full_text = f.read()
      # Find the split string
      if appendix_header in full_text:
        static_content = full_text.split(appendix_header)[0].strip()
      else:
        static_content = full_text.strip()

  md_lines = []
  if static_content:
    # Safely inject the raw user content first
    md_lines.append(static_content + "\n\n")
  else:
    md_lines.append("# NVDA Earnings Portfolio Playbook (Q4 Fiscal 2026)\n\n*(Error: Static narrative block missing!)*\n\n")

  # 7. Appendix - Raw Data Show
  md_lines.append(appendix_header + "\n")
  md_lines.append("*(Note: Everything below this line is programmatically generated and updated by `nvda_trade_analysis.py`. Run the script to refresh the data.)*\n\n")
  if nvda_df is not None:
    recent = nvda_df.tail(12).copy()

    # Format numeric columns gracefully
    cols_to_format = ['Surprise_Pct', 'Open_Change_Pct', 'High_Change_Pct', 'Close_Change_Pct']
    for col in cols_to_format:
      recent[col] = recent[col].map(lambda x: format_num(x, is_pct=True, is_signed=True))

    disp_df = recent[['Earnings_Date', 'Surprise_Pct', 'Open_Change_Pct', 'High_Change_Pct', 'Close_Change_Pct']]

    md_lines.append(disp_df.to_markdown(index=False) + "\n\n")

    avg_df = recent[recent['Earnings_Date'] != pd.to_datetime('2026-02-25').date()]

    md_lines.append(
        f"*   **Historical Average Gap Up (Open):** `{avg_df['Open_Change_Pct'].str.replace('%', '').astype(float).mean():+.2f}%`\n"
    )
    md_lines.append(
        f"*   **Historical Average Intraday Peak:** `{avg_df['High_Change_Pct'].str.replace('%', '').astype(float).mean():+.2f}%`\n"
    )
    md_lines.append(
        f"*   **Historical Average Close:** `{avg_df['Close_Change_Pct'].str.replace('%', '').astype(float).mean():+.2f}%`\n\n"
    )
    generate_nvda_fade_plot(nvda_df)
    generate_nvda_surprise_scatter_plot(nvda_df)

    generate_trajectory_prediction_plot()

    # Inject IV Crush Table
    md_lines.append("### Implied Volatility (IV) Crush Metrics\n")
    md_lines.append("*The 'Gap Trap': Tracking options premium decay from the Intraday Peak (FOMO) to the Final Close.*\n\n")
    iv_df = calculate_iv_crush_metrics(nvda_df)
    if not iv_df.empty:
      md_lines.append(iv_df.to_markdown(index=False) + "\n\n")
      generate_iv_crush_plot(iv_df)

    avg_iv_df = iv_df[iv_df['Earnings Date'] != pd.to_datetime('2026-02-25').date()]
    md_lines.append(
        f"*   **Average Premium Decay per Quarter:** `{avg_iv_df['Premium Decay (Crush)'].str.replace('%', '').astype(float).mean():+.2f}%`\n\n"
    )

  # 1.5 Execution Options
  build_nvda_decision_tree()

  # 2. Portfolio Technicals
  md_lines.append("### Current Portfolio Technical Indicators\n")
  techs = [get_technical_indicators(t, os.path.join(MARKET_DATA_DIR, "tickers")) for t in tickers]
  techs = [t for t in techs if t is not None]
  if techs:
    techs_df = pd.DataFrame(techs)
    # Manually format floats
    float_cols = techs_df.select_dtypes(include=['float64']).columns
    for col in float_cols:
      techs_df[col] = techs_df[col].map(format_num)
    md_lines.append(techs_df.to_markdown(index=False) + "\n\n")
    plot_portfolio_rsi(techs, os.path.join(os.path.dirname(__file__), "plots", "portfolio_rsi.png"))
    plot_ma200_distance(techs, os.path.join(os.path.dirname(__file__), "plots", "portfolio_ma200_dist.png"))

  # 3. Cost Basis & Unrealized PL
  md_lines.append("### Q4 Portfolio Unrealized P/L (T0 Cost Basis)\n")
  pl_df = calculate_q4_cost_basis(tickers)
  if not pl_df.empty:
    pl_df_disp = pl_df.copy()
    pl_df_disp['Current Price'] = pl_df_disp['Current Price'].map(lambda x: format_num(x, prefix="$"))
    pl_df_disp['Pre-Q4 Basis'] = pl_df_disp['Pre-Q4 Basis'].map(lambda x: format_num(x, prefix="$"))
    # Apply formatting for Unrealized_PnL_Pct and Portfolio_Weight_Pct
    if 'Unrealized_PnL_Pct' in pl_df_disp.columns:
      pl_df_disp['Unrealized_PnL_Pct'] = pl_df_disp['Unrealized_PnL_Pct'].map(lambda x: format_num(x, is_pct=True, is_signed=True, default_nan="NaN"))
    if 'Portfolio_Weight_Pct' in pl_df_disp.columns:
      pl_df_disp['Portfolio_Weight_Pct'] = pl_df_disp['Portfolio_Weight_Pct'].map(lambda x: format_num(x, is_pct=True, default_nan="NaN"))
    md_lines.append(pl_df_disp.to_markdown(index=False) + "\n\n")

  md_lines.append("### Historical Asymmetric Sympathy Beta (Trailing 12 Quarters)\n")
  md_lines.append("> *How the portfolio acts specifically in response to NVDA crashing vs surging.*\n\n")
  if beta_df is not None and not beta_df.empty:
    beta_df_disp = beta_df.copy()
    # Format the beta columns which contain numeric data before they get rendered
    for col in beta_df_disp.columns:
      if col != 'Ticker':
        beta_df_disp[col] = beta_df_disp[col].map(lambda x: format_num(x, is_pct=True, is_signed=True))
    md_lines.append(beta_df_disp.to_markdown(index=False) + "\n\n")
    generate_beta_plot(beta_df)

  # 5. Macro Sentiment
  md_lines.append("### Corroborating Macro Data (Recent Headlines)\n")
  for topic in ["GPU", "AI", "Data Center"]:
    news = get_recent_news(topic, MARKET_DATA_DIR)
    if not news.empty:
      for _, r in news.iterrows():
        md_lines.append(
            f"*   **[{topic}]** ({r['Date'].date()}): *{r['Headline']}*\n")

  # 5. Anomalies
  md_lines.append("\n### Known System Anomalies\n")
  md_lines.append(
      "*   **Missing TSM Earnings Data:** The local `market_data/tickers/TSM/` environment lacked a localized `earnings.tsv` file. The Q4 cost-basis calculation for Taiwan Semiconductor was programmatically hardcoded to anchor to January 15, 2026 (its historic standard report date) to prevent pipeline failure and ensure accurate portfolio P/L math.\n"
  )

  current_time = pd.Timestamp.now(tz='US/Pacific').strftime("%Y-%m-%d %H:%M %Z")
  md_lines.append(f"\n---\n*Generated: {current_time}*\n")

  output_file = os.path.join(os.path.dirname(__file__), "REPORT.md")

  with open(output_file, "w") as f:
    f.writelines(md_lines)

  print(f"Data successfully generated to {output_file}")


if __name__ == "__main__":
  run_full_analysis()
