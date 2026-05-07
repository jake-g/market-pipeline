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
| Value | str | 0.470461 |

### `earnings.tsv` - Earnings Dates & Estimates
| Column | Type | Example |
|---|---|---|
| Earnings Date | str | 2026-07-30 16:00:00-04:00 |
| EPS Estimate | float64 | 1.82 |
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
| Date | str | 2026-05-06 |
| Source | str | Yahoo |
| Sentiment | float64 | 0.8 |
| Headline | str | The Smartest Stocks to Buy With $1,000 in May |
| Summary | str | Amazon and Apple are two great stocks to buy th... |
| URL | str | https://www.fool.com/investing/2026/05/06/the-s... |

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
| FREIGHT_PPI | float64 | 409.156 |
| AIR_PPI | float64 | 176.501 |
| TRUCK_PPI | float64 | 185.239 |
| WAREHOUSE_PPI | float64 | 173.049 |
| MFG_CONST | float64 | 196166.0 |
| TECH_PULSE | float64 | 89.8561 |
| CHINA_IMPORTS | float64 | 20859.034 |
| TARIFFS | float64 | 346.15 |
| GDP | float64 | 31856.257 |
| UNRATE | float64 | 4.3 |
| HOUSING_STARTS | float64 | 1502.0 |
| RECESSION_PROB | float64 | 1.82 |
| CPI | float64 | 330.293 |
| FEDFUNDS | float64 | 3.64 |
| US02Y | float64 | 3.93 |
| US10Y | float64 | 4.43 |