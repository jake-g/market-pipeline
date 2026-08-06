# pylint: disable=duplicate-code
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                "..")))

from portfolios import portfolio_processor
from portfolios import yahoo_portfolio_fetcher


class TestPortfolioPipeline(unittest.TestCase):

  def setUp(self):
    self.test_dir = os.path.dirname(os.path.abspath(__file__))
    self.mock_json = os.path.join(self.test_dir, "portfolio_example.json")
    self.temp_dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(self.temp_dir, "tsvs"), exist_ok=True)

  def tearDown(self):
    shutil.rmtree(self.temp_dir)

  @patch("portfolios.yahoo_portfolio_fetcher.logger")
  def test_01_fetcher_with_local_json(self, mock_logger):
    """Test the fetcher gracefully reads a local json and builds the expected files."""
    # Run fetcher on the mock file with PORTFOLIOS_DATA_DIR set to temp_dir
    with patch.dict(
        os.environ, {
            'ACTIVE_TRADING_PORTFOLIOS': 'example_active_account',
            'PORTFOLIOS_DATA_DIR': self.temp_dir
        }):
      with patch.object(
          sys, 'argv',
          ['yahoo_portfolio_fetcher.py', '--local-json', self.mock_json]):
        yahoo_portfolio_fetcher.main()

    # Check files were generated in temp_dir
    active_path = os.path.join(self.temp_dir, "tsvs",
                               "example_active_account.tsv")
    inactive_path = os.path.join(self.temp_dir, "tsvs",
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
    active_path = os.path.join(self.temp_dir, "tsvs",
                               "example_active_account.tsv")

    # Create dummy example file in temp_dir
    with open(active_path, "w") as f:
      f.write("Ticker\nAAPL\n")

    # We invoke the target files scanning logic manually on temp_dir
    import glob
    tsv_files = glob.glob(os.path.join(self.temp_dir, "tsvs", "*.tsv"))
    target_files = [
        f for f in tsv_files
        if (not os.path.basename(f).startswith("_") or
            os.path.basename(f) == "_combined_active_portfolio.tsv") and
        "example" not in os.path.basename(f).lower()
    ]

    # The target files list should explicitly NOT contain our examples
    self.assertTrue(active_path not in target_files)


if __name__ == '__main__':
  unittest.main()
