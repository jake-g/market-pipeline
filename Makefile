# Makefile for market-pipeline
# Handles setup, testing, formatting, serving, and other utility tasks.

.PHONY: help setup format test test-unit test-auth server server-bg server-stop server-status fetch market-fetch shipping-fetch reports-macro portfolio portfolio-offline sync-news reports-periodic sync-reports dashboard-build yahoo-creds deploy-preview reports-historical notebooklm-auth backup-reports clean

PYTHON_BIN := $(shell which python3.11 2>/dev/null || which python3)
export PYTHONSAFEPATH := 1
export PYTHONPATH := $(CURDIR)


# Default target
help:
	@echo "========================================================="
	@echo "📈 Market Pipeline Management Console"
	@echo "========================================================="
	@echo "Available commands:"
	@echo "  make setup              - Set up virtual environment and install dependencies"
	@echo "  make format             - Format code using YAPF and run pre-commit checks"
	@echo "  make test-unit          - Run fast unit test suites (fail-fast pre-flight)"
	@echo "  make test               - Run all tests and generate static dashboard index"
	@echo "  make test-auth          - Verify Yahoo Finance and NotebookLM authentication status"
	@echo "  make fetch              - Run full daily market data pipeline & commit updates"
	@echo "  make market-fetch       - Run market fetcher stage (Prices, Financials, News)"
	@echo "  make shipping-fetch     - Run shipping & maritime chokepoint fetcher stage"
	@echo "  make reports-macro      - Generate macro economic indicator & shipping reports"
	@echo "  make portfolio          - Run portfolio synthesis pipeline (LIVE mode)"
	@echo "  make portfolio-offline  - Run portfolio synthesis pipeline (OFFLINE mode)"
	@echo "  make sync-news          - Upload daily market feed news archive to NotebookLM"
	@echo "  make reports-periodic   - Generate missing daily/weekly/monthly AI summary reports"
	@echo "  make sync-reports       - Upload all rendered PDF reports to NotebookLM"
	@echo "  make dashboard-build    - Generate static index.json for GitHub Pages dashboard"
	@echo "  make server             - Launch dashboard server in foreground (local mode)"
	@echo "  make server-bg          - Launch dashboard server in background"
	@echo "  make server-stop        - Stop background dashboard server"
	@echo "  make server-status      - Check background dashboard server status"
	@echo "  make yahoo-creds        - Interactive flow to update Yahoo Finance credentials"
	@echo "  make deploy-preview     - Create and push a temporary preview branch to GitHub"
	@echo "  make reports-historical - Generate historical weekly, monthly, and yearly reports"
	@echo "  make notebooklm-auth    - Clean stale profile locks and authenticate with NotebookLM"
	@echo "  make clean              - Clean up log files, pycache, and tool cache folders"
	@echo "========================================================="

# Setup environment
setup:
	@chmod +x run_env_setup.sh
	@./run_env_setup.sh

# Format code
format: setup
	@echo "🖌️  Forcing YAPF Python Formatting (2-space indent)..."
	@git ls-files '*.py' | xargs venv/bin/yapf -i --style="{based_on_style: google, indent_width: 2, column_limit: 80}"
	@echo "🛠️  Running full pre-commit validation suite..."
	@venv/bin/pre-commit run --all-files
	@echo "✅ All styling, typing, and formatting checks passed!"

# Run fast unit tests (fail-fast pre-flight)
test-unit: setup
	@echo "🧪 Running Fast Unit Tests..."
	@venv/bin/python3 -m unittest market_fetcher_test.py portfolios.test_portfolio_pipeline reports.report_utils_test

# Run tests
test: format
	@echo "🧪 Running Unit & Integration Tests..."
	@venv/bin/python3 -m unittest market_fetcher_test.py reports.report_utils_test
	@echo "📉 Running Market Fetcher Integration Test (Test Mode)..."
	@venv/bin/python3 market_fetcher.py --limit-tickers 3 --limit-topics 2 --news-days 3 --news-limit 3 2>&1 | tee logs/run_market_fetcher_test.log
	@echo "🧠 Running LSTM Backfill Integration Test..."
	@venv/bin/python3 -m unittest backfill/legacy_data_test.py
	@echo "📝 Running NotebookLM Client Tests..."
	@venv/bin/python3 reports/notebooklm_client.py 2>&1 | tee logs/test_notebooklm_client.log
	@PYTHONPATH=$(CURDIR) venv/bin/python3 -m unittest reports/notebooklm_client_test.py
	@PYTHONPATH=$(CURDIR) venv/bin/python3 -m unittest reports/report_utils_test.py
	@echo "🌐 Generating static index.json for dashboard..."
	@venv/bin/python3 market_dashboard_server.py --build 2>&1 | tee logs/generate_index.log
	@echo "🖌️  Running final formatting verification..."
	@venv/bin/pre-commit run --all-files
	@echo "✅ All Tests & Verifications Passed!"

# Verify authentication credentials status
test-auth: setup
	@echo "Checking Yahoo Finance Authentication..."
	@venv/bin/python3 -m portfolios.yahoo_portfolio_fetcher --check-auth
	@echo "Checking NotebookLM Authentication..."
	@venv/bin/python3 reports/notebooklm_report.py --mode check_auth

# Run server (foreground)
server: setup
	@echo "Git Status:"
	@git status -s
	@echo "Starting Market Pipeline Dashboard Server (Local Mode)..."
	@venv/bin/python3 market_dashboard_server.py --local

# Run server in background
server-bg: setup
	@echo "🚀 Starting dashboard server in background..."
	@mkdir -p logs
	@nohup venv/bin/python3 market_dashboard_server.py --local > logs/server.log 2>&1 &
	@sleep 1
	@pid=$$(pgrep -f "market_dashboard_server.py --local"); \
	if [ -n "$$pid" ]; then \
		echo $$pid > logs/server.pid; \
		echo "Dashboard server started with PID $$pid. Logs at logs/server.log"; \
	else \
		echo "🔴 Failed to start dashboard server. Check logs at logs/server.log"; \
	fi

# Stop background server
server-stop:
	@echo "🛑 Stopping dashboard server..."
	@pid=$$(pgrep -f "market_dashboard_server.py --local"); \
	if [ -n "$$pid" ]; then \
		kill $$pid && rm -f logs/server.pid; \
		echo "Server stopped (PID: $$pid)."; \
	else \
		echo "No running dashboard server found."; \
	fi

# Check status of background server
server-status:
	@pid=$$(pgrep -f "market_dashboard_server.py --local"); \
	if [ -n "$$pid" ]; then \
		echo "🟢 Dashboard server is running (PID: $$pid). Check logs at logs/server.log"; \
	else \
		echo "⚪ Dashboard server is not running."; \
	fi

# Run daily fetch pipeline
fetch:
	@echo "📅 Start Time: $$(date)"
	@mkdir -p logs
	@t_total_start=$$(date +%s); \
	$(MAKE) setup && \
	$(MAKE) test-auth && \
	$(MAKE) test-unit && \
	$(MAKE) market-fetch && \
	$(MAKE) shipping-fetch && \
	$(MAKE) reports-macro && \
	$(MAKE) portfolio && \
	$(MAKE) sync-news && \
	$(MAKE) reports-periodic && \
	$(MAKE) sync-reports && \
	$(MAKE) backup-reports && \
	$(MAKE) dashboard-build && \
	echo "🖌️  Pass 1: Auto-formatting code and applying pre-commit fixes..." && \
	($(MAKE) format || true) && \
	echo "🖌️  Pass 2: Strict verification of code formatting and pre-commit checks..." && \
	$(MAKE) format && \
	echo "🧪 Running unit tests post-fetch..." && \
	$(MAKE) test-unit && \
	echo "🎉 Full Pipeline Complete." && \
	echo "⏱️ Total Time: $$(($$(date +%s)-t_total_start))s." && \
	echo "💾 Committing newly generated market data..." && \
	(git add market_data/ || true) && \
	(git add reports/news/*.md || true) && \
	(git add -f reports/news/rendered/*.png || true) && \
	(git add market_data/index.json || true) && \
	(git commit -m "Auto-update market data: $$(date)" || echo "No new market data to commit.") && \
	(git push origin main || echo "No public changes to push or push failed.") && \
	echo "💾 Syncing private reports and data to Gitea..." && \
	$(MAKE) private-push


market-fetch: setup
	@echo "📉 Running Market Fetcher (All Tickers)..."
	@t_start=$$(date +%s); \
	venv/bin/python3 market_fetcher.py 2>&1 | tee logs/run_market_fetcher_full.log; \
	echo "⏱️  [Pipeline] Market Fetcher completed in $$(($$(date +%s)-t_start))s."

shipping-fetch: setup
	@echo "🚢 Running Shipping & Logistics Fetcher..."
	@t_start=$$(date +%s); \
	venv/bin/python3 shipping_fetcher.py 2>&1 | tee logs/run_shipping_fetcher.log; \
	echo "⏱️  [Pipeline] Shipping Fetcher completed in $$(($$(date +%s)-t_start))s."

reports-macro: setup
	@echo "🌍 Generating Macro & Shipping Reports..."
	@t_start=$$(date +%s); \
	venv/bin/python3 reports/generate_macro_reports.py 2>&1 | tee logs/generate_macro_reports.log; \
	echo "⏱️  [Pipeline] Macro & Shipping Reports completed in $$(($$(date +%s)-t_start))s."

sync-news: setup
	@echo "🗄️ Syncing Daily Aggregate News to NotebookLM Archive (Market Feed)..."
	@t_start=$$(date +%s); \
	venv/bin/python3 reports/notebooklm_report.py --mode feed_upload 2>&1 | tee logs/sync_notebooklm_archive.log; \
	echo "⏱️  [Pipeline] NotebookLM News Sync completed in $$(($$(date +%s)-t_start))s."

reports-periodic: setup
	@echo "🗂️ Generating Periodic Reports (Daily + Missing Weekly/Monthly)..."
	@t_start=$$(date +%s); \
	venv/bin/python3 reports/generate_periodic_reports.py 2>&1 | tee logs/generate_periodic_reports.log; \
	echo "⏱️  [Pipeline] Periodic Reports generation completed in $$(($$(date +%s)-t_start))s."

sync-reports: setup
	@echo "☁️ Syncing all rendered PDF reports to NotebookLM..."
	@t_start=$$(date +%s); \
	venv/bin/python3 reports/notebooklm_report.py --mode report_upload 2>&1 | tee logs/sync_notebooklm_reports.log; \
	echo "⏱️  [Pipeline] NotebookLM Reports Sync completed in $$(($$(date +%s)-t_start))s."

dashboard-build: setup
	@echo "🌐 Generating static index.json for dashboard..."
	@t_start=$$(date +%s); \
	venv/bin/python3 market_dashboard_server.py --build 2>&1 | tee logs/generate_index.log; \
	echo "⏱️  [Pipeline] Dashboard Build completed in $$(($$(date +%s)-t_start))s."

# Backup all market intelligence reports to a protected ZIP archive
backup-reports: setup
	@echo "📦 Creating ZIP backup of all reports..."
	@t_start=$$(date +%s); \
	venv/bin/python3 reports/backup_reports.py 2>&1 | tee logs/backup_reports.log; \
	echo "⏱️  [Pipeline] Reports Backup completed in $$(($$(date +%s)-t_start))s."

# Run portfolio pipeline (LIVE mode)
portfolio:
	@echo "📈 Running Portfolio Pipeline (LIVE mode)..."
	@./portfolios/run_portfolio_pipeline.sh

# Run portfolio pipeline (OFFLINE mode)
portfolio-offline:
	@echo "📈 Running Portfolio Pipeline (OFFLINE mode)..."
	@./portfolios/run_portfolio_pipeline.sh --offline

# Update Yahoo Finance credentials
yahoo-creds:
	@echo "🔐 Launching Yahoo Finance credentials update..."
	@./portfolios/update_yahoo_creds.sh

# Deploy temporary preview branch
deploy-preview:
	@echo "☁️  Deploying temporary reports preview branch..."
	@./deploy/create_tmp_branch.sh

# Generate historical reports
reports-historical:
	@echo "📅 Generating historical reports..."
	@./reports/generate_historical_reports.sh

# Authenticate with NotebookLM
notebooklm-auth:
	@echo "🧹 Cleaning up any locked Playwright or Chromium processes..."
	@-pkill -f "Google Chrome for Testing" || true
	@-pkill -f "Chromium" || true
	@LOCKFILE="$$HOME/.notebooklm/browser_profile/SingletonLock"; \
	if [ -f "$$LOCKFILE" ]; then \
		echo "🔓 Removing stale profile lock: $$LOCKFILE"; \
		rm -f "$$LOCKFILE"; \
	fi
	@echo "✅ Environment unlocked."
	@echo "🔐 Spawning NotebookLM login flow..."
	@venv/bin/notebooklm login

# Private Git Repository Management
PRIVATE_GIT := git --git-dir=.private_git --work-tree=.

private-status:
	@$(PRIVATE_GIT) status

private-add:
	@$(PRIVATE_GIT) add .
	@$(PRIVATE_GIT) add -f reports/ portfolios/ 2>/dev/null || true

private-commit: private-add
	@$(PRIVATE_GIT) commit -m "update private market data and reports" || true

private-push: private-commit
	@$(PRIVATE_GIT) push -u origin main

# Clean project caches and log files
clean:
	@echo "🧹 Cleaning up temporary files, caches, and logs..."
	@rm -f logs/*.log logs/*.pid logs/*.json
	@rm -rf __pycache__ portfolios/__pycache__ reports/__pycache__ apis/__pycache__ backfill/__pycache__ forks/__pycache__
	@rm -rf .mypy_cache .pytest_cache .pre-commit-config.yaml.cache
	@echo "Note: 'venv' virtual environment directory was not removed. Remove it manually with 'rm -rf venv' if desired."
