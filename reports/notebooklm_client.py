import asyncio
import datetime as _dt
import logging
import os
import re
import tempfile
from typing import Any, List, Optional
import uuid

from notebooklm import NotebookLMClient

logger = logging.getLogger(__name__)

NOTEBOOK_NAME = "Market News DB"

# NotebookLM's chat now sometimes creates a Studio "report" artifact and
# answers with a confirmation instead of the text. Detect that so we can
# fetch the artifact (or retry) rather than saving the stub as the report.
_STUDIO_STUB_RE = re.compile(
    r"(studio panel|has been (generated|published)|is published and|"
    r"ready in your studio)", re.IGNORECASE)
MIN_REPORT_CHARS = 2500


class NotebookLMQuotaError(RuntimeError):
  """Raised when NotebookLM refuses a generation because of rate limits.

  Callers doing backfills should stop the sweep and resume later rather
  than fall back to slower paths.
  """


def title_date(title: str) -> Optional[_dt.date]:
  """Extracts a date from a source title for chronological pruning.

  Handles "2026-10-08 Daily Market Feed", "2026-10-04 to 2026-10-10 …",
  "10-08_DAILY_REPORT.pdf" (year inferred, December→January rollover) and
  "09_MONTHLY_REPORT.pdf".

  Args:
    title (str): Source title.

  Returns:
    Optional[datetime.date]: Parsed date or None if no date is present.
  """
  m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", title)
  if m:
    try:
      return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
      return None
  m = re.match(r"(\d{2})-(\d{2})_", title)
  if m:
    today = _dt.date.today()
    year = today.year
    try:
      d = _dt.date(year, int(m.group(1)), int(m.group(2)))
    except ValueError:
      return None
    return d.replace(year=year - 1) if d > today else d
  m = re.match(r"(\d{2})_MONTHLY", title)
  if m:
    today = _dt.date.today()
    month = int(m.group(1))
    year = today.year if month <= today.month else today.year - 1
    return _dt.date(year, month, 1)
  return None


def _source_sort_key(src: Any) -> tuple:
  """Oldest-first sort key: title date, then created_at, then title."""
  d = title_date(getattr(src, "title", "") or "")
  created = getattr(src, "created_at", None)
  return (d or _dt.date.max, str(created or ""), getattr(src, "title", ""))


def looks_like_studio_stub(
    answer: str, required_markers: Optional[List[str]] = None) -> bool:
  """True if the chat answer is a Studio confirmation, not the report."""
  text = (answer or "").strip()
  if len(text) < 1500:
    return True
  if len(text) < MIN_REPORT_CHARS and _STUDIO_STUB_RE.search(text):
    return True
  if required_markers:
    return not all(
        m.lstrip("# ").strip().lower() in text.lower()
        for m in required_markers)
  return False


class MarketNewsClient:
  """Wrapper around NotebookLMClient to manage an overarching market news notebook."""

  def __init__(self,
               project_name: str = "Market News DB",
               test_mode: bool = False):
    self.notebook_id: Optional[str] = None
    self.client = None
    self.notebook_name = f"TEST {project_name}" if test_mode else project_name

  async def __aenter__(self):
    self.client = await NotebookLMClient.from_storage(timeout=180.0)
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

      # Sort each category chronologically (oldest first). Titles carry
      # the authoritative date ("2026-10-08 Daily Market Feed",
      # "10-08_DAILY_REPORT.pdf"); created_at is often None, and str(None)
      # sorts arbitrarily, which previously deleted the NEWEST sources.
      daily_sources.sort(key=_source_sort_key)
      weekly_sources.sort(key=_source_sort_key)
      unknown_sources.sort(key=_source_sort_key)

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

  async def upload_file(self, file_path: str, prune: bool = True):
    """Uploads a local file (PDF, Markdown, TXT) to the notebook as a source.

    Args:
      file_path (str): Path of the file to upload.
      prune (bool): Run the source-cap prune check first. Batch callers
        that already pruned once should pass False.
    """
    if not self.notebook_id:
      raise ValueError("Not connected to a notebook. Call connect() first.")

    if prune:
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

  async def find_source_ids(self, titles: List[str]) -> List[str]:
    """Returns ids of sources whose title matches any of ``titles``."""
    client = self.client
    if not self.notebook_id or client is None or not hasattr(client, "sources"):
      return []
    wanted = set(titles)
    sources = await client.sources.list(self.notebook_id)
    return [s.id for s in sources if getattr(s, "title", "") in wanted]

  async def recent_feed_source_ids(self, days: int = 5) -> List[str]:
    """Ids of the ``days`` most recent '... Daily Market Feed' sources."""
    client = self.client
    if not self.notebook_id or client is None or not hasattr(client, "sources"):
      return []
    sources = await client.sources.list(self.notebook_id)
    feeds = [
        s for s in sources if "Daily Market Feed" in getattr(s, "title", "") and
        "Quantitative" not in getattr(s, "title", "")
    ]
    feeds.sort(key=_source_sort_key, reverse=True)
    return [s.id for s in feeds[:days]]

  async def _download_latest_report_artifact(self) -> str:
    """Fetches the newest Studio report artifact as markdown, then deletes it."""
    client = self.client
    if not self.notebook_id or client is None or not hasattr(
        client, "artifacts"):
      return ""
    try:
      reports = await client.artifacts.list_reports(self.notebook_id)
    except Exception as e:  # pylint: disable=broad-except
      logger.warning("Could not list report artifacts: %s", e)
      return ""
    if not reports:
      return ""
    reports.sort(key=lambda a: str(getattr(a, "created_at", "")), reverse=True)
    art = reports[0]
    try:
      status = getattr(art, "status", None)
      if status is not None and str(status).lower() not in ("completed",
                                                            "ready", "done"):
        await client.artifacts.wait_for_completion(self.notebook_id,
                                                   art.id,
                                                   timeout=240)
      with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "report.md")
        await client.artifacts.download_report(self.notebook_id, path, art.id)
        with open(path, "r", encoding="utf-8") as f:
          text = f.read()
      logger.info("Recovered %d chars from Studio report artifact %s",
                  len(text), art.id)
      try:
        await client.artifacts.delete(self.notebook_id, art.id)
      except Exception:  # pylint: disable=broad-except
        pass
      return text
    except Exception as e:  # pylint: disable=broad-except
      logger.warning("Could not download report artifact %s: %s", art.id, e)
      return ""

  async def generate_report_artifact(self,
                                     prompt: str,
                                     source_ids: Optional[List[str]] = None,
                                     timeout: float = 420.0) -> str:
    """Synthesises a report via the Studio report-artifact API.

    This is the reliable path for long "write a report" prompts: chat.ask
    on such prompts now triggers NotebookLM's agentic report generation
    and either returns a one-line confirmation or streams >256 MB and
    aborts (observed 2026-10-12). The artifact API is deterministic:
    create -> poll -> download markdown -> delete.

    Args:
      prompt (str): Full report prompt (used as the custom report prompt).
      source_ids (Optional[List[str]]): Sources to ground on; None = all.
      timeout (float): Seconds to wait for generation.

    Returns:
      str: Report markdown, or "" on failure.
    """
    client = self.client
    if not self.notebook_id or client is None or not hasattr(
        client, "artifacts"):
      return ""
    try:
      from notebooklm import ReportFormat  # pylint: disable=import-outside-toplevel
      status = await client.artifacts.generate_report(
          self.notebook_id,
          report_format=ReportFormat.CUSTOM,
          source_ids=source_ids or None,
          custom_prompt=prompt)
      task_id = getattr(status, "task_id", None)
      if not task_id:
        logger.warning("generate_report returned no task id: %s", status)
        return ""
      final = await client.artifacts.wait_for_completion(self.notebook_id,
                                                         task_id,
                                                         timeout=timeout)
      if str(getattr(final, "status",
                     "")).lower() not in ("completed", "ready", "done"):
        logger.warning("Report artifact %s ended with status %s", task_id,
                       getattr(final, "status", "?"))
        return ""
      with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "report.md")
        await client.artifacts.download_report(self.notebook_id, path, task_id)
        with open(path, "r", encoding="utf-8") as f:
          text = f.read()
      logger.info("Report artifact %s: %d chars", task_id, len(text))
      try:
        await client.artifacts.delete(self.notebook_id, task_id)
      except Exception as e:  # pylint: disable=broad-except
        logger.debug("Could not delete artifact %s: %s", task_id, e)
      return text
    except Exception as e:  # pylint: disable=broad-except
      msg = str(e).lower()
      if "rate limit" in msg or "quota" in msg or "ratelimit" in msg:
        raise NotebookLMQuotaError(str(e)) from e
      logger.warning("Report artifact generation failed: %s", e)
      return ""

  async def synthesize_report(
      self,
      prompt: str,
      source_ids: Optional[List[str]] = None,
      required_markers: Optional[List[str]] = None) -> str:
    """Artifact-first report synthesis with chat fallback and validation."""
    text = await self.generate_report_artifact(prompt, source_ids)
    if text and not looks_like_studio_stub(text, required_markers):
      return text
    logger.warning("Artifact path returned no valid report; trying chat.")
    return await self.ask_question(prompt,
                                   source_ids=source_ids,
                                   required_markers=required_markers)

  async def ask_question(self,
                         question: str,
                         source_ids: Optional[List[str]] = None,
                         required_markers: Optional[List[str]] = None,
                         fresh_conversation: bool = True,
                         max_attempts: int = 2) -> str:
    """Queries the notebook and returns a validated markdown answer.

    Args:
      question (str): Prompt to send.
      source_ids (Optional[List[str]]): Restrict retrieval to these sources
        (much faster than the whole notebook). None = all sources.
      required_markers (Optional[List[str]]): Substrings that must appear
        in a valid answer (e.g. section headers). Missing markers trigger
        the artifact fallback / retry.
      fresh_conversation (bool): Delete the current conversation first.
      max_attempts (int): Total chat attempts before giving up.

    Returns:
      str: The answer text (possibly recovered from a Studio artifact).
    """
    if not self.notebook_id:
      raise ValueError("Not connected to a notebook. Call connect() first.")
    client = self.client
    if client is None or not hasattr(client, "chat"):
      logger.error("Client or chat not available.")
      return ""

    inline_note = ("\n\nIMPORTANT: Reply with the complete report as markdown "
                   "text directly in this chat response. Do NOT create a "
                   "Studio report, note, document or file.")
    answer = ""
    for attempt in range(1, max_attempts + 1):
      # A client-generated conversation id starts a brand-new server thread.
      # delete_conversation() does NOT reset the notebook's "current"
      # conversation (verified 2026-10-12), so without this every ask
      # replays the whole history and can exceed the 256 MB stream cap.
      conv_id = str(uuid.uuid4()) if fresh_conversation else None
      prompt = question if attempt == 1 else question + inline_note
      logger.info(
          "Querying NotebookLM (attempt %d/%d, %s sources, conv %s): %s",
          attempt, max_attempts,
          len(source_ids) if source_ids else "all", (conv_id or "current")[:8],
          prompt[:120])
      try:
        result = await client.chat.ask(self.notebook_id,
                                       prompt,
                                       source_ids=source_ids or None,
                                       conversation_id=conv_id)
        answer = result.answer or ""
      except Exception as e:  # pylint: disable=broad-except
        logger.warning("chat.ask failed on attempt %d: %s", attempt, e)
        answer = ""

      if not looks_like_studio_stub(answer, required_markers):
        return answer

      logger.warning(
          "NotebookLM returned a %d-char stub instead of the report; "
          "checking Studio artifacts...", len(answer))
      recovered = await self._download_latest_report_artifact()
      if recovered and not looks_like_studio_stub(recovered, required_markers):
        return recovered

    logger.error("NotebookLM did not return a valid report after %d attempts",
                 max_attempts)
    return answer

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
