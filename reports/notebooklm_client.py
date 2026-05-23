import asyncio
import logging
import os
from typing import List, Optional

from notebooklm import NotebookLMClient

logger = logging.getLogger(__name__)

NOTEBOOK_NAME = "Market News DB"


class MarketNewsClient:
  """Wrapper around NotebookLMClient to manage an overarching market news notebook."""

  def __init__(self,
               project_name: str = "Market News DB",
               test_mode: bool = False):
    self.notebook_id: Optional[str] = None
    self.client = None
    self.notebook_name = f"TEST {project_name}" if test_mode else project_name

  async def __aenter__(self):
    self.client = await NotebookLMClient.from_storage()
    await self.client.__aenter__()
    return self

  async def __aexit__(self, exc_type, exc_val, exc_tb):
    if self.client:
      await self.client.__aexit__(exc_type, exc_val, exc_tb)

  async def connect(self):
    """Establishes connection to NotebookLM and finds or creates the target notebook."""
    if not self.client:
      raise ValueError(
          "MarketNewsDB must be used as an async context manager (async with MarketNewsDB() as db)."
      )

    try:
      notebooks = await self.client.notebooks.list()

      # Find existing notebook
      for nb in notebooks:
        if nb.title == self.notebook_name:
          self.notebook_id = nb.id
          logger.info("Found existing NotebookLM database: %s (ID: %s)",
                      self.notebook_name, self.notebook_id)
          break

      # Create if not found
      if not self.notebook_id:
        logger.info("Creating new NotebookLM database: %s", self.notebook_name)
        nb = await self.client.notebooks.create(title=self.notebook_name)
        self.notebook_id = nb.id

      # Automatically sync yearly/monthly reports for primary folders
      if self.notebook_name in ("Market Feed", "Market Reports"):
        await self.sync_yearly_monthly_reports()

    except Exception as e:
      logger.error("Failed to connect to NotebookLM: %s", e)
      raise

  async def sync_yearly_monthly_reports(self):
    """Finds any yearly/monthly reports locally and uploads if missing."""
    client = self.client
    if (not self.notebook_id or client is None or
        not hasattr(client, "sources")):
      return

    try:
      # 1. List all sources currently in the notebook
      sources = await client.sources.list(self.notebook_id)
      uploaded_titles = {getattr(src, "title", "") for src in sources}

      # 2. Locate local yearly/monthly reports in rendered/
      reports_dir = os.path.dirname(os.path.abspath(__file__))
      rendered_dir = os.path.join(reports_dir, "rendered")
      if not os.path.exists(rendered_dir):
        return

      for file in os.listdir(rendered_dir):
        if not file.endswith(".pdf"):
          continue

        file_upper = file.upper()
        is_yearly = "YEARLY" in file_upper or "PROSPECTIVE" in file_upper
        is_monthly = "MONTHLY" in file_upper

        if is_yearly or is_monthly:
          # NotebookLM titles for uploaded files match the file basename
          if file not in uploaded_titles:
            file_path = os.path.join(rendered_dir, file)
            logger.info(
                "Found missing local yearly/monthly report: %s. Uploading...",
                file,
            )
            await self.upload_file(file_path)

    except Exception as e:
      logger.warning("Failed to sync yearly/monthly reports: %s", e)

  async def _prune_sources_if_needed(self, threshold: int = 95):
    """Checks source count and prunes oldest daily/weekly reports if exceeding.

    Maintains yearly and monthly reports as long as possible.

    Args:
      threshold (int): The max allowed sources before pruning starts.
    """
    client = self.client
    if (not self.notebook_id or client is None or
        not hasattr(client, "sources")):
      return

    try:
      sources = await client.sources.list(self.notebook_id)
      if len(sources) < threshold:
        return

      logger.info(
          "NotebookLM source count (%d) exceeds threshold (%d). Pruning...",
          len(sources),
          threshold,
      )

      from datetime import datetime
      import re

      def classify_source(title: str) -> str:
        title_upper = title.upper()
        category = "unknown"

        # 1. Direct keywords in filename / title
        if "YEARLY" in title_upper or "PROSPECTIVE" in title_upper:
          category = "yearly"
        elif "MONTHLY" in title_upper:
          category = "monthly"
        elif "WEEKLY" in title_upper:
          category = "weekly"
        elif "DAILY" in title_upper:
          category = "daily"
        else:
          # 2. Date range extraction, e.g., "2026-05-01 to 2026-05-07"
          date_matches = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", title)
          if len(date_matches) >= 2:
            try:
              d1 = datetime.strptime(date_matches[0], "%Y-%m-%d")
              d2 = datetime.strptime(date_matches[-1], "%Y-%m-%d")
              diff_days = abs((d2 - d1).days)
              if diff_days <= 8:
                category = "weekly"
              elif 25 <= diff_days <= 32:
                category = "monthly"
              elif diff_days >= 350:
                category = "yearly"
            except ValueError:
              pass

          # 3. Single date or other indicators
          if category == "unknown":
            if "FEED" in title_upper or "QUANTITATIVE" in title_upper:
              category = "daily"

        return category

      # Categorize sources
      daily_sources = []
      weekly_sources = []
      unknown_sources = []
      kept_sources_count = 0

      for src in sources:
        title = getattr(src, "title", "")
        category = classify_source(title)

        if category == "daily":
          daily_sources.append(src)
        elif category == "weekly":
          weekly_sources.append(src)
        elif category in ("monthly", "yearly"):
          kept_sources_count += 1
        else:
          unknown_sources.append(src)

      # Sort each category chronologically by created_at (oldest first)
      daily_sources.sort(key=lambda x: str(getattr(x, "created_at", "")))
      weekly_sources.sort(key=lambda x: str(getattr(x, "created_at", "")))
      unknown_sources.sort(key=lambda x: str(getattr(x, "created_at", "")))

      # Combine lists by priority (Daily first, then Weekly, then Unknown)
      prune_candidates = daily_sources + weekly_sources + unknown_sources

      if not prune_candidates:
        logger.warning("No prune candidates (daily/weekly/unknown) found, "
                       "but threshold exceeded! Keeping monthly/yearly.")
        return

      # Target: prune enough to get below threshold with safety margin
      safety_margin = min(5, threshold // 2)
      prune_target = len(sources) - threshold + safety_margin
      prune_count = min(prune_target, len(prune_candidates))

      for i in range(prune_count):
        src_to_delete = prune_candidates[i]
        logger.info(
            "Pruning oldest source: %s (ID: %s)",
            getattr(src_to_delete, "title", "Untitled"),
            src_to_delete.id,
        )
        await self.client.sources.delete(self.notebook_id, src_to_delete.id)

    except Exception as e:
      logger.warning("Failed to prune sources: %s", e)

  async def upload_news_text(self, text_content: str, title: str):
    """Uploads arbitrary text structure as a source to the notebook."""
    if not self.notebook_id:
      raise ValueError("Not connected to a notebook. Call connect() first.")

    await self._prune_sources_if_needed()

    logger.info("Uploading news source to NotebookLM: %s", title)
    try:
      client = self.client
      if client is not None and hasattr(client, 'sources'):
        await client.sources.add_text(self.notebook_id,
                                      title=title,
                                      content=text_content,
                                      wait=True)
      else:
        logger.error("Client or sources not available.")
    except Exception as e:
      logger.error("Error uploading text: %s", e)

  async def upload_file(self, file_path: str):
    """Uploads a local file (e.g. PDF, Markdown, TXT) to the notebook as a source."""
    if not self.notebook_id:
      raise ValueError("Not connected to a notebook. Call connect() first.")

    await self._prune_sources_if_needed()

    logger.info("Uploading file to NotebookLM: %s", file_path)
    try:
      client = self.client
      if client is not None and hasattr(client, 'sources'):
        await client.sources.add_file(self.notebook_id,
                                      file_path=file_path,
                                      wait=True)
      else:
        logger.error("Client or sources not available.")
    except Exception as e:
      logger.error("Error uploading file: %s", e)

  async def ask_question(self, question: str) -> str:
    """Queries the notebook with a specific question."""
    if not self.notebook_id:
      raise ValueError("Not connected to a notebook. Call connect() first.")

    logger.info("Querying NotebookLM: %s", question)
    if self.client and hasattr(self.client, 'chat'):
      result = await self.client.chat.ask(self.notebook_id, question)
      return result.answer

    logger.error("Client or chat not available.")
    return ""

  async def summarize_sources(self, custom_prompt: Optional[str] = None) -> str:
    """Asks NotebookLM to generate a holistic, markdown-formatted summary of all current sources."""
    if not self.notebook_id:
      raise ValueError("Not connected to a notebook. Call connect() first.")

    prompt = custom_prompt or (
        "You are an expert financial analyst. Please review all provided sources "
        "and generate a highly structured, data-driven synthesis. Group related themes "
        "together, highlight major catalysts, and format the entire response in strictly "
        "valid Markdown with clear headers and bullet points.")

    logger.info("Requesting synthesis from NotebookLM...")
    if self.client and hasattr(self.client, 'chat'):
      result = await self.client.chat.ask(self.notebook_id, prompt)
      return result.answer

    logger.error("Client or chat not available.")
    return ""

  async def clear_sources(self):
    """Deletes all sources from the notebook. Useful for resetting test environments."""
    if not self.notebook_id:
      raise ValueError("Not connected to a notebook. Call connect() first.")

    logger.info("Clearing all sources from NotebookLM database...")
    if self.client and hasattr(self.client, 'sources'):
      sources = await self.client.sources.list(self.notebook_id)
      for src in sources:
        await self.client.sources.delete(self.notebook_id, src.id)
      logger.info("Deleted %d sources.", len(sources))
    else:
      logger.error("Client or sources not available.")

  async def delete_project(self):
    """Permanently deletes the current NotebookLM project."""
    if not self.notebook_id:
      raise ValueError("Not connected to a notebook. Call connect() first.")

    logger.info("Deleting NotebookLM project: %s", self.notebook_name)
    try:
      if self.client and hasattr(self.client, 'notebooks'):
        await self.client.notebooks.delete(self.notebook_id)
        self.notebook_id = None
      else:
        logger.error("Client or notebooks API not available.")
    except Exception as e:
      logger.error("Error deleting notebook: %s", e)


if __name__ == "__main__":

  async def run_test():
    logging.basicConfig(level=logging.INFO)
    try:
      async with MarketNewsClient(test_mode=True) as db:
        await db.connect()
        await db.clear_sources()

        await db.upload_news_text(
            "Nvidia just announced a massive 50% year-over-year revenue increase. TSMC is ramping up production for new AI chips.",
            "NVDA Q1 Earnings Report Summary")
        await db.upload_news_text(
            "Oil prices are surging past $90 a barrel due to Middle East tensions in the Iran/Israel conflict region.",
            "Geopolitics Oil Crisis")

        print("\n=== ASK NOTEBOOK ===")
        answer = await db.ask_question(
            "Based on the sources, what is happening with semiconductor revenues and what macro event is impacting commodities?"
        )
        print(answer)
        print("====================\n")
    except Exception as e:
      if "Authentication" in str(e) or "login" in str(e).lower():
        logger.warning(
            "Skipping NotebookLM test: Not authenticated. Run 'notebooklm login'."
        )
      else:
        raise

  if os.environ.get("CI"):
    print("Skipping live NotebookLM integration test in CI environment.")
  else:
    asyncio.run(run_test())
