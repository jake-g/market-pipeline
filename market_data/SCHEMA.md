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
| Date | str | 2026-11-20 |
| Source | str | Google |
| Sentiment | float64 | 0.0 |
| Headline | str | Growing Wealth With Gold And China - Seeking Alpha |
| Summary | str | When even a policymaker known for patience star... |
| URL | str | https://news.google.com/rss/articles/CBMigAFBVV... |

## 2. Topic Files (Example: `Data Center Power`)
### `news.tsv` - Topic News
| Column | Type | Example |
|---|---|---|
| Date | str | 2024-01-17 |
| Source | str | JLL |
| Sentiment | float64 | 0.2 |
| Headline | str | Getting data centers ready for the AI boom |
| Summary | float64 | nan |
| URL | str | https://news.google.com/rss/articles/CBMigwFBVV... |

## 2. Macro Files
### `market_data/macro/economic_indicators.tsv` - Economic Indicators
| Indicator (Column) | Type | Example |
|---|---|---|
| FREIGHT_PPI | float64 | 572.968 |
| AIR_PPI | float64 | 182.539 |
| TRUCK_PPI | float64 | 230.994 |
| WAREHOUSE_PPI | float64 | 168.507 |
| MFG_CONST | float64 | 170217.0 |
| TECH_PULSE | float64 | 95.6264 |
| CHINA_IMPORTS | float64 | 31484.5938 |
| TARIFFS | float64 | 275.296 |
| USD_INDEX | float64 | 122.6503 |
| USD_CNY | float64 | 6.671 |
| USD_EUR | float64 | 1.1034 |
| USD_JPY | float64 | 159.93 |
| FOOD_CPI | float64 | 352.359 |
| CORN_PRICE | float64 | 236.9161 |
| WHEAT_PRICE | float64 | 246.8518 |
| SUGAR_PRICE | float64 | 17.9371 |
| WTI_CRUDE | float64 | 89.53 |
| NAT_GAS_PRICE | float64 | 2.9538 |
| COPPER_PRICE | float64 | 14473.0559 |
| ELECTRIC_POWER_INDEX | float64 | 117.7056 |
| RD_INVESTMENT | float64 | 977.7 |
| US_BIRTH_RATE | float64 | 10.6 |
| LIFE_EXPECTANCY | float64 | 78.8902 |
| US_POPULATION | float64 | 343230.822 |
| DISPOSABLE_INCOME | float64 | 18366.1 |
| HOUSEHOLD_NET_WORTH | float64 | 195870496.0 |
| CREDIT_CARD_DELINQUENCY | float64 | 2.62 |
| GDP | float64 | 33010.036 |
| REAL_GDP | float64 | 24611.077 |
| UNRATE | float64 | 4.1 |
| HOUSING_STARTS | float64 | 1309.0 |
| RECESSION_PROB | float64 | 0.4 |
| UMICH_SENTIMENT | float64 | 48.0 |
| SAVINGS_RATE | float64 | 3.8 |
| M2_MONEY | float64 | 23413.9 |
| M2_VELOCITY | float64 | 1.417 |
| FED_ASSETS | float64 | 6741452.0 |
| CPI | float64 | 337.476 |
| FEDFUNDS | float64 | 3.88 |
| US02Y | float64 | 4.8 |
| US10Y | float64 | 5.07 |
| US30Y | float64 | 5.41 |
| HY_SPREAD | float64 | 3.52 |
| CORP_SPREAD | float64 | 0.94 |
| BAA_SPREAD | float64 | 1.52 |
| AAA_SPREAD | float64 | 1.06 |
| FEDFUNDS_UPPER | float64 | 4.0 |
| SOFR | float64 | 3.91 |
| US03M | float64 | 4.34 |
| US01Y | float64 | 4.62 |
| US05Y | float64 | 4.89 |
| US10Y_REAL | float64 | 2.88 |
| BREAKEVEN_10Y | float64 | 2.16 |
| TERM_PREMIUM_10Y | float64 | 0.9864 |
| HY_YIELD | float64 | 8.35 |
| CORP_YIELD | float64 | 5.91 |
| US_POLICY_UNCERTAINTY | float64 | 162.28 |
| EUROPE_POLICY_UNCERTAINTY | float64 | 373.5523 |
| GLOBAL_POLICY_UNCERTAINTY | float64 | 241.6905 |
| ST_LOUIS_FIN_STRESS | float64 | -0.8655 |
| KANSAS_CITY_FIN_STRESS | float64 | -0.885 |
| CHICAGO_FED_ACTIVITY | float64 | 0.07 |