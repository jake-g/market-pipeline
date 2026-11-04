"""Unit tests for political_fetcher (no network; requests is mocked)."""

import datetime
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from political_fetcher import ODDS_COLUMNS
from political_fetcher import PoliticalFetcher

_DAY = 86400


def _event(n_markets: int = 2):
  """Builds a minimal Gamma event with n binary sub-markets."""
  markets = []
  for i in range(n_markets):
    markets.append({
        "id":
            str(100 + i),
        "question":
            f"Will party {i} win?",
        "groupItemTitle":
            f"Party {i}",
        "outcomes":
            '["Yes", "No"]',
        "outcomePrices":
            json.dumps([str(0.1 * (i + 1)),
                        str(1 - 0.1 * (i + 1))]),
        "clobTokenIds":
            json.dumps([f"tok{i}_yes", f"tok{i}_no"]),
        "volumeNum":
            1000.0 * (n_markets - i),
    })
  return {"title": "Who wins?", "markets": markets}


class PoliticalFetcherTest(unittest.TestCase):

  def setUp(self):
    self.tmp = tempfile.mkdtemp()
    self.fetcher = PoliticalFetcher(data_dir=self.tmp, cache_dir=self.tmp)

  def tearDown(self):
    shutil.rmtree(self.tmp, ignore_errors=True)

  def test_parse_event_markets_multi(self):
    rows = PoliticalFetcher.parse_event_markets(_event(3), "k", "cat")
    # Ranked by probability (desc): party 2 (0.3), party 1 (0.2), party 0.
    self.assertEqual([r["Outcome"] for r in rows],
                     ["Party 2", "Party 1", "Party 0"])
    self.assertAlmostEqual(rows[1]["Prob"], 0.2)
    self.assertEqual(rows[1]["Token_Id"], "tok1_yes")
    self.assertEqual(rows[0]["Question"], "Who wins?")
    self.assertEqual(rows[2]["Market_Id"], "100")

  def test_parse_event_markets_binary_and_bad_rows(self):
    ev = _event(1)
    ev["markets"].append({"id": "x", "outcomePrices": None})  # unpriced
    ev["markets"].append({"id": "y", "outcomePrices": "not json"})
    closed = dict(_event(2)["markets"][1], closed=True)  # resolved bucket
    ev["markets"].append(closed)
    rows = PoliticalFetcher.parse_event_markets(ev, "k", "cat")
    self.assertEqual(len(rows), 1)
    self.assertEqual(rows[0]["Outcome"], "Yes")

  def test_parse_event_markets_caps_outcomes(self):
    rows = PoliticalFetcher.parse_event_markets(_event(10), "k", "cat")
    self.assertEqual(len(rows), 6)
    self.assertEqual(rows[0]["Outcome"], "Party 9")  # highest prob first

  def test_parse_price_history_daily_last_and_start_filter(self):
    t0 = int(datetime.datetime(2026, 1, 1).timestamp())  # local midnight
    payload = {
        "history": [
            {
                "t": t0 - _DAY,
                "p": 0.1
            },  # 2025-12-31 (filtered out)
            {
                "t": t0 + 60,
                "p": 0.5
            },
            {
                "t": t0 + 3600,
                "p": 0.55
            },  # same day, later -> wins
            {
                "t": t0 + _DAY,
                "p": 0.6
            },
            {
                "t": "bad",
                "p": 0.6
            },
        ]
    }
    daily = PoliticalFetcher.parse_price_history(payload, "2026-01-01")
    self.assertEqual(daily, {"2026-01-01": 0.55, "2026-01-02": 0.6})
    self.assertEqual(PoliticalFetcher.parse_price_history(None, "2026"), {})

  def test_merge_is_idempotent_and_prefers_new(self):
    old = pd.DataFrame(
        [["2026-01-01", "k", "c", "q", "Yes", 0.4, 1, "pm", "1"]],
        columns=ODDS_COLUMNS)
    new = pd.DataFrame(
        [["2026-01-01", "k", "c", "q", "Yes", 0.5, 1, "pm", "1"],
         ["2026-01-02", "k", "c", "q", "Yes", 0.6, 1, "pm", "1"]],
        columns=ODDS_COLUMNS)
    merged = PoliticalFetcher.merge_odds(old, new)
    self.assertEqual(len(merged), 2)
    self.assertEqual(merged.iloc[0]["Date"], "2026-01-02")  # newest first
    self.assertAlmostEqual(
        merged[merged["Date"] == "2026-01-01"]["Prob"].item(), 0.5)
    again = PoliticalFetcher.merge_odds(merged, new)
    pd.testing.assert_frame_equal(again, merged)

  def test_parse_approval_polls_rolling(self):
    polls = [{
        "end_date":
            "2026-01-01",
        "answers": [{
            "choice": "Approve",
            "pct": 40
        }, {
            "choice": "Disapprove",
            "pct": 56
        }]
    }, {
        "end_date":
            "2026-01-03",
        "answers": [{
            "choice": "Approve",
            "pct": 44
        }, {
            "choice": "Disapprove",
            "pct": 52
        }]
    }]
    df = PoliticalFetcher.parse_approval_polls(polls, "2026-01-02")
    self.assertEqual(list(df.columns), ODDS_COLUMNS)
    self.assertEqual(sorted(df["Date"].unique()), ["2026-01-02", "2026-01-03"])
    appr = df[(df["Date"] == "2026-01-03") & (df["Outcome"] == "Approve")]
    self.assertAlmostEqual(appr["Prob"].item(), 0.42)  # mean of 0.40, 0.44
    self.assertEqual(appr["Source"].item(), "votehub")

  @patch("political_fetcher.requests.get")
  def test_backfill_dates_via_mocked_requests(self, mock_get):
    today = datetime.date.today()
    t_today = int(
        datetime.datetime.combine(today, datetime.time(12)).timestamp())

    def fake(url, params=None, **_):
      resp = unittest.mock.MagicMock()
      resp.raise_for_status.return_value = None
      if "prices-history" in url:
        resp.json.return_value = {
            "history": [{
                "t": t_today - 3 * _DAY,
                "p": 0.3
            }, {
                "t": t_today - 1 * _DAY,
                "p": 0.35
            }, {
                "t": t_today,
                "p": 0.99
            }]  # ignored; today from Gamma
        }
      elif "/events" in url:
        resp.json.return_value = [_event(1)]
      else:
        resp.json.return_value = []  # VoteHub: no polls
      return resp

    mock_get.side_effect = fake
    cfg = [{"key": "k", "category": "c", "slug_or_query": "some-slug"}]
    with patch("political_fetcher.config.POLITICAL_MARKETS", cfg):
      df = self.fetcher.run(backfill=True, days=2)

    def fmt(days_ago: int) -> str:
      return (today - datetime.timedelta(days=days_ago)).strftime("%Y-%m-%d")

    self.assertEqual(list(df["Date"]), [fmt(0), fmt(1)])  # 3d-ago excluded
    self.assertAlmostEqual(df.iloc[0]["Prob"], 0.1)  # Gamma price for today
    self.assertAlmostEqual(df.iloc[1]["Prob"], 0.35)
    self.assertTrue(self.fetcher.odds_file.exists())
    self.assertTrue(self.fetcher.events_file.exists())


if __name__ == "__main__":
  unittest.main()
