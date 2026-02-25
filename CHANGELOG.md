# Changelog


> **Note**: For future roadmap and ideas, see `TODO.md`.

> **Note**: Newest on top. These versions map directly to the  `git tag` releases on the GitHub repository.

## [v1.4.4] - 2026-02-24
### Features
- **NVDA Q4 Earnings Playbook (`reports/2026-02-24_NVDA_earnings_trade/`)**:
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
