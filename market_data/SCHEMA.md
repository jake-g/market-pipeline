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
| Date | str | 2026-10-14 |
| Source | str | Google |
| Sentiment | float64 | 0.0 |
| Headline | str | China resumes U.S. soybean buying with 8-10 car... |
| Summary | str | Markets have been rising globally, with the exc... |
| URL | str | https://news.google.com/rss/articles/CBMiugFBVV... |

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
| FREIGHT_PPI | float64 | 518.617 |
| AIR_PPI | float64 | 187.374 |
| TRUCK_PPI | float64 | 207.644 |
| WAREHOUSE_PPI | float64 | 168.967 |
| MFG_CONST | float64 | 170701.0 |
| TECH_PULSE | float64 | 96.0488 |
| CHINA_IMPORTS | float64 | 27133.8159 |
| TARIFFS | float64 | 306.398 |
| USD_INDEX | float64 | 121.3848 |
| USD_CNY | float64 | 6.7038 |
| USD_EUR | float64 | 1.1259 |
| USD_JPY | float64 | 157.81 |
| FOOD_CPI | float64 | 350.418 |
| CORN_PRICE | float64 | 213.1902 |
| WHEAT_PRICE | float64 | 228.7388 |
| SUGAR_PRICE | float64 | 14.8123 |
| WTI_CRUDE | float64 | 96.24 |
| NAT_GAS_PRICE | float64 | 2.9632 |
| COPPER_PRICE | float64 | 13542.8209 |
| ELECTRIC_POWER_INDEX | float64 | 118.7493 |
| RD_INVESTMENT | float64 | 950.518 |
| US_BIRTH_RATE | float64 | 10.6 |
| LIFE_EXPECTANCY | float64 | 78.8902 |
| US_POPULATION | float64 | 343149.507 |
| DISPOSABLE_INCOME | float64 | 18410.5 |
| HOUSEHOLD_NET_WORTH | float64 | 195870496.0 |
| CREDIT_CARD_DELINQUENCY | float64 | 2.62 |
| GDP | float64 | 32563.03 |
| REAL_GDP | float64 | 24408.011 |
| UNRATE | float64 | 4.2 |
| HOUSING_STARTS | float64 | 1275.0 |
| RECESSION_PROB | float64 | 0.62 |
| UMICH_SENTIMENT | float64 | 51.7 |
| SAVINGS_RATE | float64 | 4.1 |
| M2_MONEY | float64 | 23342.8 |
| M2_VELOCITY | float64 | 1.418 |
| FED_ASSETS | float64 | 6747560.0 |
| CPI | float64 | 334.131 |
| FEDFUNDS | float64 | 3.75 |
| US02Y | float64 | 4.75 |
| US10Y | float64 | 5.22 |
| US30Y | float64 | 5.6 |
| HY_SPREAD | float64 | 3.15 |
| CORP_SPREAD | float64 | 0.82 |
| BAA_SPREAD | float64 | 1.48 |
| AAA_SPREAD | float64 | 1.03 |
| FEDFUNDS_UPPER | float64 | 4.0 |
| SOFR | float64 | 3.87 |
| US03M | float64 | 4.25 |
| US01Y | float64 | 4.47 |
| US05Y | float64 | 5.02 |
| US10Y_REAL | float64 | 2.91 |
| BREAKEVEN_10Y | float64 | 2.33 |
| TERM_PREMIUM_10Y | float64 | 1.0729 |
| HY_YIELD | float64 | 8.09 |
| CORP_YIELD | float64 | 5.96 |
| US_POLICY_UNCERTAINTY | float64 | 242.69 |
| EUROPE_POLICY_UNCERTAINTY | float64 | 358.5228 |
| GLOBAL_POLICY_UNCERTAINTY | float64 | 241.6905 |
| ST_LOUIS_FIN_STRESS | float64 | -0.4681 |
| KANSAS_CITY_FIN_STRESS | float64 | -0.9858 |
| CHICAGO_FED_ACTIVITY | float64 | -0.04 |