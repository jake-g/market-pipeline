# 04-24 Chip & AI Hedge Portfolio Prompt
*Location: analyze_04_24.py | REPORT.md*

**Purpose:** This document serves as a master prompt and framework for regenerating a highly anonymized, data-driven overview report for the **Chip & AI Hedge Portfolio** on April 24, 2026. It focuses on hiding prices, showing only percentages, and adding performance comparison against benchmarks.

---

## 1. System Setup & Data Ingestion
**Goal:** Load and combine portfolios, focusing only on individual stocks and hiding all absolute dollar values.

*   **Portfolio Bases:**
    *   `portfolios/tsvs/vanguard__roth_ira_6381.tsv`
    *   `portfolios/tsvs/vanguard__individual_8479.tsv`
*   **Combination Logic:** Concatenate and aggregate by Ticker, summing Quantity, Current_Value, and Cost_Basis.
*   **Filtering:** Exclude all broad market indices (VTSAX, VIGAX, VOO, etc.) and cash positions (CASH, VMFXX) to focus solely on individual stocks.
*   **Anonymization:** Calculate `Portfolio_Weight_Pct` and `Unrealized_PnL_Pct` based on the filtered total. Do **not** show `Current_Value`, `Cost_Basis`, or prices in the final report or tables.
*   **No Fetch:** This script assumes data is already fetched and cached in `market_data/`.

## 2. Visual Synthesis & Plots
**Goal:** Generate visualizations to support the breakdown and performance comparison.

*   **Combined Allocation & Sector Breakdown (`plots/allocation_combined.png`)**:
    *   *Implementation:* `matplotlib.pyplot` subplots (1 row, 2 columns) showing side-by-side donut charts for Ticker Allocation and Sector Breakdown. Use Seaborn `hls` palette for unique colors. Group slices smaller than 1% into "Others".
*   **Correlation Heatmap (`plots/correlation_heatmap.png`)**:
    *   *Implementation:* Call `report_utils.plot_correlation_heatmap` for **all** individual holdings to visualize risk concentration. Use a large figure size (e.g., 24x20).
*   **Performance Comparison Plot (`plots/performance_comparison.png`)**:
    *   *Implementation:* Line chart comparing the portfolio's YTD 2026 performance (assuming static current weights) against **SPY** and **VUG**. Annotate final outperformance on the plot.

## 3. The Core Markdown Report Structure
**Goal:** Construct `REPORT.md` focusing on percentages and trend analysis.

The report *must* follow this structure:
1.  **Executive Overview:** Vague title `# 04-24 Chip & AI Hedge Portfolio Report`. Note on anonymization and exclusion of indices.
2.  **📊 Allocation & Sector Breakdown:** Side-by-side donut charts.
3.  **📈 Performance Comparison (YTD 2026):** Line chart with benchmarks.
4.  **📈 Correlation Analysis:** Large heatmap for all holdings.
5.  **🔍 Concentration Risk:** Text summarizing top 5 weight sum.
6.  **📈 Trend & Momentum Analysis:** Dynamic text citing RSI and Distance to 200MA for top holdings.
7.  **📑 Combined Holdings Table:** Showing Ticker, Name, Sector, Quantity, Weight %, PnL %, RSI, Dist_to_200MA, Upcoming_Earnings. **No prices**.
8.  **🤖 NotebookLM Red-Team Critique:** Appended critique focusing on holdings, risks, and strategies for this specific portfolio.

## 4. NotebookLM Integration
**Goal:** Use NotebookLM for a critique on the anonymized data.
*   *Prompt:* "Act as a senior macroeconomic strategist. Critique the holdings, risks, and strategies for this portfolio based on the provided overview. Do not assume any price data not shown."
