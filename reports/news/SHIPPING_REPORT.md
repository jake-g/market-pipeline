# Maritime Shipping Report

## Overview
This report monitors global maritime chokepoints (Strait of Hormuz, Malacca Strait, Suez Canal, Bab el-Mandeb, Panama Canal, Taiwan Strait) and macroeconomic freight indicators to track supply chain bottlenecks, tanker availability, and logistical disruptions.

> [!NOTE]
> Chokepoint transit counts and congestion indices are sourced from IMF PortWatch daily transit calls data (covering Hormuz, Malacca, Suez, Bab el-Mandeb, Panama, and Taiwan Strait). Baseline indices reflect normalized pre-disruption transit volume (1.0 = normal baseline).

## Congestion Trends
![Congestion Timeline](rendered/shipping_timeline.png)

## Chokepoint Status
| Chokepoint    |   Vessels |   Congestion Index |
|---------------|-----------|--------------------|
| Hormuz        |         3 |               0.05 |
| Bab_el_Mandeb |        24 |               0.34 |
| Panama_Canal  |        22 |               0.61 |
| Suez_Canal    |        43 |               0.61 |
| Malacca       |       231 |               1.05 |
| Taiwan_Strait |       237 |               1.08 |

Data as of 2026-11-08

> [!WARNING]
> Chokepoint data is **4 days stale** (last observation 2026-11-08). The IMF PortWatch `Daily_Chokepoints_Data` service is currently returning errors; values above are the last real observations and are **not** carried forward as current.

## Major Port Calls (7-day avg vs prior 4 weeks)
| Port                   | Country                  | Last Date   |   7d Avg Calls |   4w Avg Calls | Δ%     |   Container 7d |   Tanker 7d |
|------------------------|--------------------------|-------------|----------------|----------------|--------|----------------|-------------|
| Singapore              | Singapore                | 2026-11-06  |          114   |          117.6 | -3.1%  |           33   |        70.1 |
| Rotterdam              | The Netherlands          | 2026-11-06  |           81   |           81   | -0.0%  |           18.3 |        41   |
| Shanghai               | China                    | 2026-11-06  |           77.9 |           77.5 | +0.5%  |           30.1 |        15.7 |
| Antwerp                | Belgium                  | 2026-11-06  |           58.7 |           52   | +12.8% |           12.6 |        32   |
| Ningbo                 | China                    | 2026-11-06  |           48.9 |           45.3 | +7.8%  |           27.9 |        12   |
| Busan                  | Korea                    | 2026-11-06  |           47   |           46.9 | +0.3%  |           27.6 |         7.1 |
| Kaohsiung              | Taiwan Province of China | 2026-11-06  |           30.7 |           26.2 | +17.0% |           18.4 |         3.9 |
| Houston (US-TX)        | United States            | 2026-11-06  |           20.7 |           20.6 | +0.5%  |            3   |        13.3 |
| Hamburg                | Germany                  | 2026-11-06  |           17.6 |           16.1 | +8.8%  |            9.7 |         3.6 |
| Los Angeles-Long Beach | United States            | 2026-11-06  |            8.9 |            9.8 | -9.8%  |            4.3 |         2.3 |
| Jebel Ali              | United Arab Emirates     | 2026-11-06  |            4.6 |            4.6 | +0.0%  |            1.6 |         0.9 |

Source: IMF PortWatch `Daily_Ports_Data` (`port_calls.tsv`).

## Shipping Macro Metrics
| Metric                              |   Latest | YoY Chg       | Date       |
|-------------------------------------|----------|---------------|------------|
| Ocean Freight PPI (PCU483111483111) |    534.8 | (+36.79% YoY) | 2026-09-01 |
| US Customs Duties (B235RC1Q027SBEA) |    275.3 | (-17.51% YoY) | 2026-07-01 |
