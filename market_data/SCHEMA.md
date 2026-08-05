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
| Value | str | 0.2775854 |

### `earnings.tsv` - Earnings Dates & Estimates
| Column | Type | Example |
|---|---|---|
| Earnings Date | str | 2026-10-29 16:00:00-04:00 |
| EPS Estimate | float64 | 1.95 |
| Reported EPS | float64 | 5.75 |
| Surprise(%) | float64 | 215.02 |

### `financials_quarterly.tsv` - Quarterly Financials
| Column | Type | Example |
|---|---|---|
| Unnamed: 0 | str | 2026-06-30 |
| Tax Effect Of Unusual Items | float64 | 3763137018.627303 |
| Tax Rate For Calcs | float64 | 0.239996 |
| Normalized EBITDA | float64 | 43899000000.0 |
| Total Unusual Items | float64 | 15680000000.0 |
| Total Unusual Items Excluding Goodwill | float64 | 15680000000.0 |
| Net Income From Continuing Operation Net Minority Interest | float64 | 30255000000.0 |
| Reconciled Depreciation | float64 | 18945000000.0 |
| Reconciled Cost Of Revenue | float64 | 87463000000.0 |
| EBITDA | float64 | 59579000000.0 |
| ... (233 more) | | |

### `news.tsv` - News Data (RSS + AlphaVantage Sentiment)
| Column | Type | Example |
|---|---|---|
| Date | str | 2026-08-05 |
| Source | str | Google |
| Sentiment | float64 | 0.75 |
| Headline | str | Andy Jassy Just Delivered Incredible News for A... |
| Summary | str | (Bloomberg) -- Jeff Bezos unloaded almost $350 ... |
| URL | str | https://news.google.com/rss/articles/CBMilwFBVV... |

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
| FREIGHT_PPI | float64 | 459.375 |
| AIR_PPI | float64 | 202.358 |
| TRUCK_PPI | float64 | 204.622 |
| WAREHOUSE_PPI | float64 | 166.206 |
| MFG_CONST | float64 | 172674.0 |
| TECH_PULSE | float64 | 95.7495 |
| CHINA_IMPORTS | float64 | 25149.9615 |
| TARIFFS | float64 | 326.324 |
| USD_INDEX | float64 | 119.7034 |
| USD_CNY | float64 | 6.7509 |
| USD_EUR | float64 | 1.1519 |
| USD_JPY | float64 | 159.16 |
| FOOD_CPI | float64 | 349.731 |
| CORN_PRICE | float64 | 195.7819 |
| WHEAT_PRICE | float64 | 199.6483 |
| SUGAR_PRICE | float64 | 13.9077 |
| WTI_CRUDE | float64 | 84.25 |
| NAT_GAS_PRICE | float64 | 3.2059 |
| COPPER_PRICE | float64 | 13552.0409 |
| ELECTRIC_POWER_INDEX | float64 | 115.4043 |
| RD_INVESTMENT | float64 | 937.772 |
| US_BIRTH_RATE | float64 | 10.6 |
| LIFE_EXPECTANCY | float64 | 78.8902 |
| US_POPULATION | float64 | 343289.575 |
| DISPOSABLE_INCOME | float64 | 18056.1 |
| HOUSEHOLD_NET_WORTH | float64 | 182979889.0 |
| CREDIT_CARD_DELINQUENCY | float64 | 2.64 |
| GDP | float64 | 32475.21 |
| REAL_GDP | float64 | 24270.599 |
| UNRATE | float64 | 4.2 |
| HOUSING_STARTS | float64 | 1427.0 |
| RECESSION_PROB | float64 | 0.6 |
| UMICH_SENTIMENT | float64 | 49.5 |
| SAVINGS_RATE | float64 | 2.7 |
| M2_MONEY | float64 | 23155.2 |
| M2_VELOCITY | float64 | 1.412 |
| FED_ASSETS | float64 | 6738190.0 |
| CPI | float64 | 332.568 |
| FEDFUNDS | float64 | 3.63 |
| US02Y | float64 | 4.25 |
| US10Y | float64 | 4.7 |
| US30Y | float64 | 5.23 |
| HY_SPREAD | float64 | 2.78 |
| CORP_SPREAD | float64 | 0.78 |
| BAA_SPREAD | float64 | 1.61 |
| AAA_SPREAD | float64 | 1.18 |
| US_POLICY_UNCERTAINTY | float64 | 213.26 |
| EUROPE_POLICY_UNCERTAINTY | float64 | 353.0482 |
| GLOBAL_POLICY_UNCERTAINTY | float64 | 278.2301 |
| ST_LOUIS_FIN_STRESS | float64 | -0.8263 |
| KANSAS_CITY_FIN_STRESS | float64 | -0.7631 |
| CHICAGO_FED_ACTIVITY | float64 | -0.02 |