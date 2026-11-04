# market_data/shipping

Outputs of `shipping_fetcher.py` (run via `make shipping-fetch`; use
`venv/bin/python shipping_fetcher.py --backfill` for a 365-day port backfill).

- `chokepoint_metrics.tsv` — daily transit counts and congestion index
  (`Vessel_Count / baseline`) for Hormuz, Malacca, Suez, Bab el-Mandeb,
  Panama and Taiwan Strait from IMF PortWatch `Daily_Chokepoints_Data`.
  Columns: `Date, Chokepoint_Name, Vessel_Count, Congestion_Index`.
- `port_calls.tsv` — daily port calls for major ports (Shanghai, Ningbo,
  Singapore, Busan, Rotterdam, Antwerp, Los Angeles-Long Beach,
  Houston, Jebel Ali, Kaohsiung, Hamburg) from IMF PortWatch
  `Daily_Ports_Data`. Long format, one row per (Date, Port):
  `Date, Port, Country, Portcalls, Portcalls_Container, Portcalls_Tanker,
  Portcalls_Dry_Bulk, Import_Tons, Export_Tons`. Port ids are resolved from
  `PortWatch_ports_database` and cached 30 days under `.cache/shipping/`.
- `tariffs.tsv`, `shipping_macro.tsv` — tariff events and FRED freight series
  (`TariffFetcher`).

## Staleness policy

Rows carry the **native PortWatch observation date only**; nothing is ever
relabelled to today or carried forward. If PortWatch is down (its ArcGIS
endpoint returns HTTP 200 with an `error` body), the fetcher logs
`PortWatch chokepoints unavailable; last observed date = X (N days stale)` and
leaves the TSV untouched. Live AISstream counts are written only when
`AISSTREAM_API_KEY` is set and a chokepoint reports > 0 vessels. A trailing
run of dates whose values all equal the previous observation (legacy
synthetic duplicates) is purged on every run. `SHIPPING_REPORT.md` prints
`Data as of` and a warning when the latest date is more than 3 days old.
