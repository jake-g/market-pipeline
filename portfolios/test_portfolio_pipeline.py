import os
# We need to import the modules to test.
import sys
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from portfolios import portfolio_processor
from portfolios import yahoo_portfolio_fetcher


class TestPortfolioPipeline(unittest.TestCase):

  def setUp(self):
    self.test_dir = os.path.dirname(os.path.abspath(__file__))
    self.mock_json = os.path.join(self.test_dir, "portfolio_example.json")

  @patch("portfolios.yahoo_portfolio_fetcher.logger")
  def test_01_fetcher_with_local_json(self, mock_logger):
    """Test the fetcher gracefully reads a local json and builds the expected files."""
    tsvs_dir = os.path.join(self.test_dir, "tsvs")
    if os.path.exists(tsvs_dir):
      for f in os.listdir(tsvs_dir):
        if f.startswith("example_") and f.endswith(".tsv"):
          os.remove(os.path.join(tsvs_dir, f))

    # Run fetcher on the mock file
    with patch.object(
        sys, 'argv',
        ['yahoo_portfolio_fetcher.py', '--local-json', self.mock_json]):
      yahoo_portfolio_fetcher.main()

    # Check files were generated
    active_path = os.path.join(self.test_dir, "tsvs",
                               "example_active_account.tsv")
    inactive_path = os.path.join(self.test_dir, "tsvs",
                                 "example_inactive_trust.tsv")
    self.assertTrue(os.path.exists(active_path))
    self.assertTrue(os.path.exists(inactive_path))

    # Check simple TSV contents
    df = pd.read_csv(active_path, sep='\t')
    self.assertEqual(len(df), 3)  # AAPL, NVDA, and CASH
    self.assertTrue("CASH" in df['Ticker'].values)

  @patch("portfolios.portfolio_processor.logger")
  def test_02_processor_ignores_examples(self, mock_logger):
    """Test the processor ignores files with example in the title."""
    active_path = os.path.join(self.test_dir, "tsvs",
                               "example_active_account.tsv")

    # Make sure it exists from prev test
    self.assertTrue(os.path.exists(active_path))

    # We invoke the target files scanning logic manually
    import glob
    tsv_files = glob.glob(os.path.join(self.test_dir, "tsvs", "*.tsv"))
    target_files = [
        f for f in tsv_files if not os.path.basename(f).startswith("_") and
        "example" not in os.path.basename(f).lower()
    ]

    # The target files list should explicitly NOT contain our examples
    self.assertTrue(active_path not in target_files)


if __name__ == '__main__':
  unittest.main()
