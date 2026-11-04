"""Tests for shipping_fetcher PortWatch handling (mocked requests)."""

import datetime
import logging
from pathlib import Path
import shutil
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import pandas as pd

import config
import shipping_fetcher
from shipping_fetcher import ShippingFetcher

ARCGIS_ERROR = {"error": {"code": 400, "message": "Invalid URL"}}


def _resp(payload, status=200) -> MagicMock:
  resp = MagicMock()
  resp.status_code = status
  resp.json.return_value = payload
  return resp


def _port_feature(date: str, pid: str, name: str, calls: int) -> dict:
  return {
      "attributes": {
          "date": date,
          "portid": pid,
          "portname": name,
          "country": "X",
          "portcalls": calls,
          "portcalls_container": 1,
          "portcalls_tanker": 2,
          "portcalls_dry_bulk": 3,
          "import": 10,
          "export": 20,
      }
  }


class TestShippingFetcherPortWatch(unittest.TestCase):

  def setUp(self):
    logging.disable(logging.CRITICAL)
    self.test_dir = Path(".test_shipping_data")
    self.cache_dir = Path(".test_shipping_cache")
    for d in (self.test_dir, self.cache_dir):
      if d.exists():
        shutil.rmtree(d)
    self.fetcher = ShippingFetcher(data_dir=str(self.test_dir),
                                   cache_dir=str(self.cache_dir))
    self.tsv = self.test_dir / "shipping" / "chokepoint_metrics.tsv"

  def tearDown(self):
    logging.disable(logging.NOTSET)
    for d in (self.test_dir, self.cache_dir):
      if d.exists():
        shutil.rmtree(d)

  def _write_synthetic_tsv(self) -> None:
    rows = []
    for date, (h, m) in {
        "2026-10-24": (5, 228),
        "2026-10-25": (2, 212),
        "2026-11-01": (2, 212),
        "2026-11-02": (2, 212),
    }.items():
      rows.append([date, "Hormuz", h, round(h / 60, 2)])
      rows.append([date, "Malacca", m, round(m / 220, 2)])
    rows.append(["2026-11-03", "Hormuz", 2, 0.03])  # partial duplicate day
    pd.DataFrame(rows, columns=shipping_fetcher.CHOKEPOINT_COLUMNS).to_csv(
        self.tsv, sep="\t", index=False)

  @patch("shipping_fetcher.time.sleep")
  @patch("shipping_fetcher.requests.get")
  def test_arcgis_error_object_returns_none_and_tries_both_paths(
      self, get, _sleep):
    get.return_value = _resp(ARCGIS_ERROR)
    with self.assertLogs(self.fetcher.logger, level="WARNING") as logs:
      logging.disable(logging.NOTSET)
      self.assertIsNone(self.fetcher.fetch_portwatch_metrics(days=7))
    self.assertEqual(get.call_count, 2 * shipping_fetcher.PORTWATCH_RETRIES)
    paths = [c.args[0] for c in get.call_args_list]
    self.assertIn("/arcgis/rest/", paths[0])
    self.assertIn("/ArcGIS/rest/", paths[1])
    self.assertTrue(any("Invalid URL" in m for m in logs.output))
    # Failures must not be cached.
    self.assertFalse(list(self.cache_dir.glob("shipping/portwatch_daily_*")))

  @patch("shipping_fetcher.time.sleep")
  @patch("shipping_fetcher.requests.get")
  def test_outage_leaves_tsv_untouched_except_purge(self, get, _sleep):
    self._write_synthetic_tsv()
    get.return_value = _resp(ARCGIS_ERROR)
    with patch.object(config, "AISSTREAM_API_KEY", None):
      self.fetcher.generate_daily_shipping_report()
    df = pd.read_csv(self.tsv, sep="\t")
    self.assertEqual(df["Date"].max(), "2026-10-25")
    self.assertEqual(len(df), 4)
    self.assertEqual(sorted(df["Date"].unique()), ["2026-10-24", "2026-10-25"])

  @patch("shipping_fetcher.requests.get")
  def test_no_relabel_to_today_and_idempotent_merge(self, get):
    features = [{
        "attributes": {
            "date": "2026-10-25",
            "portname": "Strait of Hormuz",
            "portid": "chokepoint1",
            "n_total": 3,
            "capacity": 0,
        }
    }]
    get.return_value = _resp({"features": features})
    self.fetcher.generate_daily_shipping_report()
    self.fetcher.generate_daily_shipping_report()
    df = pd.read_csv(self.tsv, sep="\t")
    self.assertEqual(len(df), 1)
    self.assertEqual(df["Date"].max(), "2026-10-25")
    self.assertNotIn(datetime.date.today().isoformat(), df["Date"].values)

  def test_purge_synthetic_rows_is_idempotent(self):
    self._write_synthetic_tsv()
    df = pd.read_csv(self.tsv, sep="\t")
    once = ShippingFetcher.purge_synthetic_rows(df)
    twice = ShippingFetcher.purge_synthetic_rows(once)
    self.assertEqual(once["Date"].max(), "2026-10-25")
    pd.testing.assert_frame_equal(once, twice)

  @patch("shipping_fetcher.requests.get")
  def test_port_calls_parse_paginate_merge(self, get):
    ids = {
        "features": [{
            "attributes": {
                "portid": "port1",
                "portname": "Shanghai",
                "country": "China"
            }
        }]
    }
    page1 = {
        "features": [_port_feature("2026-10-29", "port1", "Shanghai", 74)],
        "exceededTransferLimit": True,
    }
    page2 = {
        "features": [_port_feature("2026-10-30", "port1", "Shanghai", 86)],
    }
    get.side_effect = [_resp(ids), _resp(page1), _resp(page2)]
    out = self.fetcher.fetch_portwatch_port_calls(days=7)
    self.assertEqual(len(out), 2)
    self.assertEqual(list(out.columns), shipping_fetcher.PORT_CALLS_COLUMNS)
    offsets = [c.kwargs["params"]["resultOffset"] for c in get.call_args_list]
    self.assertEqual(offsets, ["0", "0", "1"])
    where = get.call_args_list[1].kwargs["params"]["where"]
    self.assertIn("portid IN ('port1')", where)
    self.assertIn("date >= '", where)

    # Second run: port ids come from cache, overlapping rows are deduped.
    get.side_effect = [
        _resp({
            "features": [_port_feature("2026-10-30", "port1", "Shanghai", 90)]
        })
    ]
    self.fetcher.fetch_portwatch_port_calls(days=7)
    saved = pd.read_csv(self.test_dir / "shipping" / "port_calls.tsv", sep="\t")
    self.assertEqual(len(saved), 2)
    self.assertEqual(saved.iloc[0]["Date"], "2026-10-30")
    self.assertEqual(saved.iloc[0]["Portcalls"], 90)
    self.assertEqual(saved.iloc[0]["Import_Tons"], 10)


if __name__ == "__main__":
  unittest.main()
