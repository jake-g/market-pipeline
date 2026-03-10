#!/usr/bin/env bash
# ==========================================
# Market Pipeline: NotebookLM CLI Examples
# ==========================================
# This script serves as a reference for the various ways
# to trigger the NotebookLM integration via `notebooklm_report.py`.
#
# Before running these, ensure you have authenticated:
#   $ notebooklm login
# ==========================================

# 1. Generate & Upload Daily Report (PDF)
# Synthesizes the last 24-48 hours of news and prices, creates a PDF,
# and uploads it to the "Market Reports" project.
python3 reports/notebooklm_report.py --mode daily

# 2. Generate & Upload Weekly Report (PDF)
# Requires strict bounds. Uploads a synthesized weekly PDF to "Market Reports".
python3 reports/notebooklm_report.py --mode weekly --start "2026-03-01" --end "2026-03-07"

# 3. Generate & Upload Monthly Report (PDF)
# Requires strict bounds. Uploads a synthesized monthly PDF to "Market Reports".
python3 reports/notebooklm_report.py --mode monthly --start "2026-02-01" --end "2026-02-28"

# 4. Upload All Rendered PDFs
# Mass uploads every `.pdf` found in `reports/rendered/` to the "Market Reports" project.
python3 reports/notebooklm_report.py --mode report_upload

# 5. Raw Data Feed Sync (Retrospective Push)
# Sweeps the `market_data/` directory for raw news TSVs and URL links.
# Scrapes the deep context of the URLs and uploads the raw text
# directly to the "Market Feed" project without rendering a final report.
# Maintains a `.notebooklm_last_sync.txt` state to only upload delta changes.
python3 reports/notebooklm_report.py --mode feed_upload

# 6. Generic Directory Upload
# Uploads all eligible files (.txt, .md, .pdf) from a specific target directory
# to the overarching "Market Reports" NotebookLM project.
python3 reports/notebooklm_report.py --mode upload --dir "/path/to/custom/folder"

# 7. List Active Projects
# Prints a tree of the currently authenticated NotebookLM user's projects and their source document counts.
python3 reports/notebooklm_report.py --mode list

# 8. Verify Project Uploads
# Explicitly lists all uploaded sources and their IDs for a specific project.
# Example usage to verify that "Market Reports" has the expected PDFs:
python3 reports/list_notebooklm_sources.py --project "Market Reports"
