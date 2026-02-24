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
| Value | str | -0.012640953 |

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
| Date | str | 2026-02-24 |
| Source | str | Yahoo |
| Sentiment | float64 | 0.283 |
| Headline | str | 3 Brilliant Growth Stocks to Buy Now and Hold f... |
| Summary | str | Look beyond the current numbers for enduring gr... |
| URL | str | https://www.fool.com/investing/2026/02/23/3-bri... |

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
| Date | str | 2026-02-24 |
| Source | str | Google |
| Sentiment | float64 | 0.6 |
| Headline | str | Got $5,000? Viking Therapeutics Might Be a Weig... |
| Summary | float64 | nan |
| URL | str | https://news.google.com/rss/articles/CBMimAFBVV... |

## 2. Macro Files
### `market_data/macro/economic_indicators.tsv` - Economic Indicators
| Indicator (Column) | Type | Example |
|---|---|---|
| FREIGHT_PPI | float64 | 100.0 |
| AIR_PPI | float64 | 100.0 |
| TRUCK_PPI | float64 | 100.0 |
| WAREHOUSE_PPI | float64 | 100.0 |
| MFG_CONST | float64 | 28318.0 |
| TECH_PULSE | float64 | 18.3732 |
| CHINA_IMPORTS | float64 | 293.1 |
| TARIFFS | float64 | 0.952 |
| GDP | float64 | 243.164 |
| UNRATE | float64 | 3.4 |
| HOUSING_STARTS | float64 | 1657.0 |
| RECESSION_PROB | float64 | 0.86 |
| CPI | float64 | 21.48 |
| FEDFUNDS | float64 | 0.8 |
| US02Y | float64 | 7.26 |
| US10Y | float64 | 4.06 |