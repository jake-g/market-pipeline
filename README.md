# 📈 Market Data Pipeline

[![View on GitHub](https://img.shields.io/badge/View_on-GitHub-181717?logo=github&style=flat)](https://github.com/jake-g/market-pipeline)
[![CI Status](https://github.com/jake-g/market-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/jake-g/market-pipeline/actions/workflows/ci.yml)
[![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-deployed-success?logo=github&style=flat)](https://jake-g.github.io/market-pipeline/)
[![View Demo Dashboard](https://img.shields.io/badge/View_Demo-Dashboard-blue?style=flat)](https://jake-g.github.io/market-pipeline/)
<!-- [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jake-g/market-pipeline/blob/main/notebooks/market_dashboard.ipynb) -->

## Overview
Fetch market data for a list of tickers and store it in a LLM and git friendly format.

Pipeline for fetching, backfilling, and analyzing financial data (Prices, News, Fundamentals, Macro). Fetches data from Yahoo Finance, Alpha Vantage, Google News, and FRED, storing it in plaintext formats.

### Key Features
- **[Web Dashboard](https://jake-g.github.io/market-pipeline/)**: Interactive visualization of market data.
- **Git-Friendly**: Uses TSV (Tab-Separated Values) and sort-stable updates to minimize diff noise.
- **Incremental Fetching**: Only pulls new data to respect API limits and reduce runtimes. Also backfill options.
- **Comprehensive Datasets**:
  - **OHLCV Prices**: Daily history (Default: 2018+).
  - **News**: Recent aggregate (Yahoo, Google, Seeking Alpha) and historical backfill (FNSPID, 2010-2020).
  - **Fundamentals**: Key metrics (P/E, Market Cap) and Quarterly Financials.
  - **Macro**: FRED Economic indicators (Inflation, PPI, US10Y).
  - **Insider Trading**: SEC Form 4 extraction via `sec-edgar-downloader`.
  - **ML Sentiment**: AlphaVantage Sentiment scoring and Hybrid TextBlob fallbacks.
  - **Calculated Metrics**: Graham Intrinsic Value, EPS Growth estimates, Technicals (RSI, MACD).

---
## Data Sources

### APIs
- **[Yahoo Finance (`yfinance`)](https://pypi.org/project/yfinance/)**: Historical OHLCV options and pricing data.
- **[FRED (Federal Reserve Economic Data)](https://fred.stlouisfed.org/)**: Macroeconomic indicators (GDP, CPI, Interest Rates).
- **[SEC Edgar (`sec-edgar-downloader`)](https://pypi.org/project/sec-edgar-downloader/)**: Form 4 extraction for insider trading data.
- **[Alpha Vantage](https://www.alphavantage.co/)**: Highly enriched historical news and sentiment scoring.
- **[Benzinga / Google News]**: RSS feeds used for real-time news aggregation.

### Datasets
- **FNSPID**: Financial News and Stock Price Integration Dataset
  - *Paper*: [FNSPID: A Comprehensive Financial News Dataset in Time Series](https://arxiv.org/abs/2402.06698)
  - *Authors*: Zihan Dong, Xinyu Fan, Zhiyuan Peng
  - *Source*: [HuggingFace - Zihan1004/FNSPID](https://huggingface.co/datasets/Zihan1004/FNSPID)

---

## Setup

Code is Python with .sh scripts to run common tasks.

### 1. Environment Setup
It is recommended to use a virtual environment to keep dependencies isolated.

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

> **Note**: `lxml` is required for fetching Earnings/Financials. If installation fails, ensure you have system headers `libxml2-dev` and `libxslt-dev` installed, or use a pre-built binary.

### 2. Run Tests
Validate the entire pipeline (Fetchers, Backfill, Notebook):
```bash
./run_tests.sh
```

### 3. Fetch Data
Run the full daily update pipeline:
```bash
./run_fetch.sh
```

### 4. Running the Dashboard
**Local Server (Recommended for Development):**
```bash
./run_server.sh
```
This runs a fast local server that auto-updates the file tree dynamically.

**Static Hosting (GitHub Pages):**
The dashboard is designed to run completely statically anywhere (like GitHub pages).
When `./run_fetch.sh` successfully finishes, it runs `market_dashboard_server.py --build` to create `market_data/index.json`. The `index.html` file will automatically load this static index.
To set this up on your repo:
1. Navigate to your repository **Settings > Pages** on GitHub.
2. Under **Build and deployment**, select **Deploy from a branch**.
3. Set the branch to `main` and the folder to `/ (root)`.
4. Click **Save**. Your site will now securely deploy natively using `index.html`.


> **Note**: These scripts automatically handle virtual environment creation and dependency installation via `run_env_setup.sh`.

---

## Library

The core is governed by the `market_data` library (`market_fetcher.py` and `config.py`), providing an object-oriented interface for data fetching.

### Core Components
- **`MarketFetcher`**: Main class. Handles intelligent `joblib` caching, TSV structured output, and strict API error resilience. Generates `STATS.md` and `SCHEMA.md` audits post-run.
- **`config.py`**: Central configuration mapping for `SECTORS`, `FRED_SERIES`, and cache invalidation timelines.

### Market Data Dashboard (`index.html`)
The primary human-readable visualization UI providing fast, interactive analytics for the dataset:
- **Interactive File Explorer**: Natively navigate the `market_data` tree (auto-expands to `STATS.md` on launch).
- **Embedded Plotly**: Select any TSV, click `PLOT`, and multi-line graph all numeric columns instantly.
- **Precomputed Metadata**: File line sizes and exact row lengths are precomputed efficiently by the static server for seamless browsing.
- **Search and Pinning**: Filter TSVs via regex, and pin high-signal files via `localStorage`.

---

## Scripts

| Script | Purpose |
|---|---|
| **`./run_test_pipeline.sh`** | **Verification**: Runs tests, fetches subset data (1000 limit), and validates integrity. Run before pushing. |
| **`./run_fetch.sh`** | **Production**: Fetches daily data for all `config.py` tickers + macro. Generates static `index.json`. |
| `market_fetcher.py` | Core CLI for fetching specific combinations (e.g. `--limit-tickers`, `--news-days`). |
| `./run_server.sh` | **Local UI**: Starts a lightweight HTTP server and statically serves the dashboard into your browser. |
| `backfill/fnspid.py` | Historical news backfill from HuggingFace (FNSPID). |
| `backfill/legacy_data.py` | Imports generic legacy TSV/CSV dumps into the unified layout. |
| `./run_tests.sh` | Orchestrates the `market_fetcher_test.py` and notebook validation tests. |
| `./zip_project.sh` | Packages code for easy Google Colab upload. |

---

## Data Structure (`market_data/`)

Organized generically by **Ticker** and **Topic**. View `DATA_SCHEMA.md` for detailed column specs.

### 1. Ticker Data (`/tickers/{TICKER}/`)
- `prices.tsv`: Daily OHLCV.
- `news.tsv`: Aggregated news (`Date, Source, Headline, Sentiment, URL, Summary`).
- `fundamentals.tsv`: Static company metrics.
- `earnings.tsv`: Dates, estimates.
- `financials_quarterly.tsv`: Balance sheet, income statement.

### 2. Topic/Macro Data
- `topics/{TOPIC}/news.tsv`: Thematic news ("AI", "Macro").
- `macro/economic_indicators.tsv`: FRED economic indicators.

---

## Reports

The pipeline includes a dedicated `reports/` directory designed for one off analysis.
- All analysis scripts can be executed at once via `./reports/run_all_report_scripts.sh`.
- Browse the `reports/` directory to examples.

### Analysis Capabilities & Metrics
The pipeline computes several advanced metrics natively during fetching and reporting:
- **Graham Intrinsic Value & EPS Growth**: Calculates a stock's intrinsic value based on trailing EPS, estimated annualized growth via log-linear regression, and the current 10-Year Treasury Yield.
- **Discount to Intrinsic Value**: Ranks tickers by how undervalued they are compared to their Graham Value.
- **Technical Indicators**: Calculates dynamic RSI, MACD, MA Crossovers, and Distance to 200MA.
- **Options IV Crush Risk**: Analyzes historical post-earnings volatility contraction.

### Generalized Utilities
- `reports/report_utils.py`: A shared module containing core mathematical functions (RSI, MACD) and plotting aesthetics, used by downstream scripts.
- `reports/portfolios/portfolio_processor.py`: Merges raw holding amounts with the newly fetched pipeline metrics and fundamental intrinsic values, producing comprehensive markdown tables.


After every standard fetch run, the system also generates generic data health reports in `market_data/`:
- **`STATS.md`**: Health check report (Root of `market_data/`).
  - Lists total count of news items.
  - **Macro Data Health**: Shows per-indicator valid row counts and date ranges.
  - **Missing Files**: Flags any missing core files or tickers with regular anomalies.
- **`SCHEMA.md`**: Snapshot of the current data schema (Root of `market_data/`).
- **`backfill_stats/FNSPID_STATS.md`**: Audit stats from the FNSPID backfill.

---

## Configuration
Edit `config.py` to modify:
- **`SECTORS`**: Groupings of tickers to fetch.
- **`NEWS_TOPICS`**: General search terms (e.g., "Geopolitics", "AI").
- **`FRED_SERIES`**: Macroeconomic indicators to track.
- **`DEFAULT_START_DATE`**: Start date for pricing data (Default: `2020-01-01`).
- **`ENABLE_ALPHA_VANTAGE`**: Master toggle for Alpha Vantage integration (Default: `True`).

---


## Development Notes

This project follows the **Google Python Style Guide** (2-space indent, strict typing).

Set up your own `.env` file with your Alpha Vantage API key and other settings, see `.env.example`.

```bash
# Run all style, type, and lint checks (yapf, isort, mypy, pylint)
./run_format.sh

# Run full test suite
./run_tests.sh
```

Install `pre-commit` hooks locally to auto-enforce these rules before every commit:
```bash
pre-commit install
```

---

### Workflow

### Environment Configuration
Code style is strictly replicated across environments via:
1. **VS Code**: `.vscode/settings.json` enables auto-formatting on save (`Cmd+S`).
2. **Pre-Commit**: `.pre-commit-config.yaml` is the local gatekeeper for `yapf`, `isort`, `mypy`, and `pylint`.
3. **CI Pipeline**: `.github/workflows/ci.yml` runs both `pre-commit` and `./run_tests.sh` on push to Gitea/GitHub to prevent validation drift.

*(Recommended VS Code Extensions: `Python`, `Pylint`, `Mypy Type Checker`, `isort`, `YAPF`)*

### Static Hosting (GitHub Pages)
The dashboard operates entirely serverless:
1. `./run_fetch.sh` ends by calling `market_dashboard_server.py --build` to generate `market_data/index.json`.
2. GitHub Pages natively serves `index.html` from the `main` branch.
3. The dashboard JS dynamically fetches `market_data/index.json` on load.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
Created by [Jake Garrison (jake-g)](https://github.com/jake-g).
