# 🌐 Macroeconomic & Social-Political Indicators Dataset (`economic_indicators.tsv`)

## Overview
This directory contains the primary macro time-series database (`economic_indicators.tsv`) powering the market pipeline's intrinsic valuation models, technical analysis utilities, LLM NotebookLM contextual synthesis, and risk critique engines.

## 📈 Summary Statistics
* **Historical Date Range:** `1913-01-01` to `2026-12-01` (**113+ years** of continuous observations)
* **Total Rows:** `21,600` daily & monthly records
* **Total Metrics:** `52` indicator columns
* **Data Integrity:** All lower-frequency monthly/quarterly series are daily forward-filled (`ffill()`) to ensure complete daily coverage.

---

## 📋 Comprehensive Column Directory

| Column Name | Category | FRED Series ID | Historical Start | Min Value | Max Value | Latest Value | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `FREIGHT_PPI` | Supply Chain | `PCU483111483111` | `1988-06-01` | `100.0` | `468.16` | `466.38` | Ocean Freight Transportation PPI Index |
| `AIR_PPI` | Supply Chain | `PCU481112481112` | `2003-12-01` | `97.5` | `198.48` | `198.48` | Air Freight Transportation PPI Index |
| `TRUCK_PPI` | Supply Chain | `PCU484121484121` | `2003-12-01` | `100.0` | `216.12` | `216.12` | Long-Distance Trucking PPI Index |
| `WAREHOUSE_PPI` | Supply Chain | `PCU493110493110` | `2003-12-01` | `99.3` | `178.71` | `169.44` | Warehousing & Storage PPI Index |
| `MFG_CONST` | Supply Chain | `TLMFGCONS` | `2002-01-01` | `19,703.0` | `250,233.0` | `174,764.0` | U.S. Manufacturing Construction ($M, Fabs & Data Centers) |
| `TECH_PULSE` | Supply Chain | `IPB53110S` | `1947-01-01` | `18.37` | `106.38` | `94.04` | Industrial Production: High Technology (Semis & Hardware) |
| `CHINA_IMPORTS` | Supply Chain | `IMPCH` | `1985-01-01` | `264.9` | `52,081.07` | `19,789.16` | U.S. Imports from China ($ Millions) |
| `TARIFFS` | Supply Chain | `B235RC1Q027SBEA` | `1959-01-01` | `0.95` | `364.32` | `346.15` | U.S. Customs Duties Collected ($ Billions) |
| `USD_INDEX` | Foreign Exchange | `DTWEXBGS` | `2006-01-02` | `85.47` | `130.04` | `120.89` | Nominal Broad U.S. Dollar Index |
| `USD_CNY` | Foreign Exchange | `DEXCHUS` | `1981-01-02` | `1.53` | `8.74` | `6.8` | Chinese Yuan Renminbi to U.S. Dollar Exchange Rate |
| `USD_EUR` | Foreign Exchange | `DEXUSEU` | `1999-01-04` | `0.83` | `1.6` | `1.14` | U.S. Dollars to Euro Exchange Rate |
| `USD_JPY` | Foreign Exchange | `DEXJPUS` | `1971-01-04` | `75.72` | `358.44` | `161.67` | Japanese Yen to U.S. Dollar Exchange Rate |
| `FOOD_CPI` | Agriculture & Food | `CPIUFDNS` | `1913-01-01` | `9.4` | `349.03` | `349.03` | Consumer Price Index for Food & Groceries |
| `CORN_PRICE` | Agriculture & Food | `PMAIZMTUSDM` | `1992-01-01` | `75.06` | `348.51` | `215.62` | Global Price of Corn ($/Metric Ton) |
| `WHEAT_PRICE` | Agriculture & Food | `PWHEAMTUSDM` | `1992-01-01` | `88.55` | `444.16` | `220.88` | Global Price of Wheat ($/Metric Ton) |
| `SUGAR_PRICE` | Agriculture & Food | `PSUGAISAUSDM` | `1992-01-01` | `5.11` | `29.74` | `14.87` | Global Price of Sugar (Cents/lb) |
| `WTI_CRUDE` | Energy & Grid | `DCOILWTICO` | `1986-01-02` | `-36.98` | `145.31` | `71.87` | WTI Spot Crude Oil Price ($/bbl) |
| `NAT_GAS_PRICE` | Energy & Grid | `PNGASUSUSDM` | `1992-01-01` | `1.18` | `13.63` | `2.9` | U.S. Henry Hub Spot Natural Gas Price ($/MMBtu) |
| `COPPER_PRICE` | Energy & Grid | `PCOPPUSDM` | `1992-01-01` | `1,377.38` | `13,483.75` | `13,483.75` | Global Copper Price ($/Metric Ton) |
| `ELECTRIC_POWER_INDEX` | Energy & Grid | `IPG22112S` | `1972-01-01` | `35.38` | `118.52` | `114.05` | Electric Power Generation & Grid Output Index |
| `RD_INVESTMENT` | Science & R&D | `Y006RC1Q027SBEA` | `1947-01-01` | `0.95` | `909.51` | `909.51` | Gross Domestic Investment in Research & Development ($B) |
| `US_BIRTH_RATE` | Demographics & Health | `SPDYNCBRTINUSA` | `1960-01-01` | `10.6` | `23.7` | `10.6` | U.S. Crude Birth Rate (per 1,000 people) |
| `LIFE_EXPECTANCY` | Demographics & Health | `SPDYNLE00INUSA` | `1960-01-01` | `69.77` | `78.89` | `78.89` | U.S. Life Expectancy at Birth (Years) |
| `US_POPULATION` | Demographics & Health | `POP` | `1952-01-01` | `156,309.0` | `343,289.58` | `343,289.58` | Total U.S. Population (Thousands) |
| `DISPOSABLE_INCOME` | Prosperity & Wealth | `DSPIC96` | `1959-01-01` | `2,318.4` | `20,520.0` | `17,983.8` | Real Disposable Personal Income ($ Billions) |
| `HOUSEHOLD_NET_WORTH` | Prosperity & Wealth | `TNWBSHNO` | `1945-10-01` | `806,616.0` | `182,979,889.0` | `182,979,889.0` | U.S. Household & Nonprofit Net Worth ($ Millions) |
| `CREDIT_CARD_DELINQUENCY` | Prosperity & Wealth | `DRCLACBS` | `1987-01-01` | `1.52` | `4.85` | `2.64` | Credit Card Loan Delinquency Rate (%) |
| `GDP` | Growth & Labor | `GDP` | `1947-01-01` | `243.16` | `31,865.72` | `31,865.72` | Gross Domestic Product ($ Billions) |
| `REAL_GDP` | Growth & Labor | `GDPC1` | `1947-01-01` | `2,172.43` | `24,180.42` | `24,180.42` | Real Gross Domestic Product (Chained 2017 Dollars, $B) |
| `UNRATE` | Growth & Labor | `UNRATE` | `1948-01-01` | `2.5` | `14.8` | `4.2` | U.S. Unemployment Rate (%) |
| `HOUSING_STARTS` | Growth & Labor | `HOUST` | `1959-01-01` | `478.0` | `2,494.0` | `1,177.0` | Housing Starts: Total New Privately Owned Units |
| `RECESSION_PROB` | Growth & Labor | `RECPROUSM156N` | `1967-06-01` | `0.0` | `100.0` | `0.54` | Smoothed U.S. Recession Probability (%) |
| `UMICH_SENTIMENT` | Growth & Labor | `UMCSENT` | `1952-11-01` | `44.8` | `112.0` | `44.8` | U. Michigan Consumer Sentiment Index |
| `SAVINGS_RATE` | Prosperity & Wealth | `PSAVERT` | `1959-01-01` | `1.4` | `31.8` | `3.0` | Personal Saving Rate (%) |
| `M2_MONEY` | Inflation & Money | `M2SL` | `1959-01-01` | `286.6` | `23,052.3` | `23,052.3` | M2 Money Supply ($ Billions) |
| `M2_VELOCITY` | Inflation & Money | `M2V` | `1959-01-01` | `1.13` | `2.19` | `1.41` | Velocity of M2 Money Stock |
| `FED_ASSETS` | Inflation & Money | `WALCL` | `2002-12-18` | `712,809.0` | `8,965,487.0` | `6,735,645.0` | Federal Reserve Total Balance Sheet Assets ($ Millions) |
| `CPI` | Inflation & Money | `CPIAUCSL` | `1947-01-01` | `21.48` | `333.98` | `333.98` | Consumer Price Index for All Urban Consumers |
| `FEDFUNDS` | Inflation & Money | `FEDFUNDS` | `1954-07-01` | `0.05` | `19.1` | `3.63` | Federal Funds Effective Rate (%) |
| `US02Y` | Rates & Spreads | `DGS2` | `1976-06-01` | `0.09` | `16.95` | `4.14` | 2-Year Treasury Constant Maturity Rate (%) |
| `US10Y` | Rates & Spreads | `DGS10` | `1962-01-02` | `0.52` | `15.84` | `4.44` | 10-Year Treasury Constant Maturity Rate (%) |
| `US30Y` | Rates & Spreads | `DGS30` | `1977-02-15` | `0.99` | `15.21` | `4.97` | 30-Year Treasury Constant Maturity Rate (%) |
| `HY_SPREAD` | Rates & Spreads | `BAMLH0A0HYM2` | `2023-07-03` | `2.59` | `4.61` | `2.74` | ICE BofA U.S. High Yield Option-Adjusted Spread (%) |
| `CORP_SPREAD` | Rates & Spreads | `BAMLC0A0CM` | `2023-07-03` | `0.73` | `1.33` | `0.76` | Investment Grade Corporate Bond Spread (%) |
| `BAA_SPREAD` | Rates & Spreads | `BAA10Y` | `1986-01-02` | `1.16` | `6.16` | `1.53` | Moody's Baa Corporate Spread over 10Y Treasury (%) |
| `AAA_SPREAD` | Rates & Spreads | `AAA10Y` | `1983-01-03` | `-0.44` | `3.2` | `1.11` | Moody's Aaa Corporate Spread over 10Y Treasury (%) |
| `US_POLICY_UNCERTAINTY` | Political & Geopolitical Chaos | `USEPUINDXD` | `1985-01-01` | `3.32` | `1,048.95` | `163.74` | Daily U.S. Economic Policy & Political Uncertainty Index |
| `EUROPE_POLICY_UNCERTAINTY` | Political & Geopolitical Chaos | `EUEPUINDXM` | `1987-01-01` | `33.79` | `779.27` | `353.05` | European Economic Policy Uncertainty Index |
| `GLOBAL_POLICY_UNCERTAINTY` | Political & Geopolitical Chaos | `GEPUCURRENT` | `1997-01-01` | `47.59` | `623.35` | `371.1` | Global Economic Policy Uncertainty Index |
| `ST_LOUIS_FIN_STRESS` | Political & Geopolitical Chaos | `STLFSI4` | `1993-12-31` | `-1.13` | `9.67` | `-0.64` | St. Louis Fed Financial Market Stress Index |
| `KANSAS_CITY_FIN_STRESS` | Political & Geopolitical Chaos | `KCFSI` | `1990-02-01` | `-1.06` | `5.82` | `-0.88` | Kansas City Financial Stress Index |
| `CHICAGO_FED_ACTIVITY` | Political & Geopolitical Chaos | `CFNAI` | `1967-03-01` | `-18.31` | `6.32` | `-0.1` | Chicago Fed National Activity Index (Coincident Prosperity) |

---

## 🛠️ Update Engine & Pipeline Integration
The macro dataset is automatically maintained by `MarketFetcher.update_macro()` in `market_fetcher.py`.
It queries the FRED JSON API (or anonymous CSV fallback) with a 30-day joblib caching layer to respect rate limits while maintaining freshness.
