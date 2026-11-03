#!/usr/bin/env python3
# pylint: disable=duplicate-code
"""Generates the NotebookLM red-team critique for the 11-02 public report.

Uploads the finished REPORT.md to a temporary NotebookLM project, requests an
institutional red-team critique referencing the three decision trees, writes
the result to ``notebooklm_critique.md``, and deletes the temporary project.
Re-run ``analyze_11_02.py`` afterwards to embed the critique in the report.
"""

import asyncio
import datetime
import logging
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
for _p in (PROJECT_ROOT, os.path.join(PROJECT_ROOT, "reports")):
  if _p not in sys.path:
    sys.path.insert(0, _p)

# pylint: disable=wrong-import-position
from reports.notebooklm_client import MarketNewsClient
from reports.notebooklm_report import OUTPUT_RULES
from reports.report_utils import clean_md

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REPORT_PATH = os.path.join(SCRIPT_DIR, "REPORT.md")
OUT_PATH = os.path.join(SCRIPT_DIR, "notebooklm_critique.md")
PROJECT_NAME = "Market Pipeline: 11-02 Public Strategy Red-Team"

PROMPT = (
    """You are a Senior Macroeconomic Strategist and Institutional Portfolio Risk Officer. You have been given the full text of the **November 2, 2026 Public Market Strategy & Institutional Model Portfolio — Semiconductor & Hyperscaler Air-Pocket Edition**, which evaluates an anonymized 80% Core / 20% Tactical model portfolio across three decision trees (a 5-Pillar Tactical Sleeve tree with the Capitulation Exception on Friday Weekly-Close Watch, a 3-Gate Core Ballast tree, and a 5-tranche Fresh-Capital Deployment tree), a Trigger Scorecard, six hypotheses with contrarian alternatives, and Scenarios A–E.

Write an independent RED-TEAM CRITIQUE of this strategy. Be specific and quantitative; cite the report's own numbers (percent weights, RSI, distance to 200DMA, 10Y, HY spread, WTI) when you make a point.

Structure (use these exact Markdown headers):
## Verdict
One paragraph: is placing the Capitulation Exception on Friday Weekly-Close Watch after SOXX fell -3.79% today to -4.81% vs 200DMA (while SMH is -2.26%, NVDA is -1.03%, TSM is -0.08% vs 200DMA) and holding GOOG (RSI 12.7) / META (RSI 8.2) defensible?
## 1. Where the Trees Could Be Wrong
Three to five numbered objections. For each: the tree node you are attacking, the data that would prove it wrong, and what you would change (a threshold, a vehicle, a sequence).
## 2. Fresh-Capital Plan Stress Test
Evaluate the T1–T5 schedule: splitting T1 into Core Now (10%) and Tactical Thursday (10% post-Midterms + AMD/ANET), disqualifying MRVL (-12.7% today, -6.6% vs 200DMA), tax-wrapper routing, and the half-core / half-tactical structure. Name the single biggest flaw and a concrete fix.
## 3. Hypotheses & Alternative Theories
Which of H1–H6 is weakest? Offer at least one alternative hypothesis the report did not consider, with an observable that would confirm it.
## 4. Look-Through Factor & Execution Risk
Audit look-through AI/Tech concentration across the 20% Tactical Sleeve and the 80% Core Ballast (VUG 15.2%, VGT 7.8%) plus pre-print binary execution risk around AAPL, AMD, ANET, and NVDA.
## 5. What I Would Do Differently This Week
A terse, numbered list of concrete actions (percent of model book or percent of fresh capital only — never dollars).

CRITICAL RULES:
1. MAX 60 words per paragraph. Terse bullets. No fluff, no generic disclaimers.
2. Never mention dollar balances; use the percentages in the report.
3. Do NOT suggest options, puts, calls, leverage or margin.
4. Refer to the decision trees by name and node (e.g. 'Pillar 1B-iii', 'Gate 1', 'T1').
5. End with a numbered '## References' list mapping any citations to the report section titles you relied on."""
    + OUTPUT_RULES)


async def main() -> None:
  """Runs the red-team synthesis and writes notebooklm_critique.md."""
  if not os.path.exists(REPORT_PATH):
    raise FileNotFoundError(REPORT_PATH)
  with open(REPORT_PATH, "r", encoding="utf-8") as f:
    report_md = f.read()
  head, sep, _ = report_md.partition(
      "## 🤖 SECTION 4: SENIOR STRATEGIST RED-TEAM CRITIQUE")
  body = head if sep else report_md

  async with MarketNewsClient(project_name=PROJECT_NAME) as db:
    await db.connect()
    await db.clear_sources()
    await db.upload_news_text(body, title="11-02 Public Model Strategy Report")
    logger.info("Requesting red-team synthesis...")
    try:
      text = await db.synthesize_report(
          PROMPT, required_markers=["## Verdict", "## References"])
    finally:
      try:
        await db.delete_project()
      except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Could not delete temp project: %s", exc)
  if not text or len(text.strip()) < 300:
    raise RuntimeError("Empty or stub critique returned; not writing file.")
  stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
  out = (f"*NotebookLM red-team synthesis generated {stamp} from the finished "
         "11-02 public strategy report text.*\n\n" + text.strip())
  with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(clean_md(out))
  logger.info("✅ Wrote %s (%d chars)", OUT_PATH, len(out))


if __name__ == "__main__":
  asyncio.run(main())
