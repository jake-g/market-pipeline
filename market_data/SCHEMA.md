# Data Schema Report

This report documents the file structures and column data types used in `market_data/`.

## 1. Ticker Files (Example: `AMZN`)
### `prices.tsv` - Daily OHLCV Prices
| Column | Type | Example |
|---|---|---|
| Date | str | 2018-01-02 |
| Open | float64 | 58.6 |
| High | float64 | 59.5 |
| Low | float64 | 58.53 |
| Close | float64 | 59.45 |
| Volume | int64 | 53890000 |

### `fundamentals.tsv` - Key Statistics (Key-Value)
| Column | Type | Example |
|---|---|---|
| Metric | str | 52WeekChange |
| Value | str | 0.11305618 |

### `earnings.tsv` - Earnings Dates & Estimates
| Column | Type | Example |
|---|---|---|
| Earnings Date | str | 2026-07-30 16:00:00-04:00 |
| EPS Estimate | float64 | 1.81 |
| Reported EPS | float64 | 2.78 |
| Surprise(%) | float64 | 68.18 |

### `financials_quarterly.tsv` - Quarterly Financials
| Column | Type | Example |
|---|---|---|
| Unnamed: 0 | str | 2026-03-31 |
| Tax Effect Of Unusual Items | float64 | 3763137018.627303 |
| Tax Rate For Calcs | float64 | 0.239996 |
| Normalized EBITDA | float64 | 43899000000.0 |
| Total Unusual Items | float64 | 15680000000.0 |
| Total Unusual Items Excluding Goodwill | float64 | 15680000000.0 |
| Net Income From Continuing Operation Net Minority Interest | float64 | 30255000000.0 |
| Reconciled Depreciation | float64 | 18945000000.0 |
| Reconciled Cost Of Revenue | float64 | 87463000000.0 |
| EBITDA | float64 | 59579000000.0 |
| ... (145 more) | | |

### `news.tsv` - News Data (RSS + AlphaVantage Sentiment)
| Column | Type | Example |
|---|---|---|
| Date | str | 2026-07-08 |
| Source | str | Google |
| Sentiment | float64 | 0.6 |
| Headline | str | Amazon.com vs. Shopify: Comparing Revenue Trend... |
| Summary | str | Corning Incorporated (NYSE:GLW) is one of the B... |
| URL | str | https://news.google.com/rss/articles/CBMizgFBVV... |

### `insider_trading.tsv` - Insider Trading Data
| Column | Type | Example |
|---|---|---|
| Date | str | 2004-02-02 |
| Shares | float64 | 311250.0 |
| Amount | float64 | 15336673.625 |
| BuyFlag | int64 | 0 |

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
| FREIGHT_PPI | float64 | 466.381 |
| AIR_PPI | float64 | 198.479 |
| TRUCK_PPI | float64 | 216.119 |
| WAREHOUSE_PPI | float64 | 169.441 |
| MFG_CONST | float64 | 174764.0 |
| TECH_PULSE | float64 | 94.0431 |
| CHINA_IMPORTS | float64 | 23507.8161 |
| TARIFFS | float64 | 346.15 |
| USD_INDEX | float64 | 120.6902 |
| USD_CNY | float64 | 6.7886 |
| USD_EUR | float64 | 1.1448 |
| USD_JPY | float64 | 160.9 |
| FOOD_CPI | float64 | 349.032 |
| CORN_PRICE | float64 | 215.6206 |
| WHEAT_PRICE | float64 | 220.8846 |
| SUGAR_PRICE | float64 | 14.8692 |
| WTI_CRUDE | float64 | 69.6 |
| NAT_GAS_PRICE | float64 | 2.8977 |
| COPPER_PRICE | float64 | 13483.7515 |
| ELECTRIC_POWER_INDEX | float64 | 114.0543 |
| RD_INVESTMENT | float64 | 909.507 |
| US_BIRTH_RATE | float64 | 10.6 |
| LIFE_EXPECTANCY | float64 | 78.8902 |
| US_POPULATION | float64 | 343289.575 |
| DISPOSABLE_INCOME | float64 | 17983.8 |
| HOUSEHOLD_NET_WORTH | float64 | 182979889.0 |
| CREDIT_CARD_DELINQUENCY | float64 | 2.64 |
| GDP | float64 | 31865.721 |
| REAL_GDP | float64 | 24180.419 |
| UNRATE | float64 | 4.2 |
| HOUSING_STARTS | float64 | 1177.0 |
| RECESSION_PROB | float64 | 0.54 |
| UMICH_SENTIMENT | float64 | 44.8 |
| SAVINGS_RATE | float64 | 3.0 |
| M2_MONEY | float64 | 23052.3 |
| M2_VELOCITY | float64 | 1.411 |
| FED_ASSETS | float64 | 6724564.0 |
| CPI | float64 | 333.979 |
| FEDFUNDS | float64 | 3.63 |
| US02Y | float64 | 4.19 |
| US10Y | float64 | 4.55 |
| US30Y | float64 | 5.05 |
| HY_SPREAD | float64 | 2.67 |
| CORP_SPREAD | float64 | 0.76 |
| BAA_SPREAD | float64 | 1.55 |
| AAA_SPREAD | float64 | 1.12 |
| US_POLICY_UNCERTAINTY | float64 | 181.76 |
| EUROPE_POLICY_UNCERTAINTY | float64 | 353.0482 |
| GLOBAL_POLICY_UNCERTAINTY | float64 | 278.2301 |
| ST_LOUIS_FIN_STRESS | float64 | -0.7246 |
| KANSAS_CITY_FIN_STRESS | float64 | -0.7631 |
| CHICAGO_FED_ACTIVITY | float64 | -0.1 |