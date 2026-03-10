import asyncio
import logging
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

    except Exception as e:
      logger.error("Failed to connect to NotebookLM: %s", e)
      raise

  async def upload_news_text(self, text_content: str, title: str):
    """Uploads arbitrary text structure as a source to the notebook."""
    if not self.notebook_id:
      raise ValueError("Not connected to a notebook. Call connect() first.")

    logger.info("Uploading news source to NotebookLM: %s", title)
    try:
      if self.client and hasattr(self.client, 'sources'):
        await self.client.sources.add_text(self.notebook_id,
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

    logger.info("Uploading file to NotebookLM: %s", file_path)
    try:
      if self.client and hasattr(self.client, 'sources'):
        await self.client.sources.add_file(self.notebook_id,
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

  asyncio.run(run_test())
