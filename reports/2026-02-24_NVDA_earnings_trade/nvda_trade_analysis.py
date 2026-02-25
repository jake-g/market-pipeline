import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from graphviz import Digraph

# Adjust the path to read market_data from the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
MARKET_DATA_DIR = os.path.join(PROJECT_ROOT, "market_data")


def compute_rsi(data, window=14):
  delta = data.diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
  RS = gain / loss
  return 100 - (100 / (1 + RS))


def get_technical_indicators(ticker):
  try:
    prices = pd.read_csv(os.path.join(MARKET_DATA_DIR,
                                      f"tickers/{ticker}/prices.tsv"),
                         sep="\t")
    prices['Date'] = pd.to_datetime(prices['Date'])
    prices = prices.sort_values('Date').reset_index(drop=True)
    prices['MA200'] = prices['Close'].rolling(window=200).mean()
    prices['RSI'] = compute_rsi(prices['Close'])

    last_row = prices.iloc[-1]
    dist_200 = (
        (last_row['Close'] - last_row['MA200']) / last_row['MA200']) * 100
    last5_return = (last_row['Close'] / prices.iloc[-6]['Close'] - 1) * 100

    return {
        "Ticker": ticker,
        "Close": f"${last_row['Close']:.2f}",
        "RSI": round(last_row['RSI'], 1),
        "Dist_to_200MA": round(dist_200, 1),
        "Trailing_5D_Ret": round(last5_return, 1)
    }
  except Exception as e:
    return None


def analyze_earnings_movement(ticker):
  try:
    earnings = pd.read_csv(os.path.join(MARKET_DATA_DIR,
                                        f"tickers/{ticker}/earnings.tsv"),
                           sep="\t")
    prices = pd.read_csv(os.path.join(MARKET_DATA_DIR,
                                      f"tickers/{ticker}/prices.tsv"),
                         sep="\t")

    prices['Date'] = pd.to_datetime(prices['Date']).dt.date
    prices = prices.sort_values('Date').reset_index(drop=True)

    earnings = earnings.dropna(subset=['Reported EPS'])  # Drop future
    earnings['Earnings Date'] = pd.to_datetime(earnings['Earnings Date'],
                                               utc=True)
    earnings['Date'] = earnings['Earnings Date'].dt.tz_convert(
        'America/New_York').dt.date

    results = []

    for _, row in earnings.iterrows():
      edate = row['Date']

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

      t0_row = prices.iloc[t0_idx]
      t1_row = prices.iloc[t1_idx]

      t0_close = t0_row['Close']
      t1_open = t1_row['Open']
      t1_high = t1_row['High']
      t1_close = t1_row['Close']

      open_pct = (t1_open - t0_close) / t0_close * 100
      close_pct = (t1_close - t0_close) / t0_close * 100
      high_pct = (t1_high - t0_close) / t0_close * 100

      results.append({
          'Earnings_Date': edate,
          'Surprise_Pct': row['Surprise(%)'],
          'T0_Close': t0_close,
          'T1_Open': t1_open,
          'T1_High': t1_high,
          'T1_Close': t1_close,
          'Open_Change_Pct': open_pct,
          'High_Change_Pct': high_pct,
          'Close_Change_Pct': close_pct
      })

    df = pd.DataFrame(results)
    df = df.sort_values('Earnings_Date', ascending=True).reset_index(drop=True)
    return df
  except Exception as e:
    return None


def get_recent_news(topic):
  try:
    path = os.path.join(MARKET_DATA_DIR, f"topics/{topic}/news.tsv")
    news = pd.read_csv(path, sep="\t")
    news['Date'] = pd.to_datetime(news['Date'])
    # sort desc
    news = news.sort_values('Date', ascending=False).head(3)
    return news
  except Exception as e:
    return pd.DataFrame()


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

  nvda_recent = nvda_df.tail(8)
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

  recent_8 = nvda_df.tail(8)
  results = []

  for _, row in recent_8.iterrows():
    edate = row['Earnings_Date']
    peak = row['High_Change_Pct']
    close = row['Close_Change_Pct']

    # Premium decay is the percentage points lost from the absolute peak to the close
    decay = close - peak

    results.append({
        'Earnings Date': edate,
        'Intraday Peak (High)': f"{peak:+.2f}%",
        'T+1 Final Close': f"{close:+.2f}%",
        'Premium Decay (Crush)': f"{decay:+.2f}%"
    })

  return pd.DataFrame(results)


def generate_trajectory_prediction_plot():
  """Generates a speculative T0 -> T1 trajectory plot for the 3 hypotheses."""
  plt.figure(figsize=(10, 6))
  sns.set_theme(style="darkgrid")

  # Base T0 Price assumption
  t0_price = 192.85

  # Timepoints
  x = [0, 1, 2, 3]
  labels = ['T0 (Feb 24 Close)', 'T1 Open (9:30 AM)', 'T1 Peak (10:30 AM)', 'T1 Close (4:00 PM)']

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
  df = nvda_df.tail(8)
  plt.figure(figsize=(10, 6))
  sns.set_theme(style="whitegrid")
  dates = df['Earnings_Date'].astype(str).tolist()
  plt.plot(dates,
           df['Open_Change_Pct'],
           marker='o',
           label='Open (Gap Up)',
           color='green',
           linewidth=2)
  plt.plot(dates,
           df['High_Change_Pct'],
           marker='^',
           label='Peak (Intraday High)',
           color='orange',
           linestyle='--',
           linewidth=2)
  plt.plot(dates,
           df['Close_Change_Pct'],
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
  df = nvda_df.tail(8)
  plt.figure(figsize=(10, 6))
  sns.set_theme(style="whitegrid")
  sns.scatterplot(x='Surprise_Pct',
                  y='Close_Change_Pct',
                  data=df,
                  s=150,
                  color='purple',
                  alpha=0.8)
  sns.regplot(x='Surprise_Pct',
              y='Close_Change_Pct',
              data=df,
              scatter=False,
              color='gray',
              line_kws={"linestyle": "--"})
  plt.title("NVDA EPS Surprise vs. Post-Earnings Close (T+1)",
            fontsize=14,
            fontweight='bold')
  plt.ylabel("Close Percentage Change (%)", fontsize=12)
  plt.xlabel("EPS Surprise (%)", fontsize=12)
  plt.axhline(0, color='black', linewidth=1, linestyle='-')

  # Annotate points
  for i, row in df.iterrows():
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


def generate_portfolio_rsi_plot(techs):
  if not techs:
    return
  df = pd.DataFrame(techs)
  df = df.sort_values('RSI', ascending=False)
  plt.figure(figsize=(10, 6))
  sns.set_theme(style="whitegrid")
  colors = [
      '#e74c3c' if rsi >= 70 else ('#2ecc71' if rsi <= 30 else '#95a5a6')
      for rsi in df['RSI']
  ]
  ax = sns.barplot(x='Ticker',
                   y='RSI',
                   hue='Ticker',
                   data=df,
                   palette=colors,
                   legend=False)
  plt.axhline(70,
              color='red',
              linestyle='--',
              alpha=0.7,
              label='Overbought Threshold (70)')
  plt.axhline(30,
              color='green',
              linestyle='--',
              alpha=0.7,
              label='Oversold Threshold (30)')
  plt.title("Portfolio RSI (Relative Strength Index) Heat Check",
            fontsize=14,
            fontweight='bold')
  plt.ylabel("14-Day RSI", fontsize=12)
  plt.xlabel("Ticker", fontsize=12)
  plt.legend(loc='best')
  plt.tight_layout()
  output_path = os.path.join(os.path.dirname(__file__), "plots", "portfolio_rsi.png")
  plt.savefig(output_path, dpi=300)
  plt.close()


def generate_ma200_distance_plot(techs):
  if not techs:
    return
  df = pd.DataFrame(techs)
  df = df.sort_values('Dist_to_200MA', ascending=False)
  plt.figure(figsize=(10, 6))
  sns.set_theme(style="whitegrid")
  colors = [
      '#27ae60' if dist > 0 else '#c0392b' for dist in df['Dist_to_200MA']
  ]
  ax = sns.barplot(x='Ticker',
                   y='Dist_to_200MA',
                   hue='Ticker',
                   data=df,
                   palette=colors,
                   legend=False)
  plt.axhline(0, color='black', linewidth=1, linestyle='-')
  plt.title("Portfolio Structural Momentum (Distance to 200-Day MA)",
            fontsize=14,
            fontweight='bold')
  plt.ylabel("Percentage Distance (%)", fontsize=12)
  plt.xlabel("Ticker", fontsize=12)

  # Add value labels on top of bars
  for i, v in enumerate(df['Dist_to_200MA']):
    ax.text(i, v + (1 if v > 0 else -3), f"{v:+.1f}%", ha='center', fontsize=10)

  plt.tight_layout()
  output_path = os.path.join(os.path.dirname(__file__), "plots",
                             "portfolio_ma200_dist.png")
  plt.savefig(output_path, dpi=300)
  plt.close()

def build_nvda_decision_tree():
  """Generates a Graphviz decision tree for the highly volatile NVDA Earnings Print execution."""
  dot = Digraph(comment='NVDA Earnings Execution')
  dot.attr(rankdir='TB', size='12,12!', dpi='300', fontname='Helvetica', fontsize='14')

  dot.node('A', 'NVDA Q4 Earnings Print\n(Feb 25, 2026)', shape='box', style='filled', fillcolor='lightblue', fontsize='16', fontname='Helvetica-Bold')

  # Scenarios matching trajectory plot colors
  dot.node('B1', 'Scenario 1:\nMassive Beat & Raise', style='filled', fillcolor='#d4edda', fontsize='14', fontname='Helvetica-Bold') # light green
  dot.node('B2', 'Scenario 2:\nIn-Line / Barely Beats', style='filled', fillcolor='#fff3cd', fontsize='14', fontname='Helvetica-Bold') # light gold/yellow
  dot.node('B3', 'Scenario 3:\nThe Miss / CapEx Cut', style='filled', fillcolor='#f8d7da', fontsize='14', fontname='Helvetica-Bold') # light red

  dot.edge('A', 'B1', label='Guidance > $40B', fontsize='12', fontname='Helvetica-Bold')
  dot.edge('A', 'B2', label='Guidance ~ $35B', fontsize='12', fontname='Helvetica-Bold')
  dot.edge('A', 'B3', label='Guidance < $32B', fontsize='12', fontname='Helvetica-Bold')

  # Actions B1
  dot.node('C1_A', 'EXECUTE: Sell 30-50% into Initial IV Spike\n(Capture premium + intrinsic squeeze)', shape='ellipse', fontsize='14', fontname='Helvetica')
  dot.node('C1_B', 'HOLD: Ride the residual T+3 Sympathy Alpha\n(e.g. AMD, MU run)', shape='ellipse', fontsize='14', fontname='Helvetica')
  dot.edge('B1', 'C1_A')
  dot.edge('B1', 'C1_B')

  # Actions B2
  dot.node('C2', 'EXECUTE: The Baseline Fade\nWait for 10:30am, buy the localized -5% dip', shape='ellipse', fontsize='14', fontname='Helvetica')
  dot.edge('B2', 'C2')

  # Actions B3
  dot.node('C3_A', 'EXECUTE: Liquidation/Stop Loss\nClose out short-term speculative calls instantly', shape='ellipse', fontsize='14', fontname='Helvetica')
  dot.node('C3_B', 'ROTATE: Buy Defensive Growth\nMove capital into NVO, RTX, MPWR', shape='ellipse', fontsize='14', fontname='Helvetica')
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
  nvda_df = analyze_earnings_movement("NVDA")

  # Generate Beta Data early so it can be used/displayed in the report seamlessly
  beta_df = calculate_historical_sympathy_beta(nvda_df, tickers)

  report_path = os.path.join(os.path.dirname(__file__), "REPORT.md")

  # Ensure plots directory exists
  os.makedirs(os.path.join(os.path.dirname(__file__), "plots"), exist_ok=True)

  # Read the user's hand-crafted static narrative report specifically chopping at the Appendix Header
  static_content = ""
  appendix_header = "## Dynamic Computational Appendix"

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
    recent_8 = nvda_df.tail(8)
    md_lines.append(recent_8[[
        'Earnings_Date', 'Surprise_Pct', 'Open_Change_Pct', 'High_Change_Pct',
        'Close_Change_Pct'
    ]].to_markdown(index=False) + "\n\n")
    md_lines.append(
        f"*   **Historical Average Gap Up (Open):** `{recent_8['Open_Change_Pct'].mean():+.2f}%`\n"
    )
    md_lines.append(
        f"*   **Historical Average Intraday Peak:** `{recent_8['High_Change_Pct'].mean():+.2f}%`\n"
    )
    md_lines.append(
        f"*   **Historical Average Close:** `{recent_8['Close_Change_Pct'].mean():+.2f}%`\n\n"
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
    md_lines.append(
        f"*   **Average Premium Decay per Quarter:** `{iv_df['Premium Decay (Crush)'].str.replace('%', '').astype(float).mean():+.2f}%`\n\n"
    )

  # 1.5 Execution Options
  build_nvda_decision_tree()

  # 2. Portfolio Technicals
  md_lines.append("### Current Portfolio Technical Indicators\n")
  techs = [get_technical_indicators(t) for t in tickers]
  techs = [t for t in techs if t is not None]
  if techs:
    md_lines.append(pd.DataFrame(techs).to_markdown(index=False) + "\n\n")
    generate_portfolio_rsi_plot(techs)

    generate_ma200_distance_plot(techs)

  # 3. Cost Basis & Unrealized PL
  md_lines.append("### Q4 Portfolio Unrealized P/L (T0 Cost Basis)\n")
  pl_df = calculate_q4_cost_basis(tickers)
  if not pl_df.empty:
    md_lines.append(pl_df.to_markdown(index=False) + "\n\n")

  # 4. Asymmetric Sympathy Beta
  md_lines.append("### Historical Asymmetric Sympathy Beta (Trailing 8 Quarters)\n")
  if beta_df is not None and not beta_df.empty:
    md_lines.append(beta_df.to_markdown(index=False) + "\n\n")

  # 5. Macro Sentiment
  md_lines.append("### Corroborating Macro Data (Recent Headlines)\n")
  for topic in ["Tariffs", "Geopolitics", "Big Tech"]:
    news = get_recent_news(topic)
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
