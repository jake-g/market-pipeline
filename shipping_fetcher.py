import argparse
import asyncio
import datetime
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

import joblib
import pandas as pd
import requests
from tqdm import tqdm
import websockets

import config

# IMF PortWatch mapping: API portname -> (Chokepoint_Name, Baseline transits/day)
PORTWATCH_CHOKEPOINTS: Dict[str, Tuple[str, float]] = {
    "Strait of Hormuz": ("Hormuz", 60.0),
    "Taiwan Strait": ("Taiwan_Strait", 220.0),
    "Panama Canal": ("Panama_Canal", 36.0),
    "Malacca Strait": ("Malacca", 220.0),
    "Suez Canal": ("Suez_Canal", 70.0),
    "Bab el-Mandeb Strait": ("Bab_el_Mandeb", 70.0),
}

# IMF PortWatch ArcGIS FeatureServer. The hosted path casing has flipped in the
# past, so both variants are tried before giving up.
PORTWATCH_HOST = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG"
PORTWATCH_PATHS: Tuple[str, ...] = ("arcgis", "ArcGIS")
PORTWATCH_MAX_RECORDS = 1000
# The service intermittently answers "Invalid URL" / times out; retry a few
# times per path before declaring an outage.
PORTWATCH_RETRIES = 3
PORTWATCH_RETRY_SLEEP_SECONDS = 2.0
PORTWATCH_TIMEOUT_SECONDS = 30
PORTWATCH_PORT_IDS_CACHE_SECONDS = 86400 * 30

# Major ports tracked in port_calls.tsv, using native PortWatch `portname`
# values (Los Angeles and Long Beach are a single PortWatch port).
PORTWATCH_PORTS: Tuple[str, ...] = (
    "Shanghai",
    "Ningbo",
    "Singapore",
    "Busan",
    "Rotterdam",
    "Antwerp",
    "Los Angeles-Long Beach",
    "Houston (US-TX)",
    "Jebel Ali",
    "Kaohsiung",
    "Hamburg",
)
PORT_CALLS_COLUMNS = [
    "Date", "Port", "Country", "Portcalls", "Portcalls_Container",
    "Portcalls_Tanker", "Portcalls_Dry_Bulk", "Import_Tons", "Export_Tons"
]
CHOKEPOINT_COLUMNS = [
    "Date", "Chokepoint_Name", "Vessel_Count", "Congestion_Index"
]


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
      self.logger.propagate = False

  @property
  def port_calls_out_file(self) -> Path:
    """Path of the long-format port calls TSV."""
    return self.shipping_out_dir / "port_calls.tsv"

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
    """Gathers live AISstream vessel counts for today.

    Only chokepoints with a live vessel count > 0 are returned; nothing is
    carried forward or defaulted so that gaps are never disguised as data.

    Returns:
        pd.DataFrame: Today's observed chokepoint rows (may be empty).
    """
    if not config.AISSTREAM_API_KEY:
      self.logger.warning("AISSTREAM_API_KEY not set; skipping live AIS.")
      return pd.DataFrame(columns=CHOKEPOINT_COLUMNS)

    chokepoints = self._get_default_chokepoints()
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    self.logger.info("Gathering AIS data for %d chokepoints...",
                     len(chokepoints))
    rows = []
    for point_name, params in tqdm(chokepoints.items(), desc="Shipping Data"):
      vessel_data = self.fetch_chokepoint_vessels(point_name, params)
      vessel_count = len(vessel_data.get("data", [])) if vessel_data else 0
      if vessel_count <= 0:
        continue
      congestion = self.calculate_congestion_index(vessel_data or {},
                                                   params["baseline"])
      rows.append({
          "Date": today_str,
          "Chokepoint_Name": point_name,
          "Vessel_Count": vessel_count,
          "Congestion_Index": round(congestion, 2),
      })
    return pd.DataFrame(rows, columns=CHOKEPOINT_COLUMNS)

  def _portwatch_query(self, layer: str, params: Dict[str,
                                                      str]) -> Optional[Dict]:
    """Queries a PortWatch FeatureServer layer, handling ArcGIS error bodies.

    ArcGIS returns HTTP 200 with an ``{"error": {...}}`` body on failure, so
    the payload is inspected explicitly. Both path casings are attempted.

    Args:
        layer: FeatureServer service name (e.g. ``Daily_Ports_Data``).
        params: Query-string parameters; ``f=json`` is added.

    Returns:
        Optional[Dict]: Parsed JSON payload, or None if every attempt failed.
    """
    query = dict(params, f="json")
    attempts = [
        (a, p) for a in range(PORTWATCH_RETRIES) for p in PORTWATCH_PATHS
    ]
    for attempt, path in attempts:
      if attempt and path == PORTWATCH_PATHS[0]:
        time.sleep(PORTWATCH_RETRY_SLEEP_SECONDS * attempt)
      url = f"{PORTWATCH_HOST}/{path}/rest/services/{layer}/FeatureServer/0/query"
      try:
        resp = requests.get(url,
                            params=query,
                            timeout=PORTWATCH_TIMEOUT_SECONDS,
                            headers={"User-Agent": "Mozilla/5.0"})
      except requests.RequestException as e:
        self.logger.warning("PortWatch %s request failed (%s): %s", layer, path,
                            e)
        continue
      if resp.status_code != 200:
        self.logger.warning("PortWatch %s HTTP %s (%s)", layer,
                            resp.status_code, path)
        continue
      try:
        data = resp.json()
      except ValueError as e:
        self.logger.warning("PortWatch %s returned non-JSON (%s): %s", layer,
                            path, e)
        continue
      if "error" in data:
        err = data["error"]
        self.logger.warning("PortWatch %s ArcGIS error (%s): code=%s %s", layer,
                            path, err.get("code"), err.get("message"))
        continue
      return data
    return None

  def _portwatch_features(self, layer: str,
                          params: Dict[str, str]) -> Optional[List[Dict]]:
    """Fetches all feature attributes for a query, paging via resultOffset.

    Args:
        layer: FeatureServer service name.
        params: Query parameters (without paging keys).

    Returns:
        Optional[List[Dict]]: Attribute dicts, or None if the query failed.
    """
    rows: List[Dict] = []
    offset = 0
    while True:
      page = dict(params,
                  resultOffset=str(offset),
                  resultRecordCount=str(PORTWATCH_MAX_RECORDS))
      data = self._portwatch_query(layer, page)
      if data is None:
        return None
      features = data.get("features", [])
      rows.extend(f["attributes"] for f in features if "attributes" in f)
      if not data.get("exceededTransferLimit") or not features:
        return rows
      offset += len(features)

  def fetch_portwatch_metrics(self, days: int = 90) -> Optional[pd.DataFrame]:
    """Fetches real daily maritime chokepoint transit counts from IMF PortWatch.

    Args:
        days: Lookback window in days.

    Returns:
        Optional[pd.DataFrame]: Rows with native PortWatch dates, or None when
        the service is unavailable. Failures are never cached.
    """
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    cache_key = f"portwatch_daily_{today.strftime('%Y%m%d')}"
    cached = self._load_cache(cache_key, expiry_seconds=3600 * 6)
    if isinstance(cached, pd.DataFrame) and not cached.empty:
      return cached

    params = {
        "where": f"date >= '{start_date}'",
        "outFields": "date,portname,portid,n_total,capacity",
        "orderByFields": "date DESC",
        "returnGeometry": "false",
    }
    rows = self._portwatch_features("Daily_Chokepoints_Data", params)
    if not rows:
      self.logger.warning("IMF PortWatch chokepoint data unavailable.")
      return None

    df = pd.DataFrame(rows)
    if "portname" not in df.columns:
      return None
    df = df[df["portname"].isin(PORTWATCH_CHOKEPOINTS)].copy()
    if df.empty:
      return None
    df["Chokepoint_Name"] = df["portname"].map(
        lambda p: PORTWATCH_CHOKEPOINTS[p][0])
    df["Baseline"] = df["portname"].map(lambda p: PORTWATCH_CHOKEPOINTS[p][1])
    df["Date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["Vessel_Count"] = df["n_total"].fillna(0).astype(int)
    df["Congestion_Index"] = (df["Vessel_Count"] / df["Baseline"]).round(2)
    out_df = df[CHOKEPOINT_COLUMNS].sort_values(["Date", "Chokepoint_Name"],
                                                ascending=[False, True])
    self._save_cache(cache_key, out_df)
    self.logger.info(
        "Fetched %d real chokepoint transit records from PortWatch.",
        len(out_df))
    return out_df

  @staticmethod
  def purge_synthetic_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drops trailing carry-forward duplicates from chokepoint rows.

    Earlier versions relabelled the latest PortWatch rows with today's date.
    Walking dates in ascending order, a date is synthetic when every one of its
    (chokepoint, Vessel_Count, Congestion_Index) tuples equals the most recent
    prior observation. Only the trailing run of such dates is removed, so the
    last genuine observation date becomes the max Date. Safe to rerun.

    Args:
        df: Chokepoint rows with CHOKEPOINT_COLUMNS.

    Returns:
        pd.DataFrame: Rows with the synthetic tail removed.
    """
    if df.empty:
      return df
    last_seen: Dict[str, Tuple[int, float]] = {}
    synthetic_dates: List[str] = []
    for date, grp in df.sort_values("Date").groupby("Date", sort=True):
      names: List[str] = grp["Chokepoint_Name"].astype(str).tolist()
      counts: List[int] = grp["Vessel_Count"].astype(int).tolist()
      idx: List[float] = grp["Congestion_Index"].astype(float).tolist()
      vals = dict(zip(names, zip(counts, idx)))
      is_dup = bool(last_seen) and all(
          last_seen.get(k) == v for k, v in vals.items())
      synthetic_dates = synthetic_dates + [str(date)] if is_dup else []
      last_seen.update(vals)
    return df[~df["Date"].isin(synthetic_dates)]

  def generate_daily_shipping_report(self) -> None:
    """Merges native-dated PortWatch chokepoint rows into the TSV.

    Rows are never relabelled to today. When PortWatch is unavailable the TSV
    is left untouched (apart from synthetic-row cleanup) unless AISstream is
    configured and returns live counts.
    """
    existing = pd.DataFrame(columns=CHOKEPOINT_COLUMNS)
    if self.shipping_out_file.exists():
      existing = pd.read_csv(self.shipping_out_file, sep="\t")
      cleaned = self.purge_synthetic_rows(existing)
      if len(cleaned) != len(existing):
        self.logger.warning("Purged %d synthetic carry-forward rows from %s",
                            len(existing) - len(cleaned),
                            self.shipping_out_file.name)
      existing = cleaned

    new_df = self.fetch_portwatch_metrics(days=90)
    if new_df is None or new_df.empty:
      last_date = existing["Date"].max() if not existing.empty else None
      stale = ((datetime.date.today() -
                datetime.date.fromisoformat(last_date)).days
               if last_date else -1)
      self.logger.warning(
          "PortWatch chokepoints unavailable; last observed date = %s "
          "(%d days stale)", last_date, stale)
      new_df = self.gather_daily_metrics()
      if new_df.empty:
        self.logger.warning("No live AIS counts; chokepoint TSV not updated.")
        if not existing.empty:
          self._write_chokepoints(existing)
        return

    self._write_chokepoints(pd.concat([existing, new_df], ignore_index=True))

  def _write_chokepoints(self, df: pd.DataFrame) -> None:
    """Deduplicates on (Date, Chokepoint_Name) and writes the TSV."""
    final_df = df.drop_duplicates(subset=["Date", "Chokepoint_Name"],
                                  keep="last")
    final_df = final_df.sort_values(by=["Date", "Chokepoint_Name"],
                                    ascending=[False, True])
    final_df.to_csv(self.shipping_out_file, sep="\t", index=False)
    self.logger.info("Saved shipping metrics to %s (latest date %s)",
                     self.shipping_out_file.name, final_df["Date"].max())

  def fetch_portwatch_port_ids(self) -> Dict[str, Tuple[str, str]]:
    """Resolves PORTWATCH_PORTS names to PortWatch port ids (cached 30 days).

    Returns:
        Dict[str, Tuple[str, str]]: portname -> (portid, country).
    """
    cache_key = "portwatch_port_ids"
    cached = self._load_cache(cache_key,
                              expiry_seconds=PORTWATCH_PORT_IDS_CACHE_SECONDS)
    if isinstance(cached, dict) and cached:
      return cached

    names = ",".join(f"'{p}'" for p in PORTWATCH_PORTS)
    params = {
        "where": f"portname IN ({names})",
        "outFields": "portid,portname,country",
        "returnGeometry": "false",
    }
    rows = self._portwatch_features("PortWatch_ports_database", params)
    if not rows:
      return {}
    ids = {r["portname"]: (r["portid"], r.get("country", "")) for r in rows}
    missing = sorted(set(PORTWATCH_PORTS) - set(ids))
    if missing:
      self.logger.warning("PortWatch port ids not found for: %s", missing)
    self._save_cache(cache_key, ids)
    return ids

  def fetch_portwatch_port_calls(self,
                                 days: int = 90) -> Optional[pd.DataFrame]:
    """Fetches daily port calls for major ports and merges into port_calls.tsv.

    Args:
        days: Lookback window in days (use 365 for a backfill).

    Returns:
        Optional[pd.DataFrame]: Newly fetched long-format rows, or None if
        PortWatch was unavailable.
    """
    port_ids = self.fetch_portwatch_port_ids()
    if not port_ids:
      self.logger.warning(
          "No PortWatch port ids resolved; skipping port calls.")
      return None

    start = (datetime.date.today() -
             datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    out_fields = ("date,portid,portname,country,portcalls,"
                  "portcalls_container,portcalls_tanker,"
                  "portcalls_dry_bulk,import,export")
    # One query per port: the service is flaky, so partial progress is kept
    # and gaps are filled idempotently on the next run.
    rows: List[Dict] = []
    failed: List[str] = []
    for name, (pid, _) in port_ids.items():
      params = {
          "where": f"portid IN ('{pid}') AND date >= '{start}'",
          "outFields": out_fields,
          "orderByFields": "date ASC",
          "returnGeometry": "false",
      }
      port_rows = self._portwatch_features("Daily_Ports_Data", params)
      if port_rows is None:
        failed.append(name)
      else:
        rows.extend(port_rows)
    if failed:
      self.logger.warning("PortWatch port calls failed for: %s", failed)
    if not rows:
      self.logger.warning("PortWatch port calls unavailable.")
      return None

    df = pd.DataFrame(rows).rename(
        columns={
            "date": "Date",
            "portname": "Port",
            "country": "Country",
            "portcalls": "Portcalls",
            "portcalls_container": "Portcalls_Container",
            "portcalls_tanker": "Portcalls_Tanker",
            "portcalls_dry_bulk": "Portcalls_Dry_Bulk",
            "import": "Import_Tons",
            "export": "Export_Tons",
        })
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df = df[PORT_CALLS_COLUMNS]

    if self.port_calls_out_file.exists():
      existing = pd.read_csv(self.port_calls_out_file, sep="\t")
      merged = pd.concat([existing, df], ignore_index=True)
    else:
      merged = df
    merged = merged.drop_duplicates(subset=["Date", "Port"], keep="last")
    merged = merged.sort_values(["Date", "Port"], ascending=[False, True])
    merged.to_csv(self.port_calls_out_file, sep="\t", index=False)
    self.logger.info("Saved %d port-call rows to %s (latest date %s)",
                     len(merged), self.port_calls_out_file.name,
                     merged["Date"].max())
    return df


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


def main() -> None:
  """CLI entrypoint: chokepoints, port calls, then tariffs."""
  parser = argparse.ArgumentParser(description="Run Shipping & Tariff Fetchers")
  parser.add_argument("--backfill",
                      action="store_true",
                      help="Fetch deep history (port calls: 365 days)")
  args = parser.parse_args()
  logger = logging.getLogger("shipping_fetcher")
  start = time.time()

  t0 = time.time()
  shipping_fetcher = ShippingFetcher()
  shipping_fetcher.generate_daily_shipping_report()
  shipping_fetcher.fetch_portwatch_port_calls(days=365 if args.backfill else 90)
  logger.info("[Shipping] Daily shipping report generated in %ds",
              int(time.time() - t0))

  t0 = time.time()
  tariff_fetcher = TariffFetcher()
  tariff_fetcher.generate_tariff_report(backfill=args.backfill)
  logger.info("[Shipping] Tariff report generated in %ds",
              int(time.time() - t0))
  logger.info("Total Shipping Fetcher execution time: %ds",
              int(time.time() - start))


if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO, format="%(message)s")
  main()
