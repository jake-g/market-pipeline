# Broader Iran Strategy & Geo-Macro Report

## Objective
This prompt generates a highly concise, data-driven strategy report that synthesizes deep research on the broader structural effects of the U.S.-Iran conflict. It focuses on Desalination/Water Security, Energy/Oil shocks, and broad Military/Defense logistics.

## Target Audience
Senior Portfolio Managers requiring actionable, path-dependent logic for capital deployment across multiple impacted sectors.

## Workflow

1.  **Initial Research:**
    *   Aggregate research into a `.DEEP_RESEARCH.md` document covering the industrial profiles of Gulf Infrastructure, Defense Contractors, and Energy Majors.
    *   Identify key publicly traded companies across these silos.

2.  **Data Fetching:**
    *   Use the `market-pipeline` scripts to pre-fetch real-time data for the basket.
    *   Example: `python market_fetcher.py --tickers DD,AWK,XYL,CVX,XOM,SLB,LMT,RTX,BA,ESLT,GD,NOC,ZIM`

3.  **Analysis Script Generation:**
    *   Run `iran_broad_strategy_analysis.py` to generate:
        *   **Multiple Decision Trees**: Distinct logical paths for Oil/Energy, Water Security, and Military Logistics.
        *   **Quantitative Allocations**: A target percentage cross-sector portfolio.
        *   **Technical Timings**: Scatter plots for RSI vs 200MA.

4.  **NotebookLM Synthesis (AI Insights):**
    *   Upload the initial `.DEEP_RESEARCH.md`, the output `REPORT.md`, and relevant news TSVs to a dedicated NotebookLM notebook.
    *   Prompt NotebookLM:
        > Act as a senior geopolitical defense and macro-energy analyst. Synthesize the provided deep research on the Iran conflict with the latest market data.
        >
        > **Critical Directives:**
        > 1. Critically evaluate the provided decision tree and proposed portfolio basket. Directly CONFIRM or OPPOSE the strategic logic and timing.
        > 2. Cite specific evidence from the uploaded research documents and cross-reference with related news in your database (e.g., previous geopolitics reports like 03-02).
        > 3. Provide a highly concise, bulleted readout of these insights.
        > 4. Output in rich markdown suitable for appending to the absolute end of a formal report.

5.  **Final Assembly:**
    *   Copy the NotebookLM output into `iran_broad_strategy_analysis.py` (or let it manually append to `REPORT.md`).
    *   Ensure strict section ordering: Context > Decision Trees > Portfolio > Timing > Future Refection > AI Insights > Deep Research.
