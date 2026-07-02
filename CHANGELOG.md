# Changelog


> **Note**: For future roadmap and ideas, see `TODO.md`.

> **Note**: Newest on top. These versions map directly to the  `git tag` releases on the GitHub repository.

## [v1.8.0] - 2026-07-02
### Pipeline Runtime Optimization (2h 13m → < 5 Min) & Macro/News Suite Expansion
- **Performance Benchmarks & Speedup (269 Tickers)**:
  - **Baseline (Unoptimized):** **2h 13m 45s** total pipeline runtime.
  - **Active Fetch Run (Uncached):** **6m 50s** (**6.5x speedup**; Stage 1 Macro: 9s, Stage 2 Prices: 42s, Stage 3 Fundamentals: 2m 29s, Stage 4 Financials: 1m 26s, Stage 5 Insider: 2m 24s).
  - **Warm Cache Run:** **10s total** (**800x speedup**; Stage 1 Macro: 0s, Stage 2 Prices: 1s, Stage 3 Fundamentals: 3s, Stage 4 Financials: 4s, Stage 5 Insider: 2s).
- **Core Bottleneck Fixes**:
  - **Cache Bypass Bug Fix**: Changed `if not data:` to `if data is None:` in `market_fetcher.py`, preventing cached empty responses `[]` (e.g. ETFs without quarterly statements) from triggering false cache misses and rate limits.
  - **Index Collision Fix**: Added `reset_index(drop=True)` before index-based deletion in `_fuzzy_deduplicate`, stopping pandas index collisions from dropping unrelated historical news rows.
  - **Headline Deduplication Scope**: Scoped exact title deduplication to `['Date', 'Headline']` to preserve legitimate recurring periodic updates on different dates.
- **Comprehensive 52-Column Macro Suite**: Expanded `economic_indicators.tsv` from 16 to **52 FRED indicators** covering Currencies (USD Index, USD/CNY, USD/EUR, USD/JPY), Energy/Grid (WTI Crude, Natural Gas, Copper, Electric Power Index), Science & R&D Investment (Gross Domestic R&D), Demographics & Health (US Birth Rate, Life Expectancy, Total Population), Wealth & Prosperity (Real Disposable Income, Household Net Worth, Credit Card Delinquency), Political Chaos & Policy Uncertainty (US Economic Policy Uncertainty, European EPU, Global EPU), and Systemic Stress (St. Louis & Kansas City Financial Stress Indices, Chicago Fed Activity Index).
- **Deep Historical Data Ranges**: Extended historical macro data back as far as **1913-01-01** (113+ years of continuous macro data across 21,600 rows).
- **Daily Forward-Filling**: Resolved macro data sparsity by forward-filling lower-frequency series across daily dates, ensuring non-null macro values for daily quantitative analysis.
- **News Ingestion & Full Pipeline Timing**:
  - **Full Market Fetch**: Processed 30 cached RSS topic feeds (6m 6s) and 331 live RSS feeds across 361 tickers + 92 topics.
  - **Total Pipeline Execution**: Completed full pipeline run in **5,244 seconds** (~1h 27m), populating news records across all 269 equities and ETFs while maintaining 100% deduplication integrity.
- **Full Makefile Pipeline Consolidation**: Migrated all daily pipeline orchestration, per-stage timing metrics, and git auto-commit steps directly into `Makefile` under `make fetch`, eliminating `run_fetch.sh` and ensuring virtualenv python execution across all stages.
- **Ambiguous Ticker Querying & Relevance Filter**: Mapped 48 short/generic tickers (`CAT`, `COP`, `ON`, `MS`, `V`, `HD`, `KO`, `GS`, `PG`, `TM`, `ZS`, `MU`, `GE`, `CF`, `BP`, `GD`, `BX`, etc.) to exact company stock search terms in Google News RSS (e.g. `COP` $\rightarrow$ `"ConocoPhillips stock"`). Implemented post-ingestion relevance filtering and purged **89,138 non-company noise headlines** from disk.
- **Shipping Chokepoint Fallback Fix**: Updated `gather_daily_metrics` in `shipping_fetcher.py` to carry forward last known valid vessel counts and congestion indices if live AISStream WebSocket sampling yields 0 messages, preventing zero-drop gaps in `chokepoint_metrics.tsv`.
- **Automated Macro & Shipping Reports**: Created `reports/generate_macro_reports.py` to parse the newly expanded macroeconomic indicators and the shipping chokepoint/tariff data into robust daily markdown and PDF reports (`MACRO_REPORT.md` and `SHIPPING_REPORT.md`).
  - Added 1-Year and 5-Year timeline plots, Z-score normalized correlation matrices, and 1-Yr/1-Mo variation tables.
  - Implemented automated **Anomaly Detection** alerting on sudden 1-day spikes (>15%) and extreme data staleness (>365 days).
  - Included raw text generation for top positive and inverse correlations to ensure insights are easily accessible inside NotebookLM context without parsing the images.
  - Routed generated reports to `reports/news/` and their images to `reports/news/rendered/` to avoid cluttering the parent reports directory and cleanly bypass strict gitignores.
  - Integrated these generation steps directly into `run_fetch.sh` for continuous NotebookLM sync.
- **Portfolio Analytics Upgrades**: Injected an **Anomaly Alerts** engine into `PORTFOLIO_REPORT.md` to flag massive daily stock swings (>10%) and severely overvalued holdings (< -40% intrinsic discount) alongside automated PDF rendering.

## [v1.7.0] - 2026-06-29
### Pipeline Optimization & Interactive Auth
- **Yahoo Finance Auth**: Added interactive TTY credential recovery flow (`prompt_for_curl_and_save_env`) to recover stale sessions inline without exiting the pipeline.
- **AlphaVantage Caching**: Implemented a **30-day** cache expiry for slow-changing AlphaVantage data (Overview and Financials), keeping Yahoo Finance data on a 24-hour cycle. This preserves the rich dataset while eliminating 40+ minutes of daily API overhead.
- **Parallel RSS News**: Refactored news fetching to use a `ThreadPoolExecutor` with 8 workers, staggered random delays to prevent IP bans, and a cache pre-check, reducing news ingestion time from 1.5 hours to under 2 minutes.
- **Pipeline Timing**: Added stage-level timers and logging to `run_fetch.sh`, `market_fetcher.py`, and `shipping_fetcher.py` for precise runtime tracking.
- **Bug Fixes**: Resolved a pylint `redefined-outer-name` warning in `shipping_fetcher.py`.

## [v1.6.0] - 2026-03-17
### Shipping Data Enhancements & Global Logistics Tracking
- **Shipping & Tariff APIs**: Added dedicated shipping fetch code (`shipping_fetcher.py`) to pull tariff and maritime chokepoint metrics (`chokepoint_metrics.tsv`, `tariffs.tsv`, `shipping_macro.tsv`).
- **FRED API Integration**: Added `FRED_API_KEY` to support enhanced FRED macro data fetching. (TODO: Expand usage of this API for broader macroeconomic indicators).
- **Testing**: Added robust asynchronous test mocking to support testing shipping and FRED data generation processes.
- **Documentation**: Improved API documentation within the `api/` folder.

## [v1.5.1] - 2026-03-12
### Periodic Report Infrastructure & Historical Backfill
- **Fully Bounded Synthesis Contexts**: Eliminated duplicate periodic report hallucination across timeframes. `notebooklm_report.py` now mounts tightly-scoped, temporary Google NotebookLM projects specific to the generation period (e.g. only uploading one week of data at a time for weekly reports).
- **Deep Historical Scraping**: Built robust web history fetching mechanism (`backfill_historical_data.py`) querying DuckDuckGo to extract broad technological and macroeconomic summaries for years 2018-2025.
- **Recursive Generation Hierarchy**: Periodic generation commands explicitly upload preceding/smaller reports into the NotebookLM context window (e.g., monthlies embed weeklies) to compound quantitative fidelity upwards securely.
- **2026 Prospective Generation**: Added a `--only-prospective` pipeline sweep leveraging historical context to project forward-looking institutional insights.
- **Clean Output Architecture**: All intermediate Markdown generation is now isolated strictly to `reports/news/` while final scaled PDFs output uniformly into `reports/rendered/`.

## [v1.5.0] - 2026-03-10
### Agentic NotebookLM Integration
- **Unified Pipeline (`notebooklm_report.py`)**: Centralized CLI for generating daily, weekly, monthly, and yearly insights via Google NotebookLM, with segregated ingestion targets ("Market Reports" and "Market Feed").
- **Smart Deduplication & Historical Context**: Overhauled the `report_upload` and `feed_upload` sync engines to explicitly deduplicate overlapping PDFs and TSVs in-place before uploading. The synthesis engine now automatically scans local directories for recent historical reports and injects them back into the LLM context to ensure longitudinal memory.
- **AI Summarization & RAG**: Built dynamic engine to stream topic-specific news into a temporary LLM context, outputting a holistic `AI_THEMES.md` analysis. This thematic overview and custom tactical AI RAG overlays are now natively injected into daily/weekly Markdown reports and portfolio preambles.
- **PDF Rendering & Formatting**: Built a fully Python-native `weasyprint` rendering engine into `report_utils.py` to embed local charts into PDFs before upload. Hardened all prompts with strict formatting instructions (Markdown Tables, bulleted points, chronical timelines, explicit `## References`).
- **API Notice**: Google updated backend APIs (March 10), breaking the `notebooklm-py` automated PDF upload RPC. Text/Markdown generation (`feed_upload`) remains fully functional.

### Advanced Tactical Reporting
- **Bespoke Portfolio Generators**: Replaced generic wrapper logic with 4 dedicated scripts for specific portfolio constraints (Schwab 351, Vanguard 7991, Vanguard Roth IRA 6381, Combined Active Geopolitics).
- **Visual Context & Logic**: Hardcoded detailed Graphviz decision tree topologies mapping out macro responses. Report aesthetics now embed specific `## Visual Context` blocks showcasing Theme Exposure and PnL.
- **Reporting Enhancements**: Finalized Oracle (ORCL) earnings report layout and updated portfolio outputs to natively print intrinsic values mapping.

### Intelligent Market Fetching
- **Dynamic News Filtering**: Completely decoupled `build_daily_news_digest` from hardcoded topics. Now dynamically pulls from config, deduplicates similar headlines using `difflib` fuzzy matching, and explicitly injects Alpha Vantage `Summary` data as actionable bullets.
- **Historical Deep Backfill**: Created `backfill/topic_news.py` for 2018-2025 recursive topic crawling via Google News. Built deeply integrated reverse-chunking logic and bypassed the native `yfinance` limit to natively unlock 40 years of earnings data ingestion without external rate-limited APIs.
- **Fixes**: Fixed a `yfinance` header request crash by adding `fake_useragent` and patched duplicate TSV joining bugs when pulling combined portfolio aggregates natively.

## [v1.4.6] - 2026-03-02
### Features & Architecture
- **Dashboard & Local DX**:
    - Added `--local` flag to `market_dashboard_server.py` and `run_server.sh` to dynamically bypass `.gitignore` filters, enabling full local navigation of private directories (e.g. `portfolios/`).
- **Reporting & Privacy Framework**:
    - Engineered `privacy_mode` within `report_utils.py` and `build_standard_portfolio_report` to dynamically toggle raw cash values/balances into anonymized relative portfolio percentages for public-facing examples.
    - Updated `reports/.gitignore` with structured exceptions (`!03-02_combined_active.../`) to allow sharing polished examples safely.
- **New Portfolio Reporting Pipeline**:
    - Complete ground-up creation of an automated portfolio processing ecosystem (`yahoo_portfolio_fetcher.py`, `portfolio_processor.py`, and `generate_portfolio_report.py`).
    - Added comprehensive unit testing coverage through the newly created `test_portfolio_pipeline.py`.
    - Centralized automation into `reports/portfolios/run_pipeline.sh` executing unit tests, formatting, fetcher logic, metrics augmentation, and dynamic Markdown rendering.
    - Script outputs piped strictly into `reports/portfolios/logs/`.
- **API Evasion (Yahoo Finance)**:
    - Bypassed global `429 Client Error` blockades by migrating from `requests` to `curl_cffi` to natively spoof Chrome TLS fingerprints.
    - Moved authentication credentials securely out of python files into an untracked `reports/portfolios/.env`.
- **Data Footprint Consolidation**:
    - Extracted all portfolio outputs (raw files, combined matrices, and active-only groupings) strictly into `reports/portfolios/tsvs/`.
    - Eliminated obsolete `*_metrics.tsv` redundancy by natively merging metrics upstream to original files.
- **Reporting Enhancements**:
    - Designed `reports/portfolios/REPORT.md` to split portfolios explicitly into *Active Trading* vs *Set & Forget*

## [v1.4.5] - 2026-02-25
### Features & Architecture
- **Script Automation & Centralization**:
    - Created `reports/run_all_report_scripts.sh` to provide a single entrypoint for sequentially regenerating all reports.
    - Abstracted discrete quantitative, reporting, and plotting methods out of individual report generator scripts into a single `reports/report_utils.py` library.
    - Updated NVDA and Growth Portfolio reports with latest market data and standardized Graphviz decision tree visuals.
- **Reporting Enhancements**:
    - **Intrinsic Value Screener**: Adopted intrinsic value concepts to calculate Graham Intrinsic Value, normalized EPS growth, and theoretical discount. Added `reports/intrinsic_value_analysis/intrinsic_value_report.py` outputting a scatter plot against EPS Surprises.
    - Merged `intrinsic_value_screener.py` logic natively into the report script to consolidate actionable analytics.
    - Updated `reports/portfolios/portfolio_processor.py` to natively print intrinsic values mapping to current holdings.
    - Fixed NaN issues within Intrinsic Value outputs by lowering log-linear regression bounds in `market_fetcher.py`.
    - Replaced absolute dollar amounts with relative percentages in `growth_portfolio_plan.py` (privacy).
- **API Performance Enhancements (`market_fetcher.py`)**:
    - Fixed a bug where AlphaVantage payloads would not leverage local `.cache/` data when requesting missing values. Implemented robust intercept logic validating cache freshness.
    - Added "Broad Market & Intl ETFs" sector to `config.py` and successfully fetched corresponding asset data.

## [v1.4.4] - 2026-02-24
### Features
- **NVDA Q4 Earnings Playbook (`reports/2026-02-25_NVDA_earnings_trade/`)**:
    - Executable playbook for Q4 2026 based on 2-year historical data.
    - Integrated structural metrics: Sympathy Beta matrices (AMD/MU/TSM), 200-SMA distances, and active RSI mapping.
    - Evaluated historical IV crush and "gap-trap" fade mechanics vs pre-earnings FOMO.
    - `nvda_trade_analysis.py` dynamically refreshes report targets with real-time terminal endpoints.
- **Dashboard UI Refinements (`index.html`)**:
    - **Syntax Highlighting**: Python (`.py`) scripts now render with Github-style syntax formatting via `highlight.js`.
    - **Dual Themes**: Syntax colors dynamically switch on Dark/Light mode toggle.
    - **Rendering Fix**: Patched `marked.js` API type-errors for image-heavy documents.

## [v1.4.3] - 2026-02-21
### Refactoring
- **Static Hosting (GH Pages)**:
    - `index.html` automatically loads `market_data/index.json`.
    - `market_dashboard_server.py` dynamically intercepts `/market_data/index.json` requests locally.
    - Added `--build` flag to `market_dashboard_server.py` to generate `market_data/index.json` during `./run_fetch.sh`.
- **Market Data UI**: Standalone HTML/CSS/JS dashboard.
    - Updated cleanly to a Brutalist Light Mode aesthetic with Purple Accents (`#9333ea`).
    - **Interactivity**:
        - *Pinned Favorites*: `localStorage` caching to pin nested metrics (clean `PIN`/`PINNED` text toggles in header).
        - *In-Table Filtering*: Regex-based dynamic TSV search.
        - *Keyboard Navigation*: File tree traversal via `ArrowUp`, `ArrowDown`, `Space`.
        - *Resizable Layouts*: Draggable sidebar.
        - *One-Click Plotting*: Overlaid timeseries plots (SMA/EMA) auto-mapping all numeric Y-Axes on click, toggleable via Legend.
    - **Structure**:
        - Auto-expands `market_data` folder and loads `STATS.md` on startup.
        - Concise Header Title ("Market Data") alongside explicit "VIEW ON GITHUB" and WIP "OPEN IN COLAB" buttons.
        - Precomputes file line counts on the server via `index.json` for instant UI rendering.
    - **Analytics**: Pre-configured Google Analytics tracking ([View Dashboard](https://analytics.google.com/analytics/web/#/a385180260p525537369/reports/intelligenthome)).
- **Standalone API**: `market_dashboard_server.py` scans `market_pipeline` securely.
    - Explicit server exclusion overrides (ignores `TODO.md`, `requirements.txt`, `index.json`, `alpha_vantage_api`).
- **Workflow Utilities**:
    - `run_server.sh`: Launches server, prints git status, opens browser.
    - `run_format.sh`: Trigger `yapf`, `isort`, `mypy`, `pylint`.
- **Directory Architecture**:
    - Extracted backfill scripts into `backfill/`.
    - Extracted notebooks into `notebooks/`.
    - Flattened validations directly into `.pre-commit-config.yaml` (`mypy`, `pylint`, `yapf`, `isort`).
- **Continuous Integration (CI)**:
    - Added GitHub Actions/Gitea Actions `.github/workflows/ci.yml` pipeline to automatically execute `pre-commit run --all-files` and `./run_tests.sh` across Ubuntu boxes per push.

## [v1.4.2] - 2026-02-21
### Refactoring
- **Historical Backfill**: Implemented `fetch_historical_news_premium` (renamed from `fetch_historical_news`) with weekly windowing to bypass the 1000-item API limit.
- **Financials Expansion**:
    - Added `update_financials` to fetch Income, Balance Sheet, Cash Flow, and Earnings.
    - Switched storage to **Row-Based** `financials_quarterly.tsv` (Index=Date) for scalable appending.
- **Fundamentals**: Added `update_fundamentals` to capture Company Overview (Market Cap, PE, etc.) in `fundamentals.tsv`.
- **Configuration**:
    - Added `ENABLE_ALPHA_VANTAGE` flag to `config.py` as a master switch.
    - Renamed `include_av` to `include_alphavantage` across the codebase for clarity.
- **Infrastructure**:
    - Created `backfill_historical_news.py` CLI for targeted backfills (updated to use new flag).


## [v1.4.1] - 2026-02-20
### Fixes
- **Data Stats**: `STATS.md` enumerates missing core files dynamically via `SKIP_lists`.
- **Legacy Migrations**: `backfill_sentiment.py` -> `backfill_legacy_data.py`.
- **Insider Backfill**: Imports `/insiderBuying` CSVs into `insider_trading.tsv` via date deduplication.
- **Fixes**:
    - Configured API Key Rotation in `config.py` (Currently Single-Key default).
    - Hardcoded SEC CIK overrides for `LLY`, `LMT`, `MATX`, `SMCI`, `SO`, `UPS`, `VRT`.
    - Purged broken `backfill_spy_vix` imports.
    - Pointed `run_tests.sh` strictly to `backfill_legacy_data_test.py`.
- **Macro Expansion**:
    - Shifted `config.DEFAULT_START_DATE` to **2018-01-01** capturing pre-COVID data.
    - Detects time gaps and automatically refetches history via `MarketFetcher`.



## [v1.4.0] - 2026-02-18
### Major Release: Unified Data Pipeline
Consolidated fetching APIs onto an automated standard. TSV-centric schema optimized for Git storage.

### Added
- **AlphaVantage News Sentiment**: Rich metadata integration via `update_alphavantage_sentiment`.
- **SEC Edgar Form 4s**: Native fetching for Insider Trading via `sec-edgar-downloader`.
- **NLP Fallback**: Automated `TextBlob` sentiment classification (-1.0 to 1.0) for standard RSS.
- **CI Data Audits**:
    - Programmatic `market_dashboard.ipynb` evaluation via `test_notebook.py`.
    - Automated Health Metric generation (`market_data/STATS.md`).
- **Targeted Backfills**:
    - `backfill_fnspid.py`: Mass history (2010-2020).
    - `backfill_lstm_data.py`: Rehydrates `news_sentiment.tsv` from ML outputs, interpolating `NaN` constraints for modern continuity to present day.
- **API Cache**: Intercepts AlphaVantage and rate-limited calls with `joblib` memory (4-hour TTL).
- **Automated Validation**: `run_tests.sh` unifies unit (`market_fetcher_test.py`) and integration tests.

### Changed
- **Sort Stability**: Strict `Date (Desc) -> Sentiment (Desc) -> Headline (Asc)` news enforcement.
- **Modular Data Class**: `update_prices`, `update_fundamentals`, `update_macro`.
- **Deduplication**: Strict fuzzy 0.85 tolerance spanning a 50-row window (Keeps Best Quality via Sentiment > Source > Length).
- **Rounding Accuracy**: Enforces 3-decimal (Sentiment) and 2-decimal (Insider Trading).
- Restored explicit `config.py` definitions (Indices & Futures: `^GSPC`, `CL=F`).

### Fixed
- **Legacy Removal**: Removed deprecated schema checking logic and unused "Seeking Alpha" feed placeholders.
- **Path Handling**: Fixed various relative path issues by using `pathlib.Path` throughout `MarketFetcher`.
`update_alphavantage_sentiment`.
- **Notebook Logic**: Updated `market_dashboard.ipynb` to use `MarketFetcher` directly for data fetching and disk loading, ensuring consistency with the pipeline.


## [v1.3.1] - 2026-02-17
### Added
- **Local Notebook Testing**: `run_notebook.sh` now executes `market_dashboard.ipynb` headlessly.
  - **Consolidated Reports**: Generates `notebook_outputs/market_dashboard_report.md` capturing all cell outputs.
  - **Static Plots**: Saves Plotly figures as `.png` in `notebook_outputs/plots/` using `kaleido`.
- **Refactored Backfill**: Moved `backfill_benzinga_history` to `backfill_fnspid.py` for better modularity.

### Changed
- **Output Directory**: Local test artifacts are now saved to `notebook_outputs/` instead of `notebooks/plots`.
- **Dependencies**: Added `kaleido` requirement for static image export.

### Fixed
- **Notebook Execution**: Resolved `NameError` for `render_news_table` and plotting functions by injecting them into the notebook execution flow.
- **Pandas Styling**: Fixed `JinJa2` dependency issue for DataFrame styling.

## [v1.3.0] - 2026-02-17
**Refactored Market Data Library & Centralized Configuration**

### Major Changes
- **New Library (`market_data/`)**: All data fetching logic (Prices, Fundamentals, News, Macro) has been moved to `market_fetcher.py`.
- **Centralized Config (`config.py`)**:
    - `MACRO_ASSETS`, `SECTORS`, and `FRED_SERIES` are now single-source-of-truth.
    - Cache settings (`.cache/`) and data paths (`market_data/`) are configurable.
- **Improved Data Storage**:
    - Data is now saved as **TSV** files in `market_data/tickers/` and `market_data/macro/` for easy audit and interoperability.
    - `SCHEMA.md` and `STATS.md` are automatically generated to document data health.
- **Notebook Improvements (`Market_Dashboard.ipynb`)**:
    - **Simplified**: Fetching logic is reduced to a single function call `fetch_data_v3`.
    - **Robustness**: Uses `MarketFetcher` class which handles caching, rate limits (yfinance), and error logging automatically.
    - **Documentation**: Displays `market_data/SCHEMA.md` inline at startup.
- **Backfill Capabilities**: Added support for backfilling historical news from FNSPID (Benzinga) for 2010-2020.

### Known Issues
- **Missing Middle**: Data gap from July 2020 to October 2025.
    - *Impact*: ML models trained on this data will fail to understand the post-COVID bull run.
    - *Plan*: Evaluate FMP API or Hugging Face datasets to fill this gap.

## [v1.2.9] - 2026-02-16
*Draft: "Market Backfill and Class Ideas"*
- Initial exploration of Class-based fetching.
- Prototyped `MarketFetcher` class.
- Tested efficient storage methods (TSV vs Parquet - settled on TSV for transparency).
- [Colab Link](https://colab.research.google.com/drive/1lg1xs56yRsOv-S9d27itWPvPZ4SHOT3c?usp=sharing)

## [v1.2.0] - 2026-02-16
**Final Monolithic Notebook**
- **Pinned Version**: The stable version before library refactor.
- Added comprehensive Macro/FRED data integration.
- [Colab Link](https://colab.research.google.com/drive/1CWZwjjNgdZmh1tKjoCZN2ERqywuas4Hz#scrollTo=Q2IVC4NkYZ1R)

### Revisions
- **Feb 16, 2026**: v2 final for lib.
- **Feb 13, 2026**: Pinned version.
- **Feb 12, 2026**: v2 macro data added.
- **Feb 12, 2026**: v1.5 wip.

## [v1.1.0] - 2026-02-03
**Rendering & Visuals**
- Added Plotly interactive charts.
- Implemented "Risk vs Reward" scatter plot.

## [v1.0.0] - 2026-02-02
**Initial Prototype**
- Basic yfinance fetching.
- Simple dataframe display.



The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
