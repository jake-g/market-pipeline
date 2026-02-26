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
| Value | str | -0.027011871 |

### `earnings.tsv` - Earnings Dates & Estimates
| Column | Type | Example |
|---|---|---|
| Earnings Date | str | 2026-04-30 17:00:00-04:00 |
| EPS Estimate | float64 | 1.65 |
| Reported EPS | float64 | 1.95 |
| Surprise(%) | float64 | -0.49 |

### `financials_quarterly.tsv` - Quarterly Financials
| Column | Type | Example |
|---|---|---|
| Unnamed: 0 | str | 2025-12-31 |
| Tax Effect Of Unusual Items | float64 | 227547603.833866 |
| Tax Rate For Calcs | float64 | 0.185905 |
| Normalized EBITDA | float64 | 45531000000.0 |
| Total Unusual Items | float64 | 1224000000.0 |
| Total Unusual Items Excluding Goodwill | float64 | 1224000000.0 |
| Net Income From Continuing Operation Net Minority Interest | float64 | 21192000000.0 |
| Reconciled Depreciation | float64 | 19471000000.0 |
| Reconciled Cost Of Revenue | float64 | 109959000000.0 |
| EBITDA | float64 | 46755000000.0 |
| ... (146 more) | | |

### `news.tsv` - News Data (RSS + AlphaVantage Sentiment)
| Column | Type | Example |
|---|---|---|
| Date | str | 2026-02-26 |
| Source | str | Google |
| Sentiment | float64 | 0.375 |
| Headline | str | MIG Capital’s Richard Merage Cuts Amazon.com St... |
| Summary | str | Amazon.com (NasdaqGS:AMZN) has surpassed Walmar... |
| URL | str | https://news.google.com/rss/articles/CBMitgFBVV... |

### `insider_trading.tsv` - Insider Trading Data
| Column | Type | Example |
|---|---|---|
| Date | str | 2004-02-02 |
| Shares | float64 | 311250.0 |
| Amount | float64 | 15336673.625 |
| BuyFlag | int64 | 0 |

## 2. Topic Files (Example: `GLP-1 Weight Loss`)
### `news.tsv` - Topic News
| Column | Type | Example |
|---|---|---|
| Date | str | 2025-06-16 |
| Source | str | Google |
| Sentiment | float64 | 0.15 |
| Headline | str | Are GLP-1 drugs worth their current cost? - UCh... |
| Summary | float64 | nan |
| URL | str | https://news.google.com/rss/articles/CBMitAFBVV... |

## 2. Macro Files
### `market_data/macro/economic_indicators.tsv` - Economic Indicators
| Indicator (Column) | Type | Example |
|---|---|---|
| FREIGHT_PPI | float64 | 417.553 |
| AIR_PPI | float64 | 178.066 |
| TRUCK_PPI | float64 | 188.168 |
| WAREHOUSE_PPI | float64 | 168.631 |
| MFG_CONST | float64 | 214137.0 |
| TECH_PULSE | float64 | 89.7508 |
| CHINA_IMPORTS | float64 | 21104.2786 |
| TARIFFS | float64 | 364.324 |
| GDP | float64 | 31490.07 |
| UNRATE | float64 | 4.3 |
| HOUSING_STARTS | float64 | 1404.0 |
| RECESSION_PROB | float64 | 0.8 |
| CPI | float64 | 326.588 |
| FEDFUNDS | float64 | 3.64 |
| US02Y | float64 | 3.48 |
| US10Y | float64 | 4.08 |