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
| Date | str | 2026-09-29 |
| Source | str | Google |
| Sentiment | float64 | 0.0 |
| Headline | str | FXI Oct 2026 34.500 call (FXI261030C00034500) I... |
| Summary | str | India and China ETFs are trailing AI-driven U.S... |
| URL | str | https://news.google.com/rss/articles/CBMibEFVX3... |

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
| FREIGHT_PPI | float64 | 518.617 |
| AIR_PPI | float64 | 187.374 |
| TRUCK_PPI | float64 | 207.644 |
| WAREHOUSE_PPI | float64 | 168.967 |
| MFG_CONST | float64 | 169795.0 |
| TECH_PULSE | float64 | 96.0488 |
| CHINA_IMPORTS | float64 | 27070.6514 |
| TARIFFS | float64 | 326.324 |
| USD_INDEX | float64 | 120.33 |
| USD_CNY | float64 | 6.711 |
| USD_EUR | float64 | 1.14 |
| USD_JPY | float64 | 157.18 |
| FOOD_CPI | float64 | 350.418 |
| CORN_PRICE | float64 | 213.1902 |
| WHEAT_PRICE | float64 | 228.7388 |
| SUGAR_PRICE | float64 | 14.8123 |
| WTI_CRUDE | float64 | 96.41 |
| NAT_GAS_PRICE | float64 | 2.9632 |
| COPPER_PRICE | float64 | 13542.8209 |
| ELECTRIC_POWER_INDEX | float64 | 118.7493 |
| RD_INVESTMENT | float64 | 936.0 |
| US_BIRTH_RATE | float64 | 10.6 |
| LIFE_EXPECTANCY | float64 | 78.8902 |
| US_POPULATION | float64 | 343289.575 |
| DISPOSABLE_INCOME | float64 | 18122.5 |
| HOUSEHOLD_NET_WORTH | float64 | 195870496.0 |
| CREDIT_CARD_DELINQUENCY | float64 | 2.62 |
| GDP | float64 | 32486.066 |
| REAL_GDP | float64 | 24269.613 |
| UNRATE | float64 | 4.1 |
| HOUSING_STARTS | float64 | 1275.0 |
| RECESSION_PROB | float64 | 0.76 |
| UMICH_SENTIMENT | float64 | 51.7 |
| SAVINGS_RATE | float64 | 3.0 |
| M2_MONEY | float64 | 23342.8 |
| M2_VELOCITY | float64 | 1.415 |
| FED_ASSETS | float64 | 6747704.0 |
| CPI | float64 | 334.131 |
| FEDFUNDS | float64 | 3.63 |
| US02Y | float64 | 4.92 |
| US10Y | float64 | 5.24 |
| US30Y | float64 | 5.56 |
| HY_SPREAD | float64 | 3.02 |
| CORP_SPREAD | float64 | 0.83 |
| BAA_SPREAD | float64 | 1.46 |
| AAA_SPREAD | float64 | 1.02 |
| US_POLICY_UNCERTAINTY | float64 | 193.14 |
| EUROPE_POLICY_UNCERTAINTY | float64 | 325.6696 |
| GLOBAL_POLICY_UNCERTAINTY | float64 | 241.6905 |
| ST_LOUIS_FIN_STRESS | float64 | -0.9075 |
| KANSAS_CITY_FIN_STRESS | float64 | -0.9455 |
| CHICAGO_FED_ACTIVITY | float64 | -0.04 |