# Data Schema Report

This report documents the file structures and column data types used in `market_data/`.

## 1. Ticker Files (Example: `FXI`)
### `prices.tsv` - Daily OHLCV Prices
| Column | Type | Example |
|---|---|---|
| Date | str | 2018-01-02 |
| Open | float64 | 47.58 |
| High | float64 | 47.78 |
| Low | float64 | 47.43 |
| Close | float64 | 39.22 |
| Volume | int64 | 14290900 |

### `fundamentals.tsv` - Key Statistics (Key-Value)
| Column | Type | Example |
|---|---|---|
| Metric | str | allTimeHigh |
| Value | str | 73.18667 |

### `news.tsv` - News Data (RSS + AlphaVantage Sentiment)
| Column | Type | Example |
|---|---|---|
| Date | str | 2026-09-04 |
| Source | str | Google |
| Sentiment | float64 | 0.068 |
| Headline | str | China’s Export Machine Has a New Problem as 19 ... |
| Summary | str | Korea's country ETF booked triple-digit gains w... |
| URL | str | https://news.google.com/rss/articles/CBMi8gFBVV... |

## 2. Topic Files (Example: `Memory Shortage`)
### `news.tsv` - Topic News
| Column | Type | Example |
|---|---|---|
| Date | str | 2025-12-02 |
| Source | str | Google |
| Sentiment | float64 | 0.0 |
| Headline | str | The AI frenzy is driving a memory chip supply c... |
| Summary | float64 | nan |
| URL | str | https://news.google.com/rss/articles/CBMioAFBVV... |

## 2. Macro Files
### `market_data/macro/economic_indicators.tsv` - Economic Indicators
| Indicator (Column) | Type | Example |
|---|---|---|
| FREIGHT_PPI | float64 | 526.89 |
| AIR_PPI | float64 | 178.234 |
| TRUCK_PPI | float64 | 195.575 |
| WAREHOUSE_PPI | float64 | 167.902 |
| MFG_CONST | float64 | 169795.0 |
| TECH_PULSE | float64 | 96.3106 |
| CHINA_IMPORTS | float64 | 27070.6514 |
| TARIFFS | float64 | 326.324 |
| USD_INDEX | float64 | 118.7479 |
| USD_CNY | float64 | 6.726 |
| USD_EUR | float64 | 1.1598 |
| USD_JPY | float64 | 159.97 |
| FOOD_CPI | float64 | 350.164 |
| CORN_PRICE | float64 | 213.1902 |
| WHEAT_PRICE | float64 | 228.7388 |
| SUGAR_PRICE | float64 | 14.8123 |
| WTI_CRUDE | float64 | 91.48 |
| NAT_GAS_PRICE | float64 | 2.9632 |
| COPPER_PRICE | float64 | 13542.8209 |
| ELECTRIC_POWER_INDEX | float64 | 116.4486 |
| RD_INVESTMENT | float64 | 936.0 |
| US_BIRTH_RATE | float64 | 10.6 |
| LIFE_EXPECTANCY | float64 | 78.8902 |
| US_POPULATION | float64 | 343289.575 |
| DISPOSABLE_INCOME | float64 | 18122.5 |
| HOUSEHOLD_NET_WORTH | float64 | 182979889.0 |
| CREDIT_CARD_DELINQUENCY | float64 | 2.62 |
| GDP | float64 | 32486.066 |
| REAL_GDP | float64 | 24269.613 |
| UNRATE | float64 | 4.1 |
| HOUSING_STARTS | float64 | 1239.0 |
| RECESSION_PROB | float64 | 0.76 |
| UMICH_SENTIMENT | float64 | 55.2 |
| SAVINGS_RATE | float64 | 3.0 |
| M2_MONEY | float64 | 23218.0 |
| M2_VELOCITY | float64 | 1.415 |
| FED_ASSETS | float64 | 6737204.0 |
| CPI | float64 | 332.813 |
| FEDFUNDS | float64 | 3.63 |
| US02Y | float64 | 4.39 |
| US10Y | float64 | 4.79 |
| US30Y | float64 | 5.27 |
| HY_SPREAD | float64 | 2.66 |
| CORP_SPREAD | float64 | 0.81 |
| BAA_SPREAD | float64 | 1.58 |
| AAA_SPREAD | float64 | 1.15 |
| US_POLICY_UNCERTAINTY | float64 | 276.46 |
| EUROPE_POLICY_UNCERTAINTY | float64 | 325.6696 |
| GLOBAL_POLICY_UNCERTAINTY | float64 | 241.6905 |
| ST_LOUIS_FIN_STRESS | float64 | -0.8526 |
| KANSAS_CITY_FIN_STRESS | float64 | -0.8483 |
| CHICAGO_FED_ACTIVITY | float64 | -0.08 |