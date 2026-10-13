# Changelog


> **Note**: For future roadmap and ideas, see `TODO.md`.

> **Note**: Newest on top. These versions map directly to the  `git tag` releases on the GitHub repository.

## [v1.11.1] - 2026-10-12
### NotebookLM Synthesis & Sync Overhaul (stub reports, 5-minute asks, prune order)
- **Root causes found**: (1) `chat.ask()` on a "write a report" prompt now triggers NotebookLM's agentic Studio-report generation — it either answers with a one-line *"published to your Studio panel"* confirmation or streams >256 MB and aborts; **21 saved reports since May were such stubs** (all of October). (2) `delete_conversation()` does not reset the notebook's *current* conversation, so every ask replayed a 200+-turn thread (~5 min each). (3) Source pruning sorted by `str(created_at)` (usually `None`) and **deleted the newest feeds first** — seen live pruning `2026-10-09 Daily Market Feed` seconds before asking for the weekly synthesis.
- **`notebooklm_client.py`**:
  - `synthesize_report()` — artifact-first: `artifacts.generate_report(CUSTOM, custom_prompt, source_ids)` → poll → `download_report()` → delete artifact (deterministic, ~3 min, 18 KB / 35 table rows for 09-30). Falls back to chat.
  - `ask_question()` — client-generated `conversation_id` (uuid4) for a genuinely fresh thread (14 s probe vs 5 min), `source_ids` scoping, stub validation via `looks_like_studio_stub()`, recovery from a Studio artifact, one inline-only retry.
  - Prune by `title_date()` (YYYY-MM-DD, MM-DD_, MM_MONTHLY) then `created_at`; `upload_file(prune=False)` for batch callers; `find_source_ids()` / `recent_feed_source_ids()` helpers.
- **`notebooklm_report.py`**:
  - Daily/weekly prompts rewritten: Regime Dashboard, **exact-% tables only** (no "Strong Rebound"), *Watchlist Check* for held/tracked names, falsifiable Forward Projection, shared `OUTPUT_RULES` (inline markdown only, cite everything) appended to every prompt incl. monthly/yearly/portfolio/earnings.
  - Synthesis scoped to the period's feed + quant summary + historical context + last 5 feeds; stub reports excluded from "Historical Context".
  - `sync-reports` is manifest-driven (`logs/.notebooklm_manifest_<project>.json`, sha256): unchanged PDFs skipped with zero RPCs, changed PDFs replace the stale source of the same title, duplicates collapsed, pruning once before the batch, 4-way parallel uploads.
- **`generate_periodic_reports.py`**: stub reports are detected, quarantined to `*.stub` (md + pdf) and regenerated; `--daily-start` flag, default window now 45 days (full sweep is opt-in).
- Tests: `test_prune_uses_title_date_when_created_at_missing`, `test_detects_stub_and_accepts_report`, `test_title_date`, `test_ask_question_recovers_from_studio_artifact`, `test_synthesize_report_prefers_artifact_api`.
- `notebooklm-py` upgraded 0.8.3 → 0.8.5.

## [v1.11.0] - 2026-10-12
### Data-Integrity Fixes (Prices & Portfolio Pipeline)
- **Price rows with empty `Close` no longer persist** (`market_fetcher.update_prices`):
  - Yahoo returns a `NaN` `Adj Close` for the current session; `Close = Adj Close` therefore wrote an empty Close for **273 tickers** on every same-day run, and the incremental check (`existing_max >= yesterday`) then never re-fetched the row (4 tickers carried permanent April gaps).
  - Fix: fall back to the raw `Close` when `Adj Close` is `NaN`, drop NaN-close rows before saving, and ignore them when computing `existing_max` so the next run re-downloads from the last *valid* close. Tests: `test_update_prices_nan_adj_close_falls_back_to_close`, `test_update_prices_refetches_row_with_empty_close`.
- **Portfolio technical enrichment was silently disabled** (`portfolio_processor.py`): `DATA_DIR` resolved to `<repo>/../market_data`, so no RSI/MA/Graham columns were ever appended to portfolio TSVs. Fixed to use `PROJECT_ROOT`; warns if the tickers dir is missing. Test: `test_processor_tickers_dir_is_inside_project`.
- **Active-account matching unified** via `yahoo_portfolio_fetcher.safe_portfolio_name()`:
  - `generate_portfolio_report.py` compared raw `.env` names (`Vanguard : INDIVIDUAL -8479`) against TSV stems (`vanguard__individual_8479`) → the **Active Trading Portfolios section was always empty** and the NotebookLM overlay was fed inactive accounts.
  - The fetcher used three different normalisations → active-account **CASH never reached `_combined_active_portfolio.tsv`**; two portfolios sharing a display name (`Wealthfront : BROKERAGE_CASH`) overwrote each other's TSV (now suffixed with the portfolio id).
  - Stale-file check in the report now hard-fails only for active accounts; `_combined_portfolio.tsv` is read from `portfolios/tsvs/`. Test: `test_safe_portfolio_name_matches_tsv_basename`.

## [v1.10.1] - 2026-10-05
### Yahoo Auth Refactor, Ticker Expansion & Test Hygiene
- **Yahoo Finance auth process rewritten** (`yahoo_portfolio_fetcher.py`, −400 lines net): simplified credential capture/refresh flow, `update_yahoo_creds.sh` aligned, and 76 lines of new tests in `test_portfolio_pipeline.py`.
- **Ticker & news expansion**: additional tickers in `config.py`; `backfill/historical_news.py` extended; `market_fetcher.py` learns the new symbols.
- **SKIP_EARNINGS fix**: newly added ETFs (DRAM, FIW, LIT, NASA, QTUM, SCHB, URNM) were not in `SKIP_EARNINGS`, causing needless earnings lookups; regression test added.
- **NotebookLM 0.7.x shim removed**: dropped the `_streaming_post` monkeypatch from `notebooklm_client.py` now that notebooklm-py ≥ 0.8.3 is required (fixes CI `ImportError`). Backfilled daily reports for 09-18, 09-23, 09-24, 09-25.
- **Quiet tests**: expected-warning paths in `market_fetcher_test.py` / `report_utils_test.py` now patch the logger and assert it was called instead of spamming `make test-unit` output; `test_fetch_fred_series_missing_key` no longer hits the live FRED API.

## [v1.10.0] - 2026-08-25
### Macro/Shipping Report Overhaul, Report Backups & `report_utils` Expansion
- **`generate_macro_reports.py` rewritten** (+458/−): shipping chokepoint panels, FRED tariff/freight series, Z-score and correlation views; follow-up polish to macro + periodic report code.
- **`report_utils.py` +234 lines / `report_utils_test.py` +258 lines**: new plotting and analysis helpers with the first dedicated unit-test module for report utilities; `make test-unit` now includes it.
- **Report backups**: `reports/backup_reports.py` + `make backup-reports` zips all intelligence reports after each fetch; previously git-ignored reports restored.
- **Periodic reports**: scraping performance optimised and retry resilience added in `generate_periodic_reports.py` / `notebooklm_report.py`; missing July–August daily/weekly/monthly reports generated.
- **Open-models strategy report** (`reports/08-22_strategy_open_models/analysis_open_models.py`, ~1.2k lines) and expanded AI ticker/topic config.
- Yahoo auth touch-up (+101 lines) with new tests.

## [v1.9.0] - 2026-08-08
### Automated Yahoo Credentials, CI Hardening & New Plots
- **Playwright-based Yahoo Finance credential capture** (`yahoo_portfolio_fetcher.py`, +221 lines): credentials are captured automatically instead of pasting `Copy as cURL`.
- **Semiconductor moat-watch plot** and dynamic titles for RSI scatter plots in `report_utils.py`.
- **CI / Python 3.13**: `PYTHONSAFEPATH` import-security fixes, absolute `PYTHONPATH` in the Makefile, sandboxed portfolio tests, hardened `make fetch` target, `.gitignore` and build-script clean-up.

## [v1.8.2] - 2026-07-14
### NotebookLM Fixes & Topic-Based News
- **NotebookLM**: auth check flow fixed (`--mode check_auth`, Makefile `test-auth`); PDF upload to the Market Reports notebook fixed.
- **Topic-based news feeds** added to `market_fetcher.py` (+212 lines) alongside new tickers in `config.py`; missing periodic reports regenerated.
- `make format` allowed to fail on the first (auto-fix) pass of `make fetch`.

## [v1.8.1] - 2026-07-11
### RSS News Caching Optimization & Warm Pipeline Speedup
- **Stage 6 Cached News Speedup**:
  - Implemented an early check for entry URL links in `seen_links` before performing regex cleanups, noise filtering, and TextBlob sentiment calculations.
  - Reduces per-ticker RSS cached processing time from ~20-30 seconds to **< 5 milliseconds** (a **5000x speedup** per ticker).
  - Stage 6 news cached step execution time across all 361 targets dropped from **1.5 hours** (or ~30 minutes of warm-cache CPU time) to **< 3 seconds**.
  - Warm Cache Run pipeline execution is now **~20 seconds** total.
- **AlphaVantage News Query Optimizations**:
  - Corrected a bug in `_fetch_alphavantage_news` where the raw comma-separated `config.ALPHA_VANTAGE_KEY` string was used directly, resulting in invalid API key errors. It now correctly uses the rotated `self._get_current_api_key()` key rotation engine.
  - Added a dedicated `CACHE_EXPIRY_AV_NEWS = 86400 * 14` (14 days) cache expiry parameter for slow-changing AlphaVantage news data, preventing redundant external API calls on every 4-hour cycle and avoiding request limit blocks.

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
