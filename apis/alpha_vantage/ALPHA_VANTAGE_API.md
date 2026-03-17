# Alpha Vantage API Documentation & Support

## Customer Support & FAQ

### Claim your Free API Key
Claim your free key for the Alpha Vantage Stock API © with lifetime access. We highly recommend that you use a legitimate email address - this is the primary way we will contact you for feature announcements or troubleshooting. By acquiring and using an API key, you agree to our Terms of Service and Privacy Policy.

### Frequently Asked Questions
*   **Are there usage limits?** We provide free API service for up to **25 requests per day**. For higher volumes, please visit premium membership.
*   **Why is US stock market data premium-only?** Realtime and 15-minute delayed US market data is regulated by exchanges, FINRA, and the SEC. As a licensed provider, we offer this premium data fully exchange-approved.
*   **What adjustment method do you use?** We adjust open, high, low, close, and volume data by both splits and cash dividend events. Most endpoints also offer an option for raw, unadjusted data.
*   **Need support?** Reach out to `support@alphavantage.co`.

---

## Time Series Stock Data APIs

### TIME_SERIES_INTRADAY `Trending` `Premium`
Returns current and 20+ years of historical intraday OHLCV time series of the equity specified, covering pre-market and post-market hours.
*   **Required `function`**: `TIME_SERIES_INTRADAY`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Required `interval`**: Time interval between data points. Supported: `1min`, `5min`, `15min`, `30min`, `60min`.
*   **Optional `adjusted`**: `true` (default) adjusts by historical splits/dividends. `false` queries raw values.
*   **Optional `extended_hours`**: `true` (default) includes pre/post-market. `false` restricts to regular trading hours.
*   **Optional `month`**: Queries a specific month in history (format: `YYYY-MM`, e.g., `2009-01`).
*   **Optional `outputsize`**: `compact` (default, latest 100 points) or `full` (trailing 30 days, or full month if `month` is set).
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Optional `entitlement`**: Controls freshness. Unset (historical), `realtime`, or `delayed` (15-minute delayed).
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo'
print(requests.get(url).json())
```

### TIME_SERIES_DAILY
Returns raw (as-traded) daily time series (date, open, high, low, close, volume) covering 20+ years of history.
*   **Required `function`**: `TIME_SERIES_DAILY`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Optional `outputsize`**: `compact` (default, latest 100 points) or `full` (full 20+ years). *Note: `full` requires premium.*
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### TIME_SERIES_DAILY_ADJUSTED `Trending` `Premium`
Returns raw daily OHLCV values, adjusted close values, and historical split/dividend events.
*   **Required `function`**: `TIME_SERIES_DAILY_ADJUSTED`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Optional `outputsize`**: `compact` (default, latest 100 points) or `full` (full 20+ years).
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Optional `entitlement`**: Unset (historical), `realtime`, or `delayed`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### TIME_SERIES_WEEKLY
Returns weekly time series (last trading day of each week, open, high, low, close, volume).
*   **Required `function`**: `TIME_SERIES_WEEKLY`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### TIME_SERIES_WEEKLY_ADJUSTED
Returns weekly adjusted time series (including adjusted close and weekly dividend).
*   **Required `function`**: `TIME_SERIES_WEEKLY_ADJUSTED`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY_ADJUSTED&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### TIME_SERIES_MONTHLY
Returns monthly time series (last trading day of each month, open, high, low, close, volume).
*   **Required `function`**: `TIME_SERIES_MONTHLY`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### TIME_SERIES_MONTHLY_ADJUSTED
Returns monthly adjusted time series (including adjusted close and monthly dividend).
*   **Required `function`**: `TIME_SERIES_MONTHLY_ADJUSTED`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY_ADJUSTED&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Quote Endpoint `Trending`
Returns the latest price and volume information for a single ticker.
*   **Required `function`**: `GLOBAL_QUOTE`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Optional `entitlement`**: Unset (historical), `realtime`, or `delayed`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Realtime Bulk Quotes `Premium`
Returns realtime quotes for US-traded symbols in bulk, accepting up to 100 symbols per request.
*   **Required `function`**: `REALTIME_BULK_QUOTES`
*   **Required `symbol`**: Comma-separated tickers (e.g., `MSFT,AAPL,IBM`). First 100 honored.
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=REALTIME_BULK_QUOTES&symbol=MSFT,AAPL,IBM&apikey=demo'
print(requests.get(url).json())
```

### Search Endpoint `Utility`
Returns best-matching symbols and market info based on keywords. Ideal for auto-complete.
*   **Required `function`**: `SYMBOL_SEARCH`
*   **Required `keywords`**: Text string (e.g., `microsoft` or `BA`).
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords=tesco&apikey=demo'
print(requests.get(url).json())
```

### Global Market Open & Close Status `Utility`
Returns the current market status (open vs. closed) of major global trading venues.
*   **Required `function`**: `MARKET_STATUS`
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=MARKET_STATUS&apikey=demo'
print(requests.get(url).json())
```

---

## Options Data APIs `Premium`

### Realtime Options `Trending` `Premium`
Returns realtime US options data with full market coverage. Sorted by expiration date and strike price.
*   **Required `function`**: `REALTIME_OPTIONS`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Optional `require_greeks`**: `true` enables greeks & IV. Default is `false`.
*   **Optional `contract`**: Specific US option contract ID. Defaults to entire option chain.
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=REALTIME_OPTIONS&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Historical Options `Trending` `Premium`
Returns the full historical options chain for a specific symbol on a specific date, covering 15+ years.
*   **Required `function`**: `HISTORICAL_OPTIONS`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Optional `date`**: Format `YYYY-MM-DD`. Defaults to previous trading session. Supports dates back to `2008-01-01`.
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol=IBM&date=2017-11-15&apikey=demo'
print(requests.get(url).json())
```

---

## Alpha Intelligence™

### Market News & Sentiment `Trending`
Returns live and historical market news & sentiment data enriched with LLM signals.
*   **Required `function`**: `NEWS_SENTIMENT`
*   **Optional `tickers`**: Comma-separated symbols (e.g., `IBM` or `COIN,CRYPTO:BTC,FOREX:USD`).
*   **Optional `topics`**: Comma-separated topics. Supported values:
    *   `blockchain`, `earnings`, `ipo`, `mergers_and_acquisitions`, `financial_markets`
    *   `economy_fiscal`, `economy_monetary`, `economy_macro`
    *   `energy_transportation`, `finance`, `life_sciences`, `manufacturing`, `real_estate`, `retail_wholesale`, `technology`
*   **Optional `time_from` / `time_to`**: Time range formatted as `YYYYMMDDTHHMM` (e.g., `20220410T0130`).
*   **Optional `sort`**: `LATEST` (default), `EARLIEST`, or `RELEVANCE`.
*   **Optional `limit`**: Default `50`, Max `1000`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers=AAPL&apikey=demo'
print(requests.get(url).json())
```

### Earnings Call Transcript `Trending`
Returns the earnings call transcript enriched with LLM-based sentiment signals.
*   **Required `function`**: `EARNINGS_CALL_TRANSCRIPT`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Required `quarter`**: Fiscal quarter formatted as `YYYYQM` (e.g., `2024Q1`). Supports back to 2010Q1.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=EARNINGS_CALL_TRANSCRIPT&symbol=IBM&quarter=2024Q1&apikey=demo'
print(requests.get(url).json())
```

### Top Gainers, Losers, and Most Actively Traded Tickers
Returns the top 20 gainers, losers, and most actively traded tickers in the US market.
*   **Required `function`**: `TOP_GAINERS_LOSERS`
*   **Optional `entitlement`**: Unset (historical end-of-day), `realtime`, or `delayed`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey=demo'
print(requests.get(url).json())
```

### Insider Transactions `Trending`
Returns the latest and historical insider transactions made by key stakeholders.
*   **Required `function`**: `INSIDER_TRANSACTIONS`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=INSIDER_TRANSACTIONS&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Advanced Analytics (Fixed Window)
Returns advanced analytics metrics for a given time series over a fixed temporal window.
*   **Required `function`**: `ANALYTICS_FIXED_WINDOW`
*   **Required `SYMBOLS`**: Comma-separated list (Free tier max 5, Premium max 50).
*   **Required `RANGE`**: Specifies the data range. Can specify two variables for start/end. Formats:
    *   `full`, `{N}day`, `{N}week`, `{N}month`, `{N}year`
    *   Intraday specific: `{N}minute`, `{N}hour`
    *   Dates: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`
*   **Optional `OHLC`**: `open`, `high`, `low`, or `close` (default).
*   **Required `INTERVAL`**: `1min`, `5min`, `15min`, `30min`, `60min`, `DAILY`, `WEEKLY`, `MONTHLY`.
*   **Required `CALCULATIONS`**: Comma-separated list of metrics:
    *   `MIN`, `MAX`, `MEAN`, `MEDIAN`, `CUMULATIVE_RETURN`
    *   `VARIANCE` or `VARIANCE(annualized=True)`
    *   `STDDEV` or `STDDEV(annualized=True)`
    *   `MAX_DRAWDOWN`
    *   `HISTOGRAM` or `HISTOGRAM(bins=20)`
    *   `AUTOCORRELATION` or `AUTOCORRELATION(lag=2)`
    *   `COVARIANCE` or `COVARIANCE(annualized=True)`
    *   `CORRELATION`, `CORRELATION(method=KENDALL)`, or `CORRELATION(method=SPEARMAN)`
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://alphavantageapi.co/timeseries/analytics?SYMBOLS=AAPL,MSFT,IBM&RANGE=2023-07-01&RANGE=2023-08-31&INTERVAL=DAILY&OHLC=close&CALCULATIONS=MEAN,STDDEV,CORRELATION&apikey=demo'
print(requests.get(url).json())
```

### Advanced Analytics (Sliding Window) `Trending`
Returns advanced analytics metrics calculated over a sliding moving window.
*   **Required `function`**: `ANALYTICS_SLIDING_WINDOW`
*   **Required `SYMBOLS`**: Comma-separated list.
*   **Required `RANGE`**: Same range values as Fixed Window API.
*   **Optional `OHLC`**: `open`, `high`, `low`, or `close` (default).
*   **Required `INTERVAL`**: `1min`, `5min`, etc.
*   **Required `WINDOW_SIZE`**: Integer (e.g., `20`). Hard lower bound is 10.
*   **Required `CALCULATIONS`**: Same calculations as Fixed Window, but calculates rolling values. (Free tier limits to 1 calculation per request).
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://alphavantageapi.co/timeseries/running_analytics?SYMBOLS=AAPL,IBM&RANGE=2month&INTERVAL=DAILY&OHLC=close&WINDOW_SIZE=20&CALCULATIONS=MEAN,STDDEV(annualized=True)&apikey=demo'
print(requests.get(url).json())
```

---

## Fundamental Data

### Company Overview `Trending`
Returns company info, financial ratios, and other key metrics.
*   **Required `function`**: `OVERVIEW`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=OVERVIEW&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### ETF Profile & Holdings
Returns key ETF metrics and constituents with sector allocation.
*   **Required `function`**: `ETF_PROFILE`
*   **Required `symbol`**: The ETF name (e.g., `QQQ`).
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=ETF_PROFILE&symbol=QQQ&apikey=demo'
print(requests.get(url).json())
```

### Corporate Action - Dividends
Returns historical and future (declared) dividend distributions.
*   **Required `function`**: `DIVIDENDS`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=DIVIDENDS&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Corporate Action - Splits
Returns historical split events.
*   **Required `function`**: `SPLITS`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=SPLITS&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Income Statement
Returns annual and quarterly SEC-mapped income statements.
*   **Required `function`**: `INCOME_STATEMENT`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Balance Sheet
Returns annual and quarterly SEC-mapped balance sheets.
*   **Required `function`**: `BALANCE_SHEET`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=BALANCE_SHEET&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Cash Flow
Returns annual and quarterly SEC-mapped cash flows.
*   **Required `function`**: `CASH_FLOW`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=CASH_FLOW&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Shares Outstanding
Returns quarterly diluted and basic shares outstanding values.
*   **Required `function`**: `SHARES_OUTSTANDING`
*   **Required `symbol`**: The equity name (e.g., `MSFT`).
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=SHARES_OUTSTANDING&symbol=MSFT&apikey=demo'
print(requests.get(url).json())
```

### Earnings History
Returns annual and quarterly EPS, including analyst estimates and surprises.
*   **Required `function`**: `EARNINGS`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=EARNINGS&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Earnings Estimates `Trending`
Returns annual and quarterly EPS and revenue estimates, analyst count, and revisions.
*   **Required `function`**: `EARNINGS_ESTIMATES`
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=EARNINGS_ESTIMATES&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Listing & Delisting Status (CSV Only)
Returns active or delisted US stocks/ETFs as of latest trading day or a specific date.
*   **Required `function`**: `LISTING_STATUS`
*   **Optional `date`**: Specific point in history (`YYYY-MM-DD`).
*   **Optional `state`**: `active` (default) or `delisted`.
*   **Required `apikey`**: Your API key.
```python
import csv, requests
url = 'https://www.alphavantage.co/query?function=LISTING_STATUS&apikey=demo'
with requests.Session() as s:
    content = s.get(url).content.decode('utf-8')
    for row in list(csv.reader(content.splitlines(), delimiter=','))[:5]:
        print(row)
```

### Earnings Calendar (CSV Only)
Returns scheduled company earnings in the next 3, 6, or 12 months.
*   **Required `function`**: `EARNINGS_CALENDAR`
*   **Optional `symbol`**: Target specific equity (e.g., `IBM`).
*   **Optional `horizon`**: `3month` (default), `6month`, `12month`.
*   **Required `apikey`**: Your API key.
```python
import csv, requests
url = 'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey=demo'
with requests.Session() as s:
    content = s.get(url).content.decode('utf-8')
    for row in list(csv.reader(content.splitlines(), delimiter=','))[:5]:
        print(row)
```

### IPO Calendar (CSV Only)
Returns scheduled IPOs in the next 3 months.
*   **Required `function`**: `IPO_CALENDAR`
*   **Required `apikey`**: Your API key.
```python
import csv, requests
url = 'https://www.alphavantage.co/query?function=IPO_CALENDAR&apikey=demo'
with requests.Session() as s:
    content = s.get(url).content.decode('utf-8')
    for row in list(csv.reader(content.splitlines(), delimiter=','))[:5]:
        print(row)
```

---

## Forex (FX) & Cryptocurrencies

### Currency Exchange Rate `Trending`
Returns the realtime exchange rate for fiat or crypto currencies.
*   **Required `function`**: `CURRENCY_EXCHANGE_RATE`
*   **Required `from_currency`**: Base currency (e.g., `USD` or `BTC`).
*   **Required `to_currency`**: Destination currency (e.g., `JPY` or `EUR`).
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=JPY&apikey=demo'
print(requests.get(url).json())
```

### FX / Crypto Intraday `Premium`
Returns intraday time series for FX or Crypto pairs.
*   **Required `function`**: `FX_INTRADAY` or `CRYPTO_INTRADAY`
*   **Required `from_symbol` / `symbol`**: Base currency (e.g., `EUR` or `ETH`).
*   **Required `to_symbol` / `market`**: Destination currency (e.g., `USD`).
*   **Required `interval`**: `1min`, `5min`, `15min`, `30min`, `60min`.
*   **Optional `outputsize`**: `compact` (default, latest 100 points) or `full`.
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol=EUR&to_symbol=USD&interval=5min&apikey=demo'
print(requests.get(url).json())
```

### FX / Crypto Daily, Weekly, Monthly
Returns daily, weekly, or monthly historical time series for FX or Crypto.
*   **Required `function`**: `FX_DAILY`, `FX_WEEKLY`, `FX_MONTHLY`, `DIGITAL_CURRENCY_DAILY`, `DIGITAL_CURRENCY_WEEKLY`, `DIGITAL_CURRENCY_MONTHLY`.
*   **Required `from_symbol` / `symbol`**: Base currency.
*   **Required `to_symbol` / `market`**: Destination currency.
*   **Optional `outputsize`** *(Daily only)*: `compact` (default) or `full`.
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=EUR&to_symbol=USD&apikey=demo'
print(requests.get(url).json())
```

---

## Commodities

*Common Optional Parameters for Commodities:* `datatype` (`json` or `csv`)

### Gold & Silver Spot Prices `Trending`
*   **Required `function`**: `GOLD_SILVER_SPOT`
*   **Required `symbol`**: `GOLD`/`XAU` or `SILVER`/`XAG`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=GOLD_SILVER_SPOT&symbol=SILVER&apikey=demo'
print(requests.get(url).json())
```

### Gold & Silver Historical Prices `Trending`
*   **Required `function`**: `GOLD_SILVER_HISTORY`
*   **Required `symbol`**: `GOLD`/`XAU` or `SILVER`/`XAG`.
*   **Required `interval`**: `daily`, `weekly`, `monthly`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=GOLD_SILVER_HISTORY&symbol=SILVER&interval=daily&apikey=demo'
print(requests.get(url).json())
```

### Crude Oil, Natural Gas, Global Price Indexes
*   **Required `function`**: `WTI`, `BRENT`, `NATURAL_GAS`, `COPPER`, `ALUMINUM`, `WHEAT`, `CORN`, `COTTON`, `SUGAR`, `COFFEE`, `ALL_COMMODITIES`.
*   **Optional `interval`**:
    *   WTI/Brent/NatGas: `daily`, `weekly`, `monthly` (default).
    *   Others: `monthly` (default), `quarterly`, `annual`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=WTI&interval=monthly&apikey=demo'
print(requests.get(url).json())
```

---

## Economic Indicators

*Common Optional Parameters for Economic Indicators:* `datatype` (`json` or `csv`)

### GDP, Yield, Rates, CPI & More
*   **Required `function`**: `REAL_GDP`, `REAL_GDP_PER_CAPITA`, `TREASURY_YIELD`, `FEDERAL_FUNDS_RATE`, `CPI`, `INFLATION`, `RETAIL_SALES`, `DURABLES`, `UNEMPLOYMENT`, `NONFARM_PAYROLL`.
*   **Optional `interval`**:
    *   GDP: `quarterly`, `annual` (default).
    *   Yield/Fed Funds: `daily`, `weekly`, `monthly` (default).
    *   CPI: `monthly` (default), `semiannual`.
*   **Optional `maturity`** *(Treasury Yield only)*: `3month`, `2year`, `5year`, `7year`, `10year` (default), `30year`.
*   **Required `apikey`**: Your API key.
```python
import requests
url = 'https://www.alphavantage.co/query?function=TREASURY_YIELD&interval=monthly&maturity=10year&apikey=demo'
print(requests.get(url).json())
```

---

## Technical Indicators

**Common Baseline Parameters for Technical Indicators:**
*   **Required `symbol`**: The equity name (e.g., `IBM`).
*   **Required `interval`**: Time interval between points (`1min`, `5min`, `15min`, `30min`, `60min`, `daily`, `weekly`, `monthly`).
*   **Optional `month`**: Queries a specific month in history (format `YYYY-MM`).
*   **Optional `datatype`**: `json` (default) or `csv`.
*   **Optional `entitlement`**: Unset (historical), `realtime`, or `delayed`.
*   **Required `apikey`**: Your API key.

**Moving Average Mappings (`matype`):**
0 = SMA, 1 = EMA, 2 = WMA, 3 = DEMA, 4 = TEMA, 5 = TRIMA, 6 = T3, 7 = KAMA, 8 = MAMA.

### SMA, EMA, WMA, DEMA, TEMA, TRIMA, KAMA, T3
Standard Moving Averages.
*   **Required `function`**: e.g., `SMA`, `EMA`
*   **Required `time_period`**: Number of data points (e.g., `60`).
*   **Required `series_type`**: `close`, `open`, `high`, `low`.
```python
import requests
url = 'https://www.alphavantage.co/query?function=SMA&symbol=IBM&interval=weekly&time_period=10&series_type=open&apikey=demo'
print(requests.get(url).json())
```

### MAMA
MESA Adaptive Moving Average.
*   **Required `function`**: `MAMA`
*   **Required `series_type`**: `close`, `open`, `high`, `low`.
*   **Optional `fastlimit`**: Float (default `0.01`).
*   **Optional `slowlimit`**: Float (default `0.01`).
```python
import requests
url = 'https://www.alphavantage.co/query?function=MAMA&symbol=IBM&interval=daily&series_type=close&fastlimit=0.02&apikey=demo'
print(requests.get(url).json())
```

### VWAP `Premium`
Volume Weighted Average Price.
*   **Required `function`**: `VWAP`
*   *Note: Only supports intraday intervals (`1min` to `60min`).*
```python
import requests
url = 'https://www.alphavantage.co/query?function=VWAP&symbol=IBM&interval=15min&apikey=demo'
print(requests.get(url).json())
```

### MACD & MACDEXT `Premium`
Moving Average Convergence/Divergence.
*   **Required `function`**: `MACD` or `MACDEXT`
*   **Required `series_type`**: `close`, `open`, `high`, `low`.
*   **Optional `fastperiod`**: Integer (default `12`).
*   **Optional `slowperiod`**: Integer (default `26`).
*   **Optional `signalperiod`**: Integer (default `9`).
*   **Optional `fastmatype`, `slowmatype`, `signalmatype`** *(MACDEXT only)*: 0-8 (default `0`).
```python
import requests
url = 'https://www.alphavantage.co/query?function=MACD&symbol=IBM&interval=daily&series_type=open&apikey=demo'
print(requests.get(url).json())
```

### STOCH & STOCHF
Stochastic Oscillator.
*   **Required `function`**: `STOCH` or `STOCHF`
*   **Optional `fastkperiod`**: Integer (default `5`).
*   **Optional `slowkperiod`** *(STOCH only)*: Integer (default `3`).
*   **Optional `slowdperiod`** *(STOCH only)*: Integer (default `3`).
*   **Optional `fastdperiod`** *(STOCHF only)*: Integer (default `3`).
*   **Optional `slowkmatype`, `slowdmatype`, `fastdmatype`**: 0-8 (default `0`).
```python
import requests
url = 'https://www.alphavantage.co/query?function=STOCH&symbol=IBM&interval=daily&apikey=demo'
print(requests.get(url).json())
```

### RSI & STOCHRSI
Relative Strength Index.
*   **Required `function`**: `RSI` or `STOCHRSI`
*   **Required `time_period`**: Integer.
*   **Required `series_type`**: `close`, `open`, `high`, `low`.
*   **Optional `fastkperiod`, `fastdperiod`, `fastdmatype`** *(STOCHRSI only)*.
```python
import requests
url = 'https://www.alphavantage.co/query?function=RSI&symbol=IBM&interval=weekly&time_period=10&series_type=open&apikey=demo'
print(requests.get(url).json())
```

### WILLR, ADX, ADXR, MOM, CCI, CMO, ROC, ROCR, AROON, AROONOSC, MFI, DX, MINUS_DI, PLUS_DI, MINUS_DM, PLUS_DM, ATR, NATR
Standard Period-based Indicators.
*   **Required `function`**: Indicator name.
*   **Required `time_period`**: Integer.
*   **Required `series_type`** *(MOM, CMO, ROC, ROCR only)*: `close`, `open`, `high`, `low`.
```python
import requests
url = 'https://www.alphavantage.co/query?function=CCI&symbol=IBM&interval=daily&time_period=10&apikey=demo'
print(requests.get(url).json())
```

### APO & PPO
Price Oscillators.
*   **Required `function`**: `APO` or `PPO`
*   **Required `series_type`**: `close`, `open`, `high`, `low`.
*   **Optional `fastperiod`**: Integer (default `12`).
*   **Optional `slowperiod`**: Integer (default `26`).
*   **Optional `matype`**: 0-8 (default `0`).
```python
import requests
url = 'https://www.alphavantage.co/query?function=APO&symbol=IBM&interval=daily&series_type=close&fastperiod=10&matype=1&apikey=demo'
print(requests.get(url).json())
```

### BOP, TRANGE, AD, OBV
Volume & Range Indicators (no `time_period` or `series_type` needed).
*   **Required `function`**: `BOP`, `TRANGE`, `AD`, or `OBV`.
```python
import requests
url = 'https://www.alphavantage.co/query?function=OBV&symbol=IBM&interval=weekly&apikey=demo'
print(requests.get(url).json())
```

### ADOSC
Chaikin A/D Oscillator.
*   **Required `function`**: `ADOSC`
*   **Optional `fastperiod`**: Integer (default `3`).
*   **Optional `slowperiod`**: Integer (default `10`).
```python
import requests
url = 'https://www.alphavantage.co/query?function=ADOSC&symbol=IBM&interval=daily&fastperiod=5&apikey=demo'
print(requests.get(url).json())
```

### TRIX
Triple Smooth Exponential Moving Average.
*   **Required `function`**: `TRIX`
*   **Required `time_period`**: Integer.
*   **Required `series_type`**: `close`, `open`, `high`, `low`.
```python
import requests
url = 'https://www.alphavantage.co/query?function=TRIX&symbol=IBM&interval=daily&time_period=10&series_type=close&apikey=demo'
print(requests.get(url).json())
```

### ULTOSC
Ultimate Oscillator.
*   **Required `function`**: `ULTOSC`
*   **Optional `timeperiod1`**: Integer (default `7`).
*   **Optional `timeperiod2`**: Integer (default `14`).
*   **Optional `timeperiod3`**: Integer (default `28`).
```python
import requests
url = 'https://www.alphavantage.co/query?function=ULTOSC&symbol=IBM&interval=daily&timeperiod1=8&apikey=demo'
print(requests.get(url).json())
```

### BBANDS
Bollinger Bands.
*   **Required `function`**: `BBANDS`
*   **Required `time_period`**: Integer.
*   **Required `series_type`**: `close`, `open`, `high`, `low`.
*   **Optional `nbdevup`**: Standard deviation multiplier upper (default `2`).
*   **Optional `nbdevdn`**: Standard deviation multiplier lower (default `2`).
*   **Optional `matype`**: 0-8 (default `0`).
```python
import requests
url = 'https://www.alphavantage.co/query?function=BBANDS&symbol=IBM&interval=weekly&time_period=5&series_type=close&nbdevup=3&nbdevdn=3&apikey=demo'
print(requests.get(url).json())
```

### MIDPOINT & MIDPRICE
*   **Required `function`**: `MIDPOINT` or `MIDPRICE`
*   **Required `time_period`**: Integer.
*   **Required `series_type`** *(MIDPOINT only)*: `close`, `open`, `high`, `low`.
```python
import requests
url = 'https://www.alphavantage.co/query?function=MIDPRICE&symbol=IBM&interval=daily&time_period=10&apikey=demo'
print(requests.get(url).json())
```

### SAR
Parabolic SAR.
*   **Required `function`**: `SAR`
*   **Optional `acceleration`**: Float (default `0.01`).
*   **Optional `maximum`**: Float (default `0.20`).
```python
import requests
url = 'https://www.alphavantage.co/query?function=SAR&symbol=IBM&interval=weekly&acceleration=0.05&maximum=0.25&apikey=demo'
print(requests.get(url).json())
```

### HT_TRENDLINE, HT_SINE, HT_TRENDMODE, HT_DCPERIOD, HT_DCPHASE, HT_PHASOR
Hilbert Transform Indicators.
*   **Required `function`**: `HT_TRENDLINE`, `HT_SINE`, `HT_TRENDMODE`, `HT_DCPERIOD`, `HT_DCPHASE`, or `HT_PHASOR`.
*   **Required `series_type`**: `close`, `open`, `high`, `low`.
```python
import requests
url = 'https://www.alphavantage.co/query?function=HT_TRENDLINE&symbol=IBM&interval=daily&series_type=close&apikey=demo'
print(requests.get(url).json())
```

*Copyright © Alpha Vantage Inc. 2017-2026*

---

### Example Python API Wrapper / Client

For example, we could build a class that handles your API key, automatically formats the URLs, and includes built-in rate limiting (to respect the free tier's 25 requests/day limit).

Here is a quick preview of how that could look:

```python
import requests
import time

class AlphaVantageClient:
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _request(self, **kwargs):
        """Internal method to handle the API request."""
        kwargs['apikey'] = self.api_key
        response = requests.get(self.BASE_URL, params=kwargs)
        response.raise_for_status()
        return response.json()

    def get_intraday(self, symbol: str, interval: str = "5min", **kwargs):
        """TIME_SERIES_INTRADAY endpoint."""
        return self._request(
            function="TIME_SERIES_INTRADAY",
            symbol=symbol,
            interval=interval,
            **kwargs
        )

    def get_macd(self, symbol: str, interval: str = "daily", series_type: str = "close", **kwargs):
        """MACD technical indicator."""
        return self._request(
            function="MACD",
            symbol=symbol,
            interval=interval,
            series_type=series_type,
            **kwargs
        )

# Example Usage:
# client = AlphaVantageClient(api_key="demo")
# macd_data = client.get_macd("IBM")
# print(macd_data)
```
