# Roadmap

> **Note**: For historical changes, see `CHANGELOG.md`.

### Git Release Workflow
The `HEAD` of this repository is currently live on version `v1.4.4`.

1. **Develop**: Commit iteratively on `dev-v1` (pushed to your private remote).
2. **Release**: Squash and tag onto `main`:
   ```bash
   git checkout --orphan main  # (Or `git branch -D main` if existing)
   git merge --squash dev-v1
   git commit -m "Release vX.X.X: Description"
   git tag -a vX.X.X -m "Official Release vX.X.X"
   git push origin main --tags
   ```
3. **Draft**: Use the pushed tag to draft an official GitHub Release.

---

## 🚨 Critical Priority


- [ ] **NVDA Earnings Review**: Follow up on NVDA earnings results, trade output, and lessons learned.
- [ ] **Missing Middle**: Data gap from July 2020 to October 2025.
    - *Impact*: ML models trained on this data will fail to understand the post-COVID bull run.
    - *Details*: FNSPID ends June 2020. Live RSS starts late 2025/early 2026.
    - *Action*: Backfill using AlphaVantage `NEWS_SENTIMENT`.
        - [x] Implement `fetch_historical_news` with monthly chunking (avoid 50-item limit truncation).
        - [x] Add "Key Rotation" support to handle 25 req/day limit if using free keys (or recommend Premium).
        - [x] Merge logic: Deduplicate by URL + Fuzzy Title Match.
        - [ ] **Run Backfill**: Ready to run via `backfill_historical_news.py` (Requires Premium Key).

- [ ] **Test AlphaVantage Premium Integration**:
    - [ ] Run a test utilizing an actual premium key to verify the monthly windowing logic and robust `NEWS_SENTIMENT` fetching.

## 🟡 Medium Priority

### Reporting & Portfolios
- [ ] **Portfolio Plans**: Come up with formalized reports and plans for each portfolio in `reports/portfolios/`.
- [ ] **Colab Integration**:
    - Upload `market_dashboard.ipynb` to Colab.
    - Test fetching the `market_data` library (or zip) and running the dashboard.
- [ ] **Missing Pre-2020 Price Data**:
    - Merge older price data pre 2020 into db (either from backfill lstm or going beyond 2020).

## 🔵 Low Priority / Future Ideas

### Data Pipeline (`market_fetcher.py`)
- [ ] **Add Pydantic**: Define strict schemas for `NewsItem`, `PriceRow`.
- [ ] **AsyncIO**: Switch to `aiohttp` for parallel fetching.
- [ ] **Config Loader**: Move tickers to `tickers.yaml` or `tickers.json`.
- [ ] **Database Migration**: Move to **DuckDB** or **SQLite** if TSV file I/O becomes a bottleneck (>500 tickers).
- [x] **Config Consolidation**: Centralize formatter args (`yapf`, `mypy`, `pylint`) inside `.pre-commit-config.yaml` to avoid project clutter (`.style.yapf`, `pyproject.toml`, `.mypy.ini`).

### Dashboard
- [x] **Static Hosting**: Generate `market_data/index.json` to allow `index.html` to run securely via GitHub Pages (Automatically ignores specific configuration files and precomputes line counts for rapid frontend logic).
- [ ] **Data Export**: Enable downloading current view as raw TSV or CSV directly.
- [ ] **Notebook Dashboard**: Finalize, clean up, and finish the legacy Jupyter notebook dashboard (`notebooks/market_dashboard.ipynb`), ensuring it mimics the HTML UI's parity.
- [ ] **Chart Exports**: Add an export button to securely download the Plotly charts as SVG or PNG locally.
- [x] **Analytics**: Integrated default Google Tag Manager placeholder ([Analytics Link](https://analytics.google.com/analytics/web/#/a385180260p525537369/reports/intelligenthome)).
- [x] **Real-Time Data**: Replace the `REFRESH` button with WebSockets or Server-Sent Events (SSE) to auto-update the file tree and plots instantly.
- [x] **Advanced Filtering**: Enable in-table searching to rapidly filter massive TSV datasets on the fly.
- [x] **Local Storage**: Save user preferences like `mp_pinned` inside the browser's `localStorage` to bookmark nested files.

### Infrastructure
- [ ] **Decoupled Visualization**: Abstract Plotly from UI core (`market_viz.py`).
- [x] **CI/CD Build**: Auto-Trigger `run_tests.sh` via GH Actions.

### Intelligence
- [ ] **FinLLMs**: Vector embeddings using models like FinBERT.
- [ ] **Natural Language Queries**: Interactively test trading strategies.
- [ ] **Market Forecasting**: Integrate multi-modal factors (e.g. Earnings call transcripts).

---

## ⚠️ Known Limitations (v1.4.0)

### 1. API & Data
- **AlphaVantage Free Tier**: Limited to 25 requests/day.
    - *Impact*: Historical backfill is impossible. Daily updates for >25 tickers will fail or need to be staggered.
- **Real-Time Data**: `yfinance` provides delayed data (15-20 mins).
    - *Impact*: Not suitable for high-frequency trading. Working as designed for daily analysis.

### 2. Backfill & History
- **2020-2025 News Gap**: Significant gap between FNSPID and current data.
    - *Cause*: Lack of free historical data sources.

### 3. Pipeline Logic
- **Deduplication Strictness**: Aggressive dedupe (0.85 threshold, window 50) might drop similar-but-distinct news.
    - *Status*: Monitoring needed.
- **Sentiment Precision**: Hybrid Scoring (TextBlob fallback) is less accurate than AlphaVantage's proprietary sentiment.
- **Serial Fetching**: `market_fetcher.py` fetches tickers serially (Slow for >100 tickers).

---

## ✅ Completed History (Newest First)

### v1.4.4 (NVDA Playbook & Dashboard Polish)
- [x] **NVDA Earnings Report Framework**: Delivered active Sympathy Beta matrices, RSI levels, and IV crush mechanics.
- [x] **Pristine Syntax Highlighting**: Injected `highlight.js` with Dual-Themes to auto-render GitHub-style python inside `index.html`.
- [x] **Responsive Image Scaling**: Bound massive Plotly generations to standard Viewport constraints.

### v1.4.3 (Public UI Push)
- [x] **Github Pages Delivery**: Engineered explicit server interception logic tying `index.html` seamlessly to `/market_data/index.json`.
- [x] **Library Publication**: Initial public push of the unified system (`market_fetcher.py`).

### v1.4.1 (Bug Fixes & Enhancements)
- [x] **Missing Financials & Fundamentals**:
    - [x] **Financials**: Fetch Quarterly Income, Balance Sheet, Cash Flow, Earnings.
        - *Fix*: Switch `financials_quarterly.tsv` from Transposed (Cols=Dates) to Row-based (Index=Date).
    - [x] **Fundamentals**: Fetch `OVERVIEW` (Market Cap, PE, ratios) into `fundamentals.tsv`.
    - [x] **Backfill**: Run one-off backfill for all tickers
- [x] **Fix Missing Sentiment/News**:
    - [x] **2026 Recent**: Fill the gap between the end of LSTM backfill and present day.
    - [x] **Pre-2022 (2020-2022)**: Backfill sentiment data for the period before LSTM data starts.
- [x] **Fix Missing Insider Data**:
    - [x] **Identify Failures**: LLY, LMT, MATX, SMCI, SO, UPS, VRT.
    - [x] **Solution**: Added `CIK_OVERRIDES` in `market_fetcher.py`.
- [x] **Evaluate Backfill Sources (2020-2025)**:
    - [x] Highlighted AlphaVantage Premium as the recommended solution.

### v1.4.0 (Unified Data Pipeline)
- [x] **New Data Sources**: AlphaVantage Sentiment, SEC Edgar, Hybrid Sentiment.
- [x] **Refactoring**: Split `market_fetcher.py`, Centralized Config, Joblib Caching.
- [x] **Testing**: Automated Notebook Test, Data Health Stats.
- [x] **Backfill**: `backfill_sentiment.py` for LSTM data.
- [x] **Documentation**: Consolidated README, CHANGELOG, and TODO.

### v1.3.x (Refactor & Testing)
- [x] **v1.3.1**: Local Notebook Testing with `kaleido`.
- [x] **v1.3.0**: **Major Refactor** - `market_data` library, TSV storage, FNSPID backfill.

### v1.2.0 (Monolithic Notebook)
- [x] **Macro Data**: FRED integration.
- [x] **Stable Baseline**: Final notebook-only version.

### v1.1.0 (Rendering & Visuals)
- [x] **Interactive Charts**: Plotly visualizations.
