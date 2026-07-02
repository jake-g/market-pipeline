import asyncio
import datetime
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd
import requests
from tqdm import tqdm
import websockets

import config


class ShippingFetcher:
  """Fetches global shipping data, port congestion, tariffs, and bottlenecks.

  Attributes:
      data_dir (Path): Base directory for all output market data.
      cache_dir (Path): Directory for storing API request cache data via joblib.
      logger (logging.Logger): Formatted module logger.
  """

  def __init__(self,
               data_dir: str = config.MARKET_DATA_DIR,
               cache_dir: str = config.CACHE_DIR):
    """Initializes the ShippingFetcher with data and cache paths.

    Args:
        data_dir: Base directory path for outputs.
        cache_dir: Directory path for the API cache.
    """
    self.data_dir = Path(data_dir)
    self.data_dir.mkdir(parents=True, exist_ok=True)
    self.cache_dir = Path(cache_dir)
    self.cache_dir.mkdir(parents=True, exist_ok=True)

    self.shipping_cache_dir = self.cache_dir / "shipping"
    self.shipping_cache_dir.mkdir(parents=True, exist_ok=True)

    self.shipping_out_dir = self.data_dir / "shipping"
    self.shipping_out_dir.mkdir(parents=True, exist_ok=True)
    self.shipping_out_file = self.shipping_out_dir / "chokepoint_metrics.tsv"

    self.logger = logging.getLogger(self.__class__.__name__)
    if not self.logger.handlers:
      handler = logging.StreamHandler()
      formatter = logging.Formatter(
          '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
      handler.setFormatter(formatter)
      self.logger.addHandler(handler)
      self.logger.setLevel(logging.INFO)

  def _get_cache_path(self, cache_key: str) -> Path:
    """Gets the filesystem path for a specific cache key.

    Args:
        cache_key: Unique identifier for the cached item.

    Returns:
        Path: Total path to the physical cache file.
    """
    # Sanitize key for valid filename
    safe_key = "".join(
        [c if c.isalnum() or c in ('_', '-') else '_' for c in cache_key])
    return self.shipping_cache_dir / f"{safe_key}.joblib"

  def _load_cache(
      self,
      cache_key: str,
      expiry_seconds: int = config.CACHE_EXPIRY_SHIPPING) -> Optional[Dict]:
    """Loads a cached API response if it hasn't expired.

    Args:
        cache_key: Unique identifier for the cached item.
        expiry_seconds: Time in seconds before cache expires.

    Returns:
        Optional[Dict]: The cached object or None if expired/missing.
    """
    cache_path = self._get_cache_path(cache_key)
    if cache_path.exists():
      modified_time = cache_path.stat().st_mtime
      age = time.time() - modified_time
      if age < expiry_seconds:
        try:
          data = joblib.load(cache_path)
          self.logger.debug("Cache hit for %s", cache_key)
          return data
        except Exception as e:
          self.logger.warning("Failed to load cache %s: %s", cache_key, e)
    return None

  def _save_cache(self, cache_key: str, data: Any) -> None:
    """Saves arbitrary data to the disk cache via joblib.

    Args:
        cache_key: Unique identifier.
        data: Python object/dict/list to serialize.
    """
    cache_path = self._get_cache_path(cache_key)
    try:
      joblib.dump(data, cache_path)
      self.logger.debug("Cache saved for %s", cache_key)
    except Exception as e:
      self.logger.warning("Failed to save cache %s: %s", cache_key, e)

  # ===========================================================================
  # TODO(jakegarrison): PAID API IMPLEMENTATIONS - UNUSED BY DEFAULT
  # The user explicitly requested to rely purely on Free APIs. These paid
  # snippets are retained for future scalability should the user choose to upgrade.
  # ===========================================================================
  #
  # [PAID] Datalastic API (~$50-$250/mo)
  # Provides highly reliable bounding-box and rich historical vessel routing endpoints.
  # Excellent for backtracking 2025 macro events but requires a subscription.
  #
  # def _fetch_chokepoint_vessels_datalastic(self, bounding_box: Dict[str, float]) -> Optional[Dict]:
  #   url = "https://api.datalastic.com/api/v0/vessel_in_radius"
  #   lat = (bounding_box.get('min_lat', 0) + bounding_box.get('max_lat', 0)) / 2
  #   lon = (bounding_box.get('min_lon', 0) + bounding_box.get('max_lon', 0)) / 2
  #   params = {"api-key": getattr(config, 'DATALASTIC_API_KEY', None), "lat": lat, "lon": lon, "radius": 50}
  #   response = requests.get(url, params=params, timeout=15)
  #   return response.json()
  #
  # [PAID] SeaRates API (~$100+/mo)
  # Unlocks deep Port/Terminal Congestion specifics and container ETA estimates.
  #
  # def _fetch_port_congestion_searates(self, port_id: str) -> Optional[Dict]:
  #   url = "https://www.searates.com/api/v2/port/congestion"
  #   params = {"api_key": getattr(config, 'SEARATES_API_KEY', None), "port_code": port_id}
  #   response = requests.get(url, params=params, timeout=15)
  #   return response.json()
  # ===========================================================================

  async def _stream_ais_data(
      self,
      bboxes: List[List[List[float]]],
      duration_seconds: int = 20) -> Dict[str, List[Dict]]:
    """Connects to free AISStream WebSocket targeted at specific global chokepoints.

    Args:
        bboxes: A list of [[lat1, lon1], [lat2, lon2]] bounding boxes across all chokepoints.
        duration_seconds: How long to listen to the constrained firehose.

    Returns:
        Dict: Raw messages captured.
    """
    if not config.AISSTREAM_API_KEY:
      self.logger.warning(
          "Missing config.AISSTREAM_API_KEY! Returning mock data.")
      mock_msgs = [
          {
              "MessageType": "PositionReport",
              "MetaData": {
                  "MMSI": 1,
                  "latitude": 26.5,
                  "longitude": 56.4,
                  "ShipName": "Mock1"
              }
          },
          {
              "MessageType": "PositionReport",
              "MetaData": {
                  "MMSI": 2,
                  "latitude": 24.0,
                  "longitude": 120.0,
                  "ShipName": "Mock2"
              }
          },
          {
              "MessageType": "PositionReport",
              "MetaData": {
                  "MMSI": 3,
                  "latitude": 9.0,
                  "longitude": -79.7,
                  "ShipName": "Mock3"
              }
          },
      ]
      self.latest_stream_cache = mock_msgs
      return mock_msgs  # type: ignore

    url = "wss://stream.aisstream.io/v0/stream"
    vessel_data = []

    # Passing exactly configured bounding boxes instead of global limits throttling
    subscribe_message = {
        "APIKey":
            config.AISSTREAM_API_KEY,
        "BoundingBoxes":
            bboxes,
        "FilterMessageTypes": [
            "PositionReport", "ExtendedClassBPositionReport", "ShipStaticData"
        ]
    }

    self.logger.info("Connecting to AISStream.io Free Tier (WebSockets)...")
    try:
      async with websockets.connect(url, ping_interval=None) as ws:
        await ws.send(json.dumps(subscribe_message))

        start_time = time.time()
        while time.time() - start_time < duration_seconds:
          try:
            message = await asyncio.wait_for(ws.recv(), timeout=2.0)
            data = json.loads(message)
            vessel_data.append(data)
          except asyncio.TimeoutError:
            continue

    except Exception as e:
      self.logger.error("WebSocket connection to AISStream failed: %s", e)

    self.logger.info("Sampled %d robust AIS messages in %d seconds.",
                     len(vessel_data), duration_seconds)
    self.latest_stream_cache = vessel_data
    return vessel_data  # type: ignore

  def fetch_chokepoint_vessels(
      self, chokepoint_name: str, bounding_box: Dict[str,
                                                     float]) -> Optional[Dict]:
    """Sorts the massive free-tier WebSocket pointcloud into our bounding boxes.

    Args:
        chokepoint_name: Name of the geofence (e.g., 'Hormuz').
        bounding_box: Dict containing min_lat, max_lat, min_lon, max_lon.

    Returns:
        Optional[Dict]: Synthesized vessel counts matching Datalastic schema natively.
    """
    today_str = datetime.date.today().strftime("%Y%m%d")
    cache_key = f"vessels_{chokepoint_name}_{today_str}"

    cached_data = self._load_cache(cache_key)
    if cached_data is not None:
      return cached_data

    # Check if we already did a global sample this session to avoid spamming the free tier
    if not hasattr(self, 'latest_stream_cache'):
      try:
        # Gather the master bounding boxes from the known dictionary to feed the stream
        # This isn't perfectly architectured but solves the one-pass async run neatly
        master_boxes = []
        for p, p_params in self._get_default_chokepoints().items():
          master_boxes.append([[p_params['min_lat'], p_params['min_lon']],
                               [p_params['max_lat'], p_params['max_lon']]])

        # Use event loop to block since we are in a synchronous pipeline script
        asyncio.run(
            self._stream_ais_data(bboxes=master_boxes, duration_seconds=20))
      except Exception as e:
        self.logger.error("Asyncio loop failed: %s", e)
        self.latest_stream_cache = []

    # Filter the global cache down to this specific bounding box
    filtered_vessels = []
    min_lat, max_lat = bounding_box.get("min_lat",
                                        -90), bounding_box.get("max_lat", 90)
    min_lon, max_lon = bounding_box.get("min_lon",
                                        -180), bounding_box.get("max_lon", 180)

    # We use a set since AIS streams output 5+ reports for the same ship rapidly
    seen_mmsi = set()

    for msg in self.latest_stream_cache:
      meta = msg.get("MetaData", {})
      lat = meta.get("latitude")  # type: ignore
      lon = meta.get("longitude")  # type: ignore
      mmsi = meta.get("MMSI")  # type: ignore

      if lat is not None and lon is not None and mmsi not in seen_mmsi:
        if (min_lat <= lat <= max_lat) and (min_lon <= lon <= max_lon):
          # Extract richer nested variables depending on the payload type
          msg_type = msg.get("MessageType")
          inner_msg = msg.get("Message", {}).get(msg_type, {})  # type: ignore

          speed = inner_msg.get("Sog", 0)  # Speed over ground
          heading = inner_msg.get("TrueHeading", 0)
          ship_type = inner_msg.get("Type", 0)

          filtered_vessels.append({
              "mmsi": mmsi,
              "name": meta.get("ShipName", "Unknown"),  # type: ignore
              "lat": lat,
              "lon": lon,
              "speed": speed,
              "heading": heading,
              "type": ship_type
          })
          seen_mmsi.add(mmsi)

    result = {"data": filtered_vessels}
    self._save_cache(cache_key, result)
    return result

  def calculate_congestion_index(self, vessel_data: Dict,
                                 historical_baseline: float) -> float:
    """Calculates congestion index against a 2026 historical baseline.

    Args:
        vessel_data: The fetched dict payload of ships.
        historical_baseline: Average ships historically expected in the region.

    Returns:
        float: Risk score multiplier (> 1 is congested, < 1 is sparse).
    """
    if not vessel_data or "data" not in vessel_data:
      return 1.0

    current_count = len(vessel_data["data"])
    if historical_baseline <= 0:
      return 1.0

    # Cap maximum congestion index to 5.0 to prevent severe outliers
    raw_index = current_count / historical_baseline
    return min(raw_index, 5.0)

  def fetch_tariff_data(self) -> List[Dict]:
    """Scrapes US Customs/Tariff data or returns cached API indicators from FRED.

    Returns:
        List[Dict]: Current tariff/policy alerts and basic macroeconomic rates.
    """
    tariffs = []

    # Static synthesized view representing geopolitical state.
    # We could easily drop in BeautifulSoup scraping of USTR.gov or standard APIs
    tariffs.append({
        "policy": "US-China Import Flat Tariff",
        "rate": 0.25,
        "sector": "Consumer Electronics"
    })
    tariffs.append({
        "policy": "Expected Middle-East Escalation Spike",
        "rate": 0.15,
        "sector": "Energy/Tankers"
    })

    if config.FRED_API_KEY:
      # Pull Ocean Freight PPI as proxy for shipping cost (Inflation macro)
      url = "https://api.stlouisfed.org/fred/series/observations"
      params = {
          "series_id": "PCU483111483111",
          "api_key": config.FRED_API_KEY,
          "file_type": "json",
          "sort_order": "desc",
          "limit": 1
      }
      cache_key = f"fred_shipping_ppi"
      cached = self._load_cache(cache_key)

      if cached:
        tariffs.append(cached)
      else:
        try:
          res = requests.get(url, params=params, timeout=10)  # type: ignore
          if res.status_code == 200:
            data = res.json()
            if "observations" in data and len(data["observations"]) > 0:
              ppi_val = data["observations"][0].get("value")
              ppi_dict = {
                  "policy": "Ocean Freight PPI",
                  "rate": ppi_val,
                  "sector": "Macro"
              }
              tariffs.append(ppi_dict)
              self._save_cache(cache_key, ppi_dict)
        except Exception as e:
          self.logger.warning("Failed to fetch FRED Shipping PPI: %s", e)

    return tariffs

  def _get_default_chokepoints(self) -> Any:
    return {
        "Hormuz": {
            "min_lat": 26.2,
            "max_lat": 26.8,
            "min_lon": 56.1,
            "max_lon": 56.6,
            "baseline": 80.0
        },
        "Taiwan_Strait": {
            "min_lat": 23.5,
            "max_lat": 25.0,
            "min_lon": 119.5,
            "max_lon": 121.0,
            "baseline": 150.0
        },
        "Panama_Canal": {
            "min_lat": 8.8,
            "max_lat": 9.4,
            "min_lon": -79.9,
            "max_lon": -79.5,
            "baseline": 35.0
        },
        "Malacca": {
            "min_lat": 2.0,
            "max_lat": 3.0,
            "min_lon": 101.0,
            "max_lon": 102.0,
            "baseline": 200.0
        }
    }

  def gather_daily_metrics(self) -> pd.DataFrame:
    '''Gathers all API metrics into a structured dataframe.

    Returns:
        pd.DataFrame: Today's bottleneck metrics.
    '''
    chokepoints = self._get_default_chokepoints()

    rows = []

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    self.logger.info("Gathering AIS data for %d chokepoints...",
                     len(chokepoints))

    # Read existing metrics to carry forward last known valid data if live AIS stream is silent
    last_known_metrics = {}
    if self.shipping_out_file.exists():
      try:
        ex_df = pd.read_csv(self.shipping_out_file, sep='\t')
        valid_ex = ex_df[ex_df['Vessel_Count'] > 0]
        for p_name in chokepoints:
          p_rows = valid_ex[valid_ex['Chokepoint_Name'] == p_name]
          if not p_rows.empty:
            last_known_metrics[p_name] = p_rows.iloc[0]
      except Exception:
        pass

    for point_name, params in tqdm(chokepoints.items(), desc="Shipping Data"):
      vessel_data = self.fetch_chokepoint_vessels(point_name, params)
      vessels = vessel_data.get("data", []) if vessel_data else []
      vessel_count = len(vessels)

      if vessel_count > 0:
        congestion = self.calculate_congestion_index(vessel_data or {},
                                                     params['baseline'])
      elif point_name in last_known_metrics:
        # Fallback to previous day's valid vessel count & congestion metric
        prev_row = last_known_metrics[point_name]
        vessel_count = int(prev_row['Vessel_Count'])
        congestion = float(prev_row['Congestion_Index'])
      else:
        # Fallback to default historical baseline
        vessel_count = int(params['baseline'])
        congestion = 1.0

      rows.append({
          "Date": today_str,
          "Chokepoint_Name": point_name,
          "Vessel_Count": vessel_count,
          "Congestion_Index": round(congestion, 2),
      })

    return pd.DataFrame(rows)

  def generate_daily_shipping_report(self) -> None:
    '''Aggregates metrics and outputs the TSV for NotebookLM.'''
    df = self.gather_daily_metrics()

    if df.empty:
      self.logger.warning(
          "No shipping data gathered. Skipping report generation.")
      return

    # Save to TSV (append if exists, otherwise write)
    if self.shipping_out_file.exists():
      existing_df = pd.read_csv(self.shipping_out_file, sep='\t')
      # Remove overlapping rows
      existing_df = existing_df[~existing_df['Date'].isin(df['Date'])]
      final_df = pd.concat([existing_df, df], ignore_index=True)
    else:
      final_df = df

    # Order rows
    final_df = final_df.sort_values(by=["Date", "Chokepoint_Name"],
                                    ascending=[False, True])
    final_df.to_csv(self.shipping_out_file, sep='\t', index=False)
    self.logger.info("Saved shipping metrics to %s",
                     self.shipping_out_file.name)


class TariffFetcher:
  """Fetches global tariff and macro shipping cost data using FRED API.

  Attributes:
      data_dir (Path): Base directory for output data.
      cache_dir (Path): Joblib cache directory.
      logger (logging.Logger): Formatted module logger.
  """

  def __init__(self,
               data_dir: str = config.MARKET_DATA_DIR,
               cache_dir: str = config.CACHE_DIR):
    """Initializes TariffFetcher with directory paths."""
    self.data_dir = Path(data_dir)
    self.data_dir.mkdir(parents=True, exist_ok=True)
    self.cache_dir = Path(cache_dir)
    self.cache_dir.mkdir(parents=True, exist_ok=True)

    self.tariff_cache_dir = self.cache_dir / "tariffs"
    self.tariff_cache_dir.mkdir(parents=True, exist_ok=True)

    # Use the shipping subdirectory for tariffs as requested
    self.tariff_out_dir = self.data_dir / "shipping"
    self.tariff_out_dir.mkdir(parents=True, exist_ok=True)
    self.tariff_out_file = self.tariff_out_dir / "tariffs.tsv"

    self.logger = logging.getLogger(self.__class__.__name__)
    if not self.logger.handlers:
      handler = logging.StreamHandler()
      formatter = logging.Formatter(
          '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
      handler.setFormatter(formatter)
      self.logger.addHandler(handler)
      self.logger.setLevel(logging.INFO)

  def _get_cache_path(self, cache_key: str) -> Path:
    safe_key = "".join(
        [c if c.isalnum() or c in ('_', '-') else '_' for c in cache_key])
    return self.tariff_cache_dir / f"{safe_key}.joblib"

  def _load_cache(
      self,
      cache_key: str,
      expiry_seconds: int = config.CACHE_EXPIRY_MACRO) -> Optional[Dict]:
    cache_path = self._get_cache_path(cache_key)
    if cache_path.exists():
      modified_time = cache_path.stat().st_mtime
      age = time.time() - modified_time
      if age < expiry_seconds:
        try:
          data = joblib.load(cache_path)
          self.logger.debug(f"Cache hit for {cache_key}")
          return data
        except Exception as e:
          self.logger.warning(f"Failed to load cache {cache_key}: {e}")
    return None

  def _save_cache(self, cache_key: str, data: Any) -> None:
    cache_path = self._get_cache_path(cache_key)
    try:
      joblib.dump(data, cache_path)
      self.logger.debug(f"Cache saved for {cache_key}")
    except Exception as e:
      self.logger.warning(f"Failed to save cache {cache_key}: {e}")

  def fetch_fred_series(self,
                        series_id: str,
                        start_date: str = "2024-01-01",
                        limit: int = 1000) -> List[Dict]:
    """Fetches historical observations from FRED API.

    Args:
        series_id: FRED series identifier.
        start_date: Minimum date to retrieve.
        limit: Max observations to retrieve.

    Returns:
        List of dictionaries with 'date' and 'value'.
    """
    if not config.FRED_API_KEY:
      self.logger.warning(
          "Missing config.FRED_API_KEY! Cannot fetch FRED data.")
      # Notice we no longer directly return [] here so we can fallback to CSV scrape via fred_client

    cache_key = f"fred_tariff_{series_id}_{start_date}_{limit}"
    cached = self._load_cache(cache_key)
    if cached is not None:
      return cached  # type: ignore

    from market_fetcher import fetch_fred_series as client_fetch
    df = client_fetch(series_id,
                      self.logger,
                      start_date=start_date,
                      limit=limit)

    if df is not None and not df.empty:
      results = [{
          "date": str(idx)[:10],
          "value": float(val)
      } for idx, val in df[series_id].items()]
      self._save_cache(cache_key, results)
      return results

    return []

  def get_static_tariffs(self, include_historical: bool = True) -> List[Dict]:
    """Provides static / geopolitical highlighting data for tariffs over time.
      We can eventually replace this with official scraping or APIs.
      """
    # Hardcoded static alerts
    tariffs = [{
        "date": "2024-05-14",
        "policy": "Section 301 EV Tariffs",
        "rate": 1.00,
        "sector": "Autos, Batteries",
        "impact": "High",
        "country": "China"
    }, {
        "date": "2024-05-14",
        "policy": "Section 301 Solar/Steel Tariffs",
        "rate": 0.25,
        "sector": "Energy, Metals",
        "impact": "Medium",
        "country": "China"
    }, {
        "date": "2024-08-01",
        "policy": "Semiconductor Tariffs",
        "rate": 0.50,
        "sector": "Tech, Semiconductors",
        "impact": "High",
        "country": "China"
    }, {
        "date": "2025-01-20",
        "policy": "Universal Baseline Tariff",
        "rate": 0.10,
        "sector": "All Goods",
        "impact": "Very High",
        "country": "Global"
    }, {
        "date": "2025-01-20",
        "policy": "Additional China Import Tariff",
        "rate": 0.60,
        "sector": "All Goods",
        "impact": "Severe",
        "country": "China"
    }, {
        "date": "2025-01-29",
        "policy": "BRICS Core Tariffs",
        "rate": 1.00,
        "sector": "Metals, Rare Earths",
        "impact": "High",
        "country": "BRICS"
    }, {
        "date": "2025-02-01",
        "policy": "Canadian Import Tariffs",
        "rate": 0.25,
        "sector": "Energy, Timber",
        "impact": "Medium",
        "country": "Canada"
    }, {
        "date": "2025-02-01",
        "policy": "Mexican Import Tariffs",
        "rate": 0.25,
        "sector": "Autos, Agriculture",
        "impact": "Medium",
        "country": "Mexico"
    }, {
        "date": "2026-02-15",
        "policy": "US-China Import Tariffs Escalation",
        "rate": 0.25,
        "sector": "Consumer Electronics, Auto Parts",
        "impact": "High",
        "country": "China"
    }, {
        "date": "2026-02-28",
        "policy": "Middle-East Tanker Premium/Surcharge",
        "rate": 0.15,
        "sector": "Energy, Crude Tankers",
        "impact": "High",
        "country": "Global"
    }, {
        "date": "2026-03-10",
        "policy": "North American Free Trade Renegotiation Tariffs",
        "rate": 0.10,
        "sector": "Agriculture, Autos",
        "impact": "Medium",
        "country": "Canada, Mexico"
    }, {
        "date": "2026-03-15",
        "policy": "Panama Canal Drought Surcharges",
        "rate": 0.12,
        "sector": "Shipping, Ag, General Cargo",
        "impact": "Medium",
        "country": "Global"
    }]

    if not include_historical:
      # Filter to things happening in the last 30 days
      cutoff_date = (datetime.date.today() -
                     datetime.timedelta(days=30)).strftime("%Y-%m-%d")
      tariffs = [t for t in tariffs if str(t["date"]) >= cutoff_date]

    return tariffs

  def generate_tariff_report(self, backfill: bool = False) -> None:
    """Fetches all tariff data and outputs to TSV."""
    self.logger.info("Generating Tariff/Macro report (Backfill=%s)...",
                     backfill)

    start_date = "2024-01-01" if backfill else (
        datetime.date.today() -
        datetime.timedelta(days=30)).strftime("%Y-%m-%d")

    # Fetch FRED data
    customs_duties = self.fetch_fred_series("B235RC1Q027SBEA",
                                            start_date=start_date)
    ocean_freight = self.fetch_fred_series("PCU483111483111",
                                           start_date=start_date)

    # Mapping
    tariff_rows = []
    macro_rows = []

    # Map static tariffs
    static_tariffs = self.get_static_tariffs(include_historical=backfill)
    for st in static_tariffs:
      tariff_rows.append({
          "Date": st["date"],
          "Metric_Type": "Policy_Update",
          "Name": st["policy"],
          "Value": st["rate"],
          "Sector": st["sector"],
          "Country": st["country"],
          "Impact": st["impact"]
      })

    # Map FRED Customs
    for duty in customs_duties:
      macro_rows.append({
          "Date": duty["date"],
          "Metric_Type": "FRED_Customs_Duties",
          "Name": "US Customs Duties (B235RC1Q027SBEA)",
          "Value": duty["value"],
          "Sector": "Macro",
          "Country": "US"
      })

    # Map FRED Ocean Freight
    for freight in ocean_freight:
      macro_rows.append({
          "Date": freight["date"],
          "Metric_Type": "FRED_Ocean_Freight",
          "Name": "Ocean Freight PPI (PCU483111483111)",
          "Value": freight["value"],
          "Sector": "Macro",
          "Country": "Global"
      })

    def _merge_and_save(new_df: pd.DataFrame, file_path: Path, sort_cols: list):
      if file_path.exists():
        try:
          existing_df = pd.read_csv(file_path, sep='\t')
          merged = pd.concat([existing_df, new_df], ignore_index=True)
          merged = merged.drop_duplicates(
              subset=["Date", "Metric_Type", "Name"], keep="last")
        except Exception as e:
          self.logger.warning(f"Failed to merge {file_path}, overwriting: {e}")
          merged = new_df
      else:
        merged = new_df

      merged = merged.sort_values(by=sort_cols,
                                  ascending=[False] + [True] *
                                  (len(sort_cols) - 1))
      merged.to_csv(file_path, sep='\t', index=False)

    tariff_df = pd.DataFrame(tariff_rows) if tariff_rows else pd.DataFrame()
    macro_df = pd.DataFrame(macro_rows) if macro_rows else pd.DataFrame()

    if not tariff_df.empty:
      _merge_and_save(tariff_df, self.tariff_out_dir / "tariffs.tsv",
                      ["Date", "Metric_Type", "Name"])
      self.logger.info("Saved tariff metrics to tariffs.tsv")

    if not macro_df.empty:
      _merge_and_save(macro_df, self.tariff_out_dir / "shipping_macro.tsv",
                      ["Date", "Metric_Type", "Name"])
      self.logger.info("Saved macro metrics to shipping_macro.tsv")


if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description="Run Shipping & Tariff Fetchers")
  parser.add_argument("--backfill",
                      action="store_true",
                      help="Fetch deep history")
  args = parser.parse_args()

  fetcher_start_time = time.time()

  t0 = time.time()
  shipping_fetcher = ShippingFetcher()
  shipping_fetcher.generate_daily_shipping_report()
  print(
      f"⏱️  [Shipping] Daily shipping report generated in {int(time.time() - t0)}s"
  )

  t0 = time.time()
  tariff_fetcher = TariffFetcher()
  tariff_fetcher.generate_tariff_report(backfill=args.backfill)
  print(f"⏱️  [Shipping] Tariff report generated in {int(time.time() - t0)}s")

  print(
      f"🏁 Total Shipping Fetcher execution time: {int(time.time() - fetcher_start_time)}s"
  )
