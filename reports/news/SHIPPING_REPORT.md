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
| Hormuz        |         1 |               0.02 |
| Bab_el_Mandeb |        20 |               0.29 |
| Suez_Canal    |        33 |               0.47 |
| Panama_Canal  |        25 |               0.69 |
| Malacca       |       233 |               1.06 |
| Taiwan_Strait |       240 |               1.09 |

Data as of 2026-11-22

## Major Port Calls (7-day avg vs prior 4 weeks)
| Port                   | Country                  | Last Date   |   7d Avg Calls |   4w Avg Calls | Δ%     |   Container 7d |   Tanker 7d |
|------------------------|--------------------------|-------------|----------------|----------------|--------|----------------|-------------|
| Singapore              | Singapore                | 2026-11-20  |          117.7 |          117.1 | +0.5%  |           33.6 |        71.1 |
| Rotterdam              | The Netherlands          | 2026-11-20  |           79.1 |           79.5 | -0.4%  |           17   |        42   |
| Shanghai               | China                    | 2026-11-20  |           71.6 |           77.2 | -7.3%  |           30.4 |        11.9 |
| Antwerp                | Belgium                  | 2026-11-20  |           56.1 |           53.6 | +4.8%  |           13   |        31.7 |
| Ningbo                 | China                    | 2026-11-20  |           47.4 |           45.7 | +3.8%  |           29.1 |        10.6 |
| Busan                  | Korea                    | 2026-11-20  |           45.3 |           46.5 | -2.5%  |           27.9 |         6.9 |
| Kaohsiung              | Taiwan Province of China | 2026-11-20  |           26.9 |           26.8 | +0.3%  |           16.7 |         4   |
| Houston (US-TX)        | United States            | 2026-11-20  |           19.6 |           21.5 | -9.0%  |            2.6 |        13.1 |
| Hamburg                | Germany                  | 2026-11-20  |           18.3 |           16   | +14.0% |            9.4 |         4.3 |
| Los Angeles-Long Beach | United States            | 2026-11-20  |            9   |           10   | -9.7%  |            4.3 |         2.6 |
| Jebel Ali              | United Arab Emirates     | 2026-11-20  |            4.3 |            5   | -13.7% |            1.6 |         0.7 |

Source: IMF PortWatch `Daily_Ports_Data` (`port_calls.tsv`).

## Shipping Macro Metrics
| Metric                              |   Latest | YoY Chg       | Date       |
|-------------------------------------|----------|---------------|------------|
| Ocean Freight PPI (PCU483111483111) |   572.97 | (+36.20% YoY) | 2026-10-01 |
| US Customs Duties (B235RC1Q027SBEA) |   275.3  | (-17.51% YoY) | 2026-07-01 |
