"""Unit tests for the NotebookLM client and its pruning logic."""

import asyncio
import unittest
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from reports.notebooklm_client import MarketNewsClient


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
