"""Unit tests for the NotebookLM client and its pruning logic."""

import asyncio
import datetime
import unittest
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from reports.notebooklm_client import looks_like_studio_stub
from reports.notebooklm_client import MarketNewsClient
from reports.notebooklm_client import title_date


class MockSource:
  """A simple mock class for a NotebookLM source."""

  def __init__(self, source_id: str, title: str, created_at: str):
    self.id = source_id
    self.title = title
    self.created_at = created_at


class TestMarketNewsClientPruning(unittest.TestCase):
  """Tests the pruning and categorization logic in MarketNewsClient."""

  def setUp(self):
    self.client = MarketNewsClient(project_name="Test Project")
    self.client.notebook_id = "test-notebook-id"

    # Setup the mock API client structure
    self.mock_client_api = MagicMock()
    self.mock_sources_api = AsyncMock()
    self.mock_client_api.sources = self.mock_sources_api
    self.client.client = self.mock_client_api

  def test_prune_sources_under_threshold(self):
    """Verify that no sources are pruned if count is below threshold."""
    mock_sources = [
        MockSource("1", "2026-05-07 Daily Market Feed", "2026-05-07T09:00:00Z"),
        MockSource("2", "05_MONTHLY_REPORT.pdf", "2026-05-01T00:00:00Z"),
    ]
    self.mock_sources_api.list.return_value = mock_sources

    # Run the async prune method using asyncio
    asyncio.run(self.client._prune_sources_if_needed(threshold=5))

    # Assert no deletion was attempted
    self.mock_sources_api.delete.assert_not_called()

  def test_prune_sources_prioritization(self):
    """Verify daily and weekly sources are deleted first, keeping yearly/monthly."""
    # Create a mock pool of 7 sources
    mock_sources = [
        # Daily
        MockSource("d2", "2026-05-02 Daily Market Feed",
                   "2026-05-02T09:00:00Z"),
        MockSource("d1", "2026-05-01 Daily Market Feed",
                   "2026-05-01T09:00:00Z"),
        # Weekly
        MockSource("w1", "2026-05-01 to 2026-05-07 Market Synthesis",
                   "2026-05-07T18:00:00Z"),
        # Monthly (should be kept)
        MockSource("m1", "05_MONTHLY_REPORT.pdf", "2026-05-01T00:00:00Z"),
        # Yearly (should be kept)
        MockSource("y1", "2025_YEARLY_REPORT.pdf", "2025-12-31T23:59:59Z"),
        # Unknown
        MockSource("u2", "Another random source", "2026-05-04T12:00:00Z"),
        MockSource("u1", "Some random source", "2026-05-03T12:00:00Z"),
    ]
    self.mock_sources_api.list.return_value = mock_sources

    # We have 7 sources. If threshold = 5, we prune max(10, 7 - 5 + 2) = 4 sources.
    # Since we have 5 prune candidates, it should delete the top 4 candidates:
    # 1. d1 (daily, oldest)
    # 2. d2 (daily, newer)
    # 3. w1 (weekly)
    # 4. u1 (unknown, oldest)
    # While keeping: m1 (monthly), y1 (yearly), u2 (unknown, newer)
    asyncio.run(self.client._prune_sources_if_needed(threshold=5))

    deleted_ids = [
        call.args[1] for call in self.mock_sources_api.delete.call_args_list
    ]

    self.assertEqual(len(deleted_ids), 4)
    self.assertEqual(deleted_ids[0], "d1")
    self.assertEqual(deleted_ids[1], "d2")
    self.assertEqual(deleted_ids[2], "w1")
    self.assertEqual(deleted_ids[3], "u1")

  def test_prune_uses_title_date_when_created_at_missing(self):
    """Server list order is newest-first and created_at is often None.

    Before the fix str(None) sorted everything equal and the NEWEST feeds
    were deleted first (seen live: 10-09, 10-08 pruned before 09-24).
    """
    mock_sources = [
        MockSource("new", "2026-10-09 Daily Market Feed", None),
        MockSource("mid", "2026-10-08 Daily Market Feed", None),
        MockSource("pdf", "10-07_DAILY_REPORT.pdf", None),
        MockSource("old", "2026-09-24 Daily Market Feed", None),
        MockSource("m1", "09_MONTHLY_REPORT.pdf", None),
    ]
    self.mock_sources_api.list.return_value = mock_sources

    # 5 sources, threshold 4 => prune 5-4+2 = 3 oldest dailies.
    asyncio.run(self.client._prune_sources_if_needed(threshold=4))

    deleted_ids = [
        call.args[1] for call in self.mock_sources_api.delete.call_args_list
    ]
    self.assertEqual(deleted_ids, ["old", "pdf", "mid"])
    self.assertNotIn("new", deleted_ids)


class TestStudioStubHandling(unittest.TestCase):
  """NotebookLM may answer with a Studio confirmation instead of the report."""

  STUB = ("The **Daily Market Intelligence Report for October 8, 2026** has "
          "been generated and published to your Studio panel.\n\nThis report "
          "examines Thursday's technology retrenchment...")
  GOOD = (
      "# Daily Market Intelligence Report\n\n## Top AI Thematic Insights\n" +
      ("* bullet with numbers +4.7% [1]\n" * 120) +
      "\n## References\n1. Headline - https://example.com\n")

  def test_detects_stub_and_accepts_report(self):
    self.assertTrue(looks_like_studio_stub(self.STUB))
    self.assertTrue(looks_like_studio_stub(""))
    self.assertFalse(looks_like_studio_stub(self.GOOD))
    self.assertFalse(
        looks_like_studio_stub(self.GOOD, required_markers=["## References"]))
    self.assertTrue(
        looks_like_studio_stub(self.GOOD.replace("## References", "## Refs"),
                               required_markers=["## References"]))

  def test_title_date(self):
    self.assertEqual(title_date("2026-10-08 Daily Market Feed"),
                     datetime.date(2026, 10, 8))
    self.assertEqual(title_date("2026-10-04 to 2026-10-10 Market Synthesis"),
                     datetime.date(2026, 10, 4))
    self.assertIsNotNone(title_date("10-08_DAILY_REPORT.pdf"))
    self.assertIsNone(title_date("Historical Context: Recent Reports"))

  def test_ask_question_recovers_from_studio_artifact(self):
    """A stub answer triggers download of the newest report artifact."""
    client = MarketNewsClient(project_name="Test")
    client.notebook_id = "nb"
    api = MagicMock()
    api.chat = AsyncMock()
    api.chat.get_conversation_id.return_value = "conv-1"
    api.chat.ask.return_value = MagicMock(answer=self.STUB)
    api.artifacts = AsyncMock()
    art = MagicMock(id="art-1", status="completed", created_at="2026-10-12")
    api.artifacts.list_reports.return_value = [art]

    async def _download(_nb, path, _aid):
      with open(path, "w", encoding="utf-8") as f:
        f.write(self.GOOD)
      return path

    api.artifacts.download_report.side_effect = _download
    client.client = api

    answer = asyncio.run(
        client.ask_question("write it",
                            source_ids=["s1"],
                            required_markers=["## References"]))

    self.assertEqual(answer, self.GOOD)
    self.assertIsNotNone(api.chat.ask.call_args.kwargs["conversation_id"])
    api.chat.ask.assert_awaited_once()
    self.assertEqual(api.chat.ask.call_args.kwargs["source_ids"], ["s1"])
    api.artifacts.delete.assert_awaited_with("nb", "art-1")

  def test_synthesize_report_prefers_artifact_api(self):
    """generate_report (CUSTOM) -> wait -> download -> delete; no chat."""
    client = MarketNewsClient(project_name="Test")
    client.notebook_id = "nb"
    api = MagicMock()
    api.chat = AsyncMock()
    api.artifacts = AsyncMock()
    api.artifacts.generate_report.return_value = MagicMock(task_id="t-1")
    api.artifacts.wait_for_completion.return_value = MagicMock(
        status="completed")

    async def _download(_nb, path, _aid):
      with open(path, "w", encoding="utf-8") as f:
        f.write(self.GOOD)
      return path

    api.artifacts.download_report.side_effect = _download
    client.client = api

    answer = asyncio.run(
        client.synthesize_report("prompt",
                                 source_ids=["s1"],
                                 required_markers=["## References"]))

    self.assertEqual(answer, self.GOOD)
    kwargs = api.artifacts.generate_report.call_args.kwargs
    self.assertEqual(kwargs["source_ids"], ["s1"])
    self.assertEqual(kwargs["custom_prompt"], "prompt")
    api.artifacts.delete.assert_awaited_with("nb", "t-1")
    api.chat.ask.assert_not_called()


class TestMarketNewsClientSync(unittest.TestCase):
  """Tests the automatic syncing of yearly/monthly reports."""

  def setUp(self):
    self.client = MarketNewsClient(project_name="Market Reports")
    self.client.notebook_id = "test-notebook-id"

    self.mock_client_api = MagicMock()
    self.mock_sources_api = AsyncMock()
    self.mock_client_api.sources = self.mock_sources_api
    self.client.client = self.mock_client_api

    # Mock upload_file to verify calls
    self.client.upload_file = AsyncMock()

  @unittest.mock.patch("os.path.exists")
  @unittest.mock.patch("os.listdir")
  def test_sync_missing_yearly_monthly(self, mock_listdir, mock_exists):
    """Verify missing local yearly/monthly reports are synced."""
    mock_exists.return_value = True
    mock_listdir.return_value = [
        "2025_YEARLY_REPORT.pdf",
        "05_MONTHLY_REPORT.pdf",
        "05-07_DAILY_REPORT.pdf",
        "05-07_WEEKLY_REPORT.pdf",
    ]

    # Only 2025_YEARLY_REPORT.pdf is already in NotebookLM
    mock_sources = [
        MockSource("1", "2025_YEARLY_REPORT.pdf", "2026-01-01T00:00:00Z")
    ]
    self.mock_sources_api.list.return_value = mock_sources

    asyncio.run(self.client.sync_yearly_monthly_reports())

    # It should only call upload_file for 05_MONTHLY_REPORT.pdf
    # (2025_YEARLY is already uploaded, DAILY and WEEKLY are skipped)
    self.client.upload_file.assert_called_once()
    uploaded_path = self.client.upload_file.call_args[0][0]
    self.assertTrue(uploaded_path.endswith("05_MONTHLY_REPORT.pdf"))


if __name__ == "__main__":
  unittest.main()
