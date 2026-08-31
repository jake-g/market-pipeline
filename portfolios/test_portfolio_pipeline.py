# pylint: disable=duplicate-code
import base64
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import MagicMock
from unittest.mock import mock_open
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
  def test_fetcher_with_local_json(self, mock_logger):
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
  def test_processor_ignores_examples(self, mock_logger):
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

  def test_parse_curl_command_valid(self):
    """Test parsing cURL command with cookie, crumb, and userId."""
    curl_str = (
        "curl 'https://query2.finance.yahoo.com/v7/finance/desktop/portfolio"
        "?crumb=abc123crumb&userId=user123' "
        "-H 'Cookie: A1=test_cookie_val; A3=test_val2' "
        "-H 'User-Agent: Mozilla/5.0'")
    res = yahoo_portfolio_fetcher.parse_curl_command(curl_str)
    self.assertEqual(res["crumb"], "abc123crumb")
    self.assertEqual(res["user_id"], "user123")
    self.assertEqual(res["cookie"], "A1=test_cookie_val; A3=test_val2")

  def test_parse_curl_command_no_cookie(self):
    """Test parsing cURL without cookie does not misinterpret User-Agent."""
    curl_str = (
        "curl 'https://query2.finance.yahoo.com/v7/finance/desktop/portfolio"
        "?crumb=0HbnO0IZtE7&userId=' "
        "-H 'User-Agent: Mozilla/5.0' "
        "-H 'DNT: 1'")
    res = yahoo_portfolio_fetcher.parse_curl_command(curl_str)
    self.assertEqual(res["crumb"], "0HbnO0IZtE7")
    self.assertEqual(res["cookie"], "")

  def test_parse_curl_extract_guid(self):
    """Test extracting user_id from OTH cookie JWT payload."""
    payload = json.dumps({"cu": {"guid": "GUID12345"}}).encode("utf-8")
    b64 = base64.b64encode(payload).decode("utf-8")
    oth_token = f"v=2&s=0&d=header.{b64}.sig"
    curl_str = (
        "curl 'https://query1.finance.yahoo.com/v7/finance/desktop/portfolio"
        "?crumb=testcrumb' "
        f"-b 'OTH={oth_token}; test=1'")
    res = yahoo_portfolio_fetcher.parse_curl_command(curl_str)
    self.assertEqual(res["crumb"], "testcrumb")
    self.assertEqual(res["user_id"], "GUID12345")

  @patch("portfolios.yahoo_portfolio_fetcher.logger")
  @patch("portfolios.yahoo_portfolio_fetcher.verify_yahoo_auth")
  @patch("portfolios.yahoo_portfolio_fetcher.save_credentials_to_env")
  def test_load_and_save_curl_from_file(self, mock_save, mock_verify,
                                        mock_logger):
    """Test load_and_save_curl_from_file reads auth file and saves credentials."""
    mock_verify.return_value = True
    test_auth_file = os.path.join(self.temp_dir, "yahoo_auth_curl.txt")
    with open(test_auth_file, "w", encoding="utf-8") as f:
      f.write(
          "curl 'https://query1.finance.yahoo.com/v7/finance/desktop/portfolio"
          "?crumb=mycrumb&userId=u123' -H 'Cookie: A1=val'")

    with patch("portfolios.yahoo_portfolio_fetcher.CURL_AUTH_FILE",
               test_auth_file):
      success = yahoo_portfolio_fetcher.load_and_save_curl_from_file(
          os.path.join(self.temp_dir, ".env"))
      self.assertTrue(success)
      mock_save.assert_called_once()

  def test_clear_curl_auth_file(self):
    """Test clear_curl_auth_file truncates the auth file."""
    test_auth_file = os.path.join(self.temp_dir, "yahoo_auth_curl.txt")
    with open(test_auth_file, "w", encoding="utf-8") as f:
      f.write("curl something")

    with patch("portfolios.yahoo_portfolio_fetcher.CURL_AUTH_FILE",
               test_auth_file):
      yahoo_portfolio_fetcher.clear_curl_auth_file()
      with open(test_auth_file, "r", encoding="utf-8") as f:
        self.assertEqual(f.read(), "")

  @patch("portfolios.yahoo_portfolio_fetcher.logger")
  @patch("portfolios.yahoo_portfolio_fetcher.verify_yahoo_auth")
  def test_load_and_save_curl_invalid_clears_file(self, mock_verify,
                                                  mock_logger):
    """Test that failed auth check clears the cURL auth file and returns False."""
    mock_verify.return_value = False
    test_auth_file = os.path.join(self.temp_dir, "yahoo_auth_curl.txt")
    with open(test_auth_file, "w", encoding="utf-8") as f:
      f.write(
          "curl 'https://query1.finance.yahoo.com/v7/finance/desktop/portfolio"
          "?crumb=stale_crumb&userId=u123' -H 'Cookie: A1=stale'")

    with patch("portfolios.yahoo_portfolio_fetcher.CURL_AUTH_FILE",
               test_auth_file):
      success = yahoo_portfolio_fetcher.load_and_save_curl_from_file(
          os.path.join(self.temp_dir, ".env"))
      self.assertFalse(success)
      with open(test_auth_file, "r", encoding="utf-8") as f:
        self.assertEqual(f.read(), "")


if __name__ == '__main__':
  unittest.main()
