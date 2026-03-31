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
| Value | str | 0.04568875 |

### `earnings.tsv` - Earnings Dates & Estimates
| Column | Type | Example |
|---|---|---|
| Earnings Date | str | 2026-04-30 16:00:00-04:00 |
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
| ... (144 more) | | |

### `news.tsv` - News Data (RSS + AlphaVantage Sentiment)
| Column | Type | Example |
|---|---|---|
| Date | str | 2026-03-31 |
| Source | str | Google |
| Sentiment | float64 | 1.0 |
| Headline | str | Gear up for your best spring yet with these exp... |
| Summary | str | Yahoo Finance Host Josh Lipton tracks today's t... |
| URL | str | https://news.google.com/rss/articles/CBMif0FVX3... |

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
| FREIGHT_PPI | float64 | 421.137 |
| AIR_PPI | float64 | 175.008 |
| TRUCK_PPI | float64 | 185.632 |
| WAREHOUSE_PPI | float64 | 173.049 |
| MFG_CONST | float64 | 196166.0 |
| TECH_PULSE | float64 | 92.2679 |
| CHINA_IMPORTS | float64 | 21057.9084 |
| TARIFFS | float64 | 364.324 |
| GDP | float64 | 31442.483 |
| UNRATE | float64 | 4.4 |
| HOUSING_STARTS | float64 | 1487.0 |
| RECESSION_PROB | float64 | 0.8 |
| CPI | float64 | 327.46 |
| FEDFUNDS | float64 | 3.64 |
| US02Y | float64 | 3.96 |
| US10Y | float64 | 4.42 |