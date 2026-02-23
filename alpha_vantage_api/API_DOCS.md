# Alpha Vantage API Documentation & Support

## Customer Support

### Claim your Free API Key
Claim your free key for the Alpha Vantage Stock API © with lifetime access. We highly recommend that you use a legitimate email address - this is the primary way we will contact you for feature announcements or troubleshooting (e.g., if you lose your API key). By acquiring and using an Alpha Vantage API key, you agree to our Terms of Service and Privacy Policy.

*(To claim your key, please visit the Alpha Vantage website and submit the API Key form specifying your occupation, organization, and email).*

### Frequently Asked Questions

**I have got my API key. What's next?**
Welcome to Alpha Vantage! Getting started is easy:
*   Our official API documentation includes detailed information and sample code for our 100+ data API offerings.
*   If you are a **spreadsheet user** (e.g., Excel or Google Sheets), please check out our dedicated spreadsheet add-ons.
*   Want to power your ✨LLMs or AI agents with financial data? Please try out the official Alpha Vantage MCP server today!

**Are there usage/frequency limits for the API service?**
We are pleased to provide free stock API service covering the majority of our datasets for up to **25 requests per day**. If you would like to target a larger API call volume, please visit premium membership.

**Why is your realtime and 15-minute delayed US stock market data premium-only? Can I access the data for free?**
Realtime and 15-minute delayed US market data is regulated by the stock exchanges, FINRA, and the SEC. As a NASDAQ-licensed data provider, we provide one of the *most affordable exchange-approved* realtime and 15-minute delayed data offerings in the market. If you find other data sources that are "free", please be vigilant and ensure they are properly licensed by the exchanges to minimize the risk of opening yourself up to fees, penalties, or other legal actions from the regulatory bodies.

**You support both raw and adjusted intraday/daily/weekly/monthly time series. What adjustment method are you using?**
We adjust our open, high, low, close, and volume data by both splits and cash dividend events, which is considered an industry standard methodology. And for many of the API endpoints that return adjusted data, we also provide an option to return the raw, unadjusted data.

**I have built a library/wrapper for Alpha Vantage with a specific programming language. May I open-source it on GitHub?**
Certainly! However, we ask that your language-specific library/wrapper preserves the content of our JSON/CSV responses in *both* success and error cases.

**I would like to improve an existing API or propose a new technical indicator / feature. What should I do?**
Please share your feature requests with us at `support@alphavantage.co`.

**Got more questions, thoughts, or comments?**
Please reach out to `support@alphavantage.co` anytime! If you are looking to cancel your premium subscription, you may also use our self-service workflow.

---

## Time Series Stock Data APIs

### TIME_SERIES_INTRADAY `Trending` `Premium`
Returns current and 20+ years of historical intraday OHLCV time series covering pre-market and post-market hours.
*   **Required:** `function=TIME_SERIES_INTRADAY`, `symbol`, `interval` (`1min`, `5min`, `15min`, `30min`, `60min`), `apikey`
*   **Optional:** `adjusted`, `extended_hours`, `month` (YYYY-MM), `outputsize` (`compact`, `full`), `datatype`, `entitlement` (`realtime`, `delayed`)
```python
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey=demo'
print(requests.get(url).json())
```

### TIME_SERIES_DAILY
Returns raw (as-traded) daily time series (date, daily open, high, low, close, volume).
*   **Required:** `function=TIME_SERIES_DAILY`, `symbol`, `apikey`
*   **Optional:** `outputsize` (`compact`, `full`), `datatype`
```python
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### TIME_SERIES_DAILY_ADJUSTED `Trending` `Premium`
Returns raw daily OHLCV values, adjusted close values, and historical split/dividend events.
*   **Required:** `function=TIME_SERIES_DAILY_ADJUSTED`, `symbol`, `apikey`
*   **Optional:** `outputsize`, `datatype`, `entitlement`
```python
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### TIME_SERIES_WEEKLY
Returns weekly time series (last trading day of each week, open, high, low, close, volume).
*   **Required:** `function=TIME_SERIES_WEEKLY`, `symbol`, `apikey`
*   **Optional:** `datatype`
```python
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### TIME_SERIES_WEEKLY_ADJUSTED
Returns weekly adjusted time series (including adjusted close and weekly dividend).
*   **Required:** `function=TIME_SERIES_WEEKLY_ADJUSTED`, `symbol`, `apikey`
*   **Optional:** `datatype`
```python
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_WEEKLY_ADJUSTED&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### TIME_SERIES_MONTHLY
Returns monthly time series.
*   **Required:** `function=TIME_SERIES_MONTHLY`, `symbol`, `apikey`
*   **Optional:** `datatype`
```python
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### TIME_SERIES_MONTHLY_ADJUSTED
Returns monthly adjusted time series.
*   **Required:** `function=TIME_SERIES_MONTHLY_ADJUSTED`, `symbol`, `apikey`
*   **Optional:** `datatype`
```python
url = 'https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY_ADJUSTED&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Quote Endpoint `Trending`
Returns the latest price and volume information for a ticker.
*   **Required:** `function=GLOBAL_QUOTE`, `symbol`, `apikey`
*   **Optional:** `datatype`, `entitlement`
```python
url = 'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Realtime Bulk Quotes `Premium`
Returns realtime quotes for US-traded symbols in bulk, accepting up to 100 symbols.
*   **Required:** `function=REALTIME_BULK_QUOTES`, `symbol` (e.g., MSFT,AAPL), `apikey`
*   **Optional:** `datatype`
```python
url = 'https://www.alphavantage.co/query?function=REALTIME_BULK_QUOTES&symbol=MSFT,AAPL,IBM&apikey=demo'
print(requests.get(url).json())
```

### Search Endpoint `Utility`
Returns best-matching symbols and market info based on keywords.
*   **Required:** `function=SYMBOL_SEARCH`, `keywords`, `apikey`
*   **Optional:** `datatype`
```python
url = 'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords=tesco&apikey=demo'
print(requests.get(url).json())
```

### Global Market Open & Close Status `Utility`
Returns the current market status of major trading venues.
*   **Required:** `function=MARKET_STATUS`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=MARKET_STATUS&apikey=demo'
print(requests.get(url).json())
```

---

## Options Data APIs

### Realtime Options `Trending` `Premium`
Returns realtime US options data with full market coverage.
*   **Required:** `function=REALTIME_OPTIONS`, `symbol`, `apikey`
*   **Optional:** `require_greeks` (true/false), `contract`, `datatype`
```python
url = 'https://www.alphavantage.co/query?function=REALTIME_OPTIONS&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Historical Options `Trending` `Premium`
Returns the full historical options chain for a specific symbol on a specific date.
*   **Required:** `function=HISTORICAL_OPTIONS`, `symbol`, `apikey`
*   **Optional:** `date` (YYYY-MM-DD), `datatype`
```python
url = 'https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol=IBM&date=2017-11-15&apikey=demo'
print(requests.get(url).json())
```

---

## Alpha Intelligence™

### Market News & Sentiment `Trending`
Returns live and historical market news & sentiment data.
*   **Required:** `function=NEWS_SENTIMENT`, `apikey`
*   **Optional:** `tickers`, `topics`, `time_from`, `time_to`, `sort`, `limit`
```python
url = 'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers=AAPL&apikey=demo'
print(requests.get(url).json())
```

### Earnings Call Transcript `Trending`
Returns the earnings call transcript.
*   **Required:** `function=EARNINGS_CALL_TRANSCRIPT`, `symbol`, `quarter` (e.g., 2024Q1), `apikey`
```python
url = 'https://www.alphavantage.co/query?function=EARNINGS_CALL_TRANSCRIPT&symbol=IBM&quarter=2024Q1&apikey=demo'
print(requests.get(url).json())
```

### Top Gainers, Losers, and Most Actively Traded Tickers
*   **Required:** `function=TOP_GAINERS_LOSERS`, `apikey`
*   **Optional:** `entitlement`
```python
url = 'https://www.alphavantage.co/query?function=TOP_GAINERS_LOSERS&apikey=demo'
print(requests.get(url).json())
```

### Insider Transactions `Trending`
*   **Required:** `function=INSIDER_TRANSACTIONS`, `symbol`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=INSIDER_TRANSACTIONS&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Advanced Analytics (Fixed Window)
Returns advanced analytics metrics (total return, variance, correlation, etc.) for a fixed window.
*   **Required:** `function=ANALYTICS_FIXED_WINDOW`, `SYMBOLS`, `RANGE`, `INTERVAL`, `CALCULATIONS`, `apikey`
*   **Optional:** `OHLC`
```python
url = 'https://alphavantageapi.co/timeseries/analytics?SYMBOLS=AAPL,MSFT,IBM&RANGE=2023-07-01&RANGE=2023-08-31&INTERVAL=DAILY&OHLC=close&CALCULATIONS=MEAN,STDDEV,CORRELATION&apikey=demo'
print(requests.get(url).json())
```

### Advanced Analytics (Sliding Window) `Trending`
Returns advanced analytics over sliding time windows.
*   **Required:** `function=ANALYTICS_SLIDING_WINDOW`, `SYMBOLS`, `RANGE`, `INTERVAL`, `WINDOW_SIZE`, `CALCULATIONS`, `apikey`
*   **Optional:** `OHLC`
```python
url = 'https://alphavantageapi.co/timeseries/running_analytics?SYMBOLS=AAPL,IBM&RANGE=2month&INTERVAL=DAILY&OHLC=close&WINDOW_SIZE=20&CALCULATIONS=MEAN,STDDEV(annualized=True)&apikey=demo'
print(requests.get(url).json())
```

---

## Fundamental Data

### Company Overview `Trending`
*   **Required:** `function=OVERVIEW`, `symbol`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=OVERVIEW&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### ETF Profile & Holdings
*   **Required:** `function=ETF_PROFILE`, `symbol`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=ETF_PROFILE&symbol=QQQ&apikey=demo'
print(requests.get(url).json())
```

### Corporate Action - Dividends
*   **Required:** `function=DIVIDENDS`, `symbol`, `apikey`
*   **Optional:** `datatype`
```python
url = 'https://www.alphavantage.co/query?function=DIVIDENDS&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Corporate Action - Splits
*   **Required:** `function=SPLITS`, `symbol`, `apikey`
*   **Optional:** `datatype`
```python
url = 'https://www.alphavantage.co/query?function=SPLITS&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### INCOME_STATEMENT
*   **Required:** `function=INCOME_STATEMENT`, `symbol`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### BALANCE_SHEET
*   **Required:** `function=BALANCE_SHEET`, `symbol`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=BALANCE_SHEET&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### CASH_FLOW
*   **Required:** `function=CASH_FLOW`, `symbol`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=CASH_FLOW&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### SHARES_OUTSTANDING
*   **Required:** `function=SHARES_OUTSTANDING`, `symbol`, `apikey`
*   **Optional:** `datatype`
```python
url = 'https://www.alphavantage.co/query?function=SHARES_OUTSTANDING&symbol=MSFT&apikey=demo'
print(requests.get(url).json())
```

### Earnings History
*   **Required:** `function=EARNINGS`, `symbol`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=EARNINGS&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Earnings Estimates `Trending`
*   **Required:** `function=EARNINGS_ESTIMATES`, `symbol`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=EARNINGS_ESTIMATES&symbol=IBM&apikey=demo'
print(requests.get(url).json())
```

### Listing & Delisting Status (CSV Only)
*   **Required:** `function=LISTING_STATUS`, `apikey`
*   **Optional:** `date`, `state` (`active`, `delisted`)
```python
import csv

CSV_URL = 'https://www.alphavantage.co/query?function=LISTING_STATUS&apikey=demo'
with requests.Session() as s:
    download = s.get(CSV_URL)
    decoded_content = download.content.decode('utf-8')
    cr = csv.reader(decoded_content.splitlines(), delimiter=',')
    my_list = list(cr)
    for row in my_list[:5]:
        print(row)
```

### Earnings Calendar (CSV Only)
*   **Required:** `function=EARNINGS_CALENDAR`, `apikey`
*   **Optional:** `symbol`, `horizon` (`3month`, `6month`, `12month`)
```python
import csv

CSV_URL = 'https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey=demo'
with requests.Session() as s:
    download = s.get(CSV_URL)
    decoded_content = download.content.decode('utf-8')
    cr = csv.reader(decoded_content.splitlines(), delimiter=',')
    for row in list(cr)[:5]:
        print(row)
```

### IPO Calendar (CSV Only)
*   **Required:** `function=IPO_CALENDAR`, `apikey`
```python
import csv

CSV_URL = 'https://www.alphavantage.co/query?function=IPO_CALENDAR&apikey=demo'
with requests.Session() as s:
    download = s.get(CSV_URL)
    decoded_content = download.content.decode('utf-8')
    cr = csv.reader(decoded_content.splitlines(), delimiter=',')
    for row in list(cr)[:5]:
        print(row)
```

---

## Foreign Exchange Rates (FX)

### CURRENCY_EXCHANGE_RATE `Trending`
*   **Required:** `function=CURRENCY_EXCHANGE_RATE`, `from_currency`, `to_currency`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=JPY&apikey=demo'
print(requests.get(url).json())
```

### FX_INTRADAY `Premium` `Trending`
*   **Required:** `function=FX_INTRADAY`, `from_symbol`, `to_symbol`, `interval`, `apikey`
*   **Optional:** `outputsize`, `datatype`
```python
url = 'https://www.alphavantage.co/query?function=FX_INTRADAY&from_symbol=EUR&to_symbol=USD&interval=5min&apikey=demo'
print(requests.get(url).json())
```

### FX_DAILY
*   **Required:** `function=FX_DAILY`, `from_symbol`, `to_symbol`, `apikey`
*   **Optional:** `outputsize`, `datatype`
```python
url = 'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=EUR&to_symbol=USD&apikey=demo'
print(requests.get(url).json())
```

### FX_WEEKLY
*   **Required:** `function=FX_WEEKLY`, `from_symbol`, `to_symbol`, `apikey`
*   **Optional:** `datatype`
```python
url = 'https://www.alphavantage.co/query?function=FX_WEEKLY&from_symbol=EUR&to_symbol=USD&apikey=demo'
print(requests.get(url).json())
```

### FX_MONTHLY
*   **Required:** `function=FX_MONTHLY`, `from_symbol`, `to_symbol`, `apikey`
*   **Optional:** `datatype`
```python
url = 'https://www.alphavantage.co/query?function=FX_MONTHLY&from_symbol=EUR&to_symbol=USD&apikey=demo'
print(requests.get(url).json())
```

---

## Digital & Crypto Currencies

### CRYPTO_INTRADAY `Trending` `Premium`
*   **Required:** `function=CRYPTO_INTRADAY`, `symbol`, `market`, `interval`, `apikey`
*   **Optional:** `outputsize`, `datatype`
```python
url = 'https://www.alphavantage.co/query?function=CRYPTO_INTRADAY&symbol=ETH&market=USD&interval=5min&apikey=demo'
print(requests.get(url).json())
```

### DIGITAL_CURRENCY_DAILY
*   **Required:** `function=DIGITAL_CURRENCY_DAILY`, `symbol`, `market`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol=BTC&market=EUR&apikey=demo'
print(requests.get(url).json())
```

### DIGITAL_CURRENCY_WEEKLY `Trending`
*   **Required:** `function=DIGITAL_CURRENCY_WEEKLY`, `symbol`, `market`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_WEEKLY&symbol=BTC&market=EUR&apikey=demo'
print(requests.get(url).json())
```

### DIGITAL_CURRENCY_MONTHLY `Trending`
*   **Required:** `function=DIGITAL_CURRENCY_MONTHLY`, `symbol`, `market`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_MONTHLY&symbol=BTC&market=EUR&apikey=demo'
print(requests.get(url).json())
```

---

## Commodities

*(For all endpoints below, you may optionally include `datatype`)*

### Gold & Silver Spot Prices `Trending`
*   **Required:** `function=GOLD_SILVER_SPOT`, `symbol` (`GOLD`/`XAU` or `SILVER`/`XAG`), `apikey`
```python
url = 'https://www.alphavantage.co/query?function=GOLD_SILVER_SPOT&symbol=SILVER&apikey=demo'
print(requests.get(url).json())
```

### Gold & Silver Historical Prices `Trending`
*   **Required:** `function=GOLD_SILVER_HISTORY`, `symbol`, `interval` (`daily`, `weekly`, `monthly`), `apikey`
```python
url = 'https://www.alphavantage.co/query?function=GOLD_SILVER_HISTORY&symbol=SILVER&interval=daily&apikey=demo'
print(requests.get(url).json())
```

### Crude Oil Prices: WTI `Trending`
*   **Required:** `function=WTI`, `apikey`
*   **Optional:** `interval` (`daily`, `weekly`, `monthly`)
```python
url = 'https://www.alphavantage.co/query?function=WTI&interval=monthly&apikey=demo'
print(requests.get(url).json())
```

### Crude Oil Prices (Brent) `Trending`
*   **Required:** `function=BRENT`, `apikey`
*   **Optional:** `interval`
```python
url = 'https://www.alphavantage.co/query?function=BRENT&interval=monthly&apikey=demo'
print(requests.get(url).json())
```

### Natural Gas
*   **Required:** `function=NATURAL_GAS`, `apikey`
*   **Optional:** `interval`
```python
url = 'https://www.alphavantage.co/query?function=NATURAL_GAS&interval=monthly&apikey=demo'
print(requests.get(url).json())
```

### Global Price of Copper
*   **Required:** `function=COPPER`, `apikey`
*   **Optional:** `interval` (`monthly`, `quarterly`, `annual`)
```python
url = 'https://www.alphavantage.co/query?function=COPPER&interval=monthly&apikey=demo'
print(requests.get(url).json())
```

### Global Price of Aluminum
*   **Required:** `function=ALUMINUM`, `apikey`
*   **Optional:** `interval` (`monthly`, `quarterly`, `annual`)
```python
url = 'https://www.alphavantage.co/query?function=ALUMINUM&interval=monthly&apikey=demo'
print(requests.get(url).json())
```

### Global Price of Wheat
*   **Required:** `function=WHEAT`, `apikey`
*   **Optional:** `interval` (`monthly`, `quarterly`, `annual`)
```python
url = 'https://www.alphavantage.co/query?function=WHEAT&interval=monthly&apikey=demo'
print(requests.get(url).json())
```

### Global Price of Corn
*   **Required:** `function=CORN`, `apikey`
*   **Optional:** `interval` (`monthly`, `quarterly`, `annual`)
```python
url = 'https://www.alphavantage.co/query?function=CORN&interval=monthly&apikey=demo'
print(requests.get(url).json())
```

### Global Price of Cotton
*   **Required:** `function=COTTON`, `apikey`
*   **Optional:** `interval` (`monthly`, `quarterly`, `annual`)
```python
url = 'https://www.alphavantage.co/query?function=COTTON&interval=monthly&apikey=demo'
print(requests.get(url).json())
```

### Global Price of Sugar
*   **Required:** `function=SUGAR`, `apikey`
*   **Optional:** `interval` (`monthly`, `quarterly`, `annual`)
```python
url = 'https://www.alphavantage.co/query?function=SUGAR&interval=monthly&apikey=demo'
print(requests.get(url).json())
```

### Global Price of Coffee
*   **Required:** `function=COFFEE`, `apikey`
*   **Optional:** `interval` (`monthly`, `quarterly`, `annual`)
```python
url = 'https://www.alphavantage.co/query?function=COFFEE&interval=monthly&apikey=demo'
print(requests.get(url).json())
```

### Global Price Index of All Commodities
*   **Required:** `function=ALL_COMMODITIES`, `apikey`
*   **Optional:** `interval` (`monthly`, `quarterly`, `annual`)
```python
url = 'https://www.alphavantage.co/query?function=ALL_COMMODITIES&interval=monthly&apikey=demo'
print(requests.get(url).json())
```

---

## Economic Indicators

*(For all endpoints below, you may optionally include `datatype`)*

### REAL_GDP `Trending`
*   **Required:** `function=REAL_GDP`, `apikey`
*   **Optional:** `interval` (`quarterly`, `annual`)
```python
url = 'https://www.alphavantage.co/query?function=REAL_GDP&interval=annual&apikey=demo'
print(requests.get(url).json())
```

### REAL_GDP_PER_CAPITA
*   **Required:** `function=REAL_GDP_PER_CAPITA`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=REAL_GDP_PER_CAPITA&apikey=demo'
print(requests.get(url).json())
```

### TREASURY_YIELD `Trending`
*   **Required:** `function=TREASURY_YIELD`, `apikey`
*   **Optional:** `interval` (`daily`, `weekly`, `monthly`), `maturity` (`3month`, `2year`, `5year`, `7year`, `10year`, `30year`)
```python
url = 'https://www.alphavantage.co/query?function=TREASURY_YIELD&interval=monthly&maturity=10year&apikey=demo'
print(requests.get(url).json())
```

### FEDERAL_FUNDS_RATE
*   **Required:** `function=FEDERAL_FUNDS_RATE`, `apikey`
*   **Optional:** `interval` (`daily`, `weekly`, `monthly`)
```python
url = 'https://www.alphavantage.co/query?function=FEDERAL_FUNDS_RATE&interval=monthly&apikey=demo'
print(requests.get(url).json())
```

### CPI
*   **Required:** `function=CPI`, `apikey`
*   **Optional:** `interval` (`monthly`, `semiannual`)
```python
url = 'https://www.alphavantage.co/query?function=CPI&interval=monthly&apikey=demo'
print(requests.get(url).json())
```

### INFLATION
*   **Required:** `function=INFLATION`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=INFLATION&apikey=demo'
print(requests.get(url).json())
```

### RETAIL_SALES
*   **Required:** `function=RETAIL_SALES`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=RETAIL_SALES&apikey=demo'
print(requests.get(url).json())
```

### DURABLES
*   **Required:** `function=DURABLES`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=DURABLES&apikey=demo'
print(requests.get(url).json())
```

### UNEMPLOYMENT
*   **Required:** `function=UNEMPLOYMENT`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=UNEMPLOYMENT&apikey=demo'
print(requests.get(url).json())
```

### NONFARM_PAYROLL
*   **Required:** `function=NONFARM_PAYROLL`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=NONFARM_PAYROLL&apikey=demo'
print(requests.get(url).json())
```

---

## Technical Indicators

**Common Optional Parameters across Technical Indicators:**
*   `month` (YYYY-MM)
*   `datatype` (`json` or `csv`)
*   `entitlement` (`realtime`, `delayed`)

### SMA `Trending`
Simple Moving Average.
*   **Required:** `function=SMA`, `symbol`, `interval`, `time_period`, `series_type` (`close`, `open`, `high`, `low`), `apikey`
```python
url = 'https://www.alphavantage.co/query?function=SMA&symbol=IBM&interval=weekly&time_period=10&series_type=open&apikey=demo'
print(requests.get(url).json())
```

### EMA `Trending`
Exponential Moving Average.
*   **Required:** `function=EMA`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=EMA&symbol=IBM&interval=weekly&time_period=10&series_type=open&apikey=demo'
print(requests.get(url).json())
```

### WMA
Weighted Moving Average.
*   **Required:** `function=WMA`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=WMA&symbol=IBM&interval=weekly&time_period=10&series_type=open&apikey=demo'
print(requests.get(url).json())
```

### DEMA
Double Exponential Moving Average.
*   **Required:** `function=DEMA`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=DEMA&symbol=IBM&interval=weekly&time_period=10&series_type=open&apikey=demo'
print(requests.get(url).json())
```

### TEMA
Triple Exponential Moving Average.
*   **Required:** `function=TEMA`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=TEMA&symbol=IBM&interval=weekly&time_period=10&series_type=open&apikey=demo'
print(requests.get(url).json())
```

### TRIMA
Triangular Moving Average.
*   **Required:** `function=TRIMA`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=TRIMA&symbol=IBM&interval=weekly&time_period=10&series_type=open&apikey=demo'
print(requests.get(url).json())
```

### KAMA
Kaufman Adaptive Moving Average.
*   **Required:** `function=KAMA`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=KAMA&symbol=IBM&interval=weekly&time_period=10&series_type=open&apikey=demo'
print(requests.get(url).json())
```

### MAMA
MESA Adaptive Moving Average.
*   **Required:** `function=MAMA`, `symbol`, `interval`, `series_type`, `apikey`
*   **Optional:** `fastlimit`, `slowlimit`
```python
url = 'https://www.alphavantage.co/query?function=MAMA&symbol=IBM&interval=daily&series_type=close&fastlimit=0.02&apikey=demo'
print(requests.get(url).json())
```

### VWAP `Trending` `Premium`
Volume Weighted Average Price.
*   **Required:** `function=VWAP`, `symbol`, `interval` (`1min` through `60min`), `apikey`
```python
url = 'https://www.alphavantage.co/query?function=VWAP&symbol=IBM&interval=15min&apikey=demo'
print(requests.get(url).json())
```

### T3
Tilson moving average.
*   **Required:** `function=T3`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=T3&symbol=IBM&interval=weekly&time_period=10&series_type=open&apikey=demo'
print(requests.get(url).json())
```

### MACD `Trending` `Premium`
Moving average convergence / divergence.
*   **Required:** `function=MACD`, `symbol`, `interval`, `series_type`, `apikey`
*   **Optional:** `fastperiod`, `slowperiod`, `signalperiod`
```python
url = 'https://www.alphavantage.co/query?function=MACD&symbol=IBM&interval=daily&series_type=open&apikey=demo'
print(requests.get(url).json())
```

### MACDEXT
MACD with controllable moving average type.
*   **Required:** `function=MACDEXT`, `symbol`, `interval`, `series_type`, `apikey`
*   **Optional:** `fastperiod`, `slowperiod`, `signalperiod`, `fastmatype` (0-8), `slowmatype` (0-8), `signalmatype` (0-8)
```python
url = 'https://www.alphavantage.co/query?function=MACDEXT&symbol=IBM&interval=daily&series_type=open&apikey=demo'
print(requests.get(url).json())
```

### STOCH `Trending`
Stochastic oscillator.
*   **Required:** `function=STOCH`, `symbol`, `interval`, `apikey`
*   **Optional:** `fastkperiod`, `slowkperiod`, `slowdperiod`, `slowkmatype` (0-8), `slowdmatype` (0-8)
```python
url = 'https://www.alphavantage.co/query?function=STOCH&symbol=IBM&interval=daily&apikey=demo'
print(requests.get(url).json())
```

### STOCHF
Stochastic fast.
*   **Required:** `function=STOCHF`, `symbol`, `interval`, `apikey`
*   **Optional:** `fastkperiod`, `fastdperiod`, `fastdmatype` (0-8)
```python
url = 'https://www.alphavantage.co/query?function=STOCHF&symbol=IBM&interval=daily&apikey=demo'
print(requests.get(url).json())
```

### RSI `Trending`
Relative strength index.
*   **Required:** `function=RSI`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=RSI&symbol=IBM&interval=weekly&time_period=10&series_type=open&apikey=demo'
print(requests.get(url).json())
```

### STOCHRSI
Stochastic relative strength index.
*   **Required:** `function=STOCHRSI`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
*   **Optional:** `fastkperiod`, `fastdperiod`, `fastdmatype` (0-8)
```python
url = 'https://www.alphavantage.co/query?function=STOCHRSI&symbol=IBM&interval=daily&time_period=10&series_type=close&fastkperiod=6&fastdmatype=1&apikey=demo'
print(requests.get(url).json())
```

### WILLR
Williams' %R.
*   **Required:** `function=WILLR`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=WILLR&symbol=IBM&interval=daily&time_period=10&apikey=demo'
print(requests.get(url).json())
```

### ADX `Trending`
Average directional movement index.
*   **Required:** `function=ADX`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=ADX&symbol=IBM&interval=daily&time_period=10&apikey=demo'
print(requests.get(url).json())
```

### ADXR
Average directional movement index rating.
*   **Required:** `function=ADXR`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=ADXR&symbol=IBM&interval=daily&time_period=10&apikey=demo'
print(requests.get(url).json())
```

### APO
Absolute price oscillator.
*   **Required:** `function=APO`, `symbol`, `interval`, `series_type`, `apikey`
*   **Optional:** `fastperiod`, `slowperiod`, `matype` (0-8)
```python
url = 'https://www.alphavantage.co/query?function=APO&symbol=IBM&interval=daily&series_type=close&fastperiod=10&matype=1&apikey=demo'
print(requests.get(url).json())
```

### PPO
Percentage price oscillator.
*   **Required:** `function=PPO`, `symbol`, `interval`, `series_type`, `apikey`
*   **Optional:** `fastperiod`, `slowperiod`, `matype` (0-8)
```python
url = 'https://www.alphavantage.co/query?function=PPO&symbol=IBM&interval=daily&series_type=close&fastperiod=10&matype=1&apikey=demo'
print(requests.get(url).json())
```

### MOM
Momentum values.
*   **Required:** `function=MOM`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=MOM&symbol=IBM&interval=daily&time_period=10&series_type=close&apikey=demo'
print(requests.get(url).json())
```

### BOP
Balance of power.
*   **Required:** `function=BOP`, `symbol`, `interval`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=BOP&symbol=IBM&interval=daily&apikey=demo'
print(requests.get(url).json())
```

### CCI `Trending`
Commodity channel index.
*   **Required:** `function=CCI`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=CCI&symbol=IBM&interval=daily&time_period=10&apikey=demo'
print(requests.get(url).json())
```

### CMO
Chande momentum oscillator.
*   **Required:** `function=CMO`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=CMO&symbol=IBM&interval=weekly&time_period=10&series_type=close&apikey=demo'
print(requests.get(url).json())
```

### ROC
Rate of change.
*   **Required:** `function=ROC`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=ROC&symbol=IBM&interval=weekly&time_period=10&series_type=close&apikey=demo'
print(requests.get(url).json())
```

### ROCR
Rate of change ratio.
*   **Required:** `function=ROCR`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=ROCR&symbol=IBM&interval=daily&time_period=10&series_type=close&apikey=demo'
print(requests.get(url).json())
```

### AROON `Trending`
Aroon indicator.
*   **Required:** `function=AROON`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=AROON&symbol=IBM&interval=daily&time_period=14&apikey=demo'
print(requests.get(url).json())
```

### AROONOSC
Aroon oscillator.
*   **Required:** `function=AROONOSC`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=AROONOSC&symbol=IBM&interval=daily&time_period=10&apikey=demo'
print(requests.get(url).json())
```

### MFI
Money flow index.
*   **Required:** `function=MFI`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=MFI&symbol=IBM&interval=weekly&time_period=10&apikey=demo'
print(requests.get(url).json())
```

### TRIX
1-day rate of change of a triple smooth exponential moving average.
*   **Required:** `function=TRIX`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=TRIX&symbol=IBM&interval=daily&time_period=10&series_type=close&apikey=demo'
print(requests.get(url).json())
```

### ULTOSC
Ultimate oscillator.
*   **Required:** `function=ULTOSC`, `symbol`, `interval`, `apikey`
*   **Optional:** `timeperiod1`, `timeperiod2`, `timeperiod3`
```python
url = 'https://www.alphavantage.co/query?function=ULTOSC&symbol=IBM&interval=daily&timeperiod1=8&apikey=demo'
print(requests.get(url).json())
```

### DX
Directional movement index.
*   **Required:** `function=DX`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=DX&symbol=IBM&interval=daily&time_period=10&apikey=demo'
print(requests.get(url).json())
```

### MINUS_DI
Minus directional indicator.
*   **Required:** `function=MINUS_DI`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=MINUS_DI&symbol=IBM&interval=weekly&time_period=10&apikey=demo'
print(requests.get(url).json())
```

### PLUS_DI
Plus directional indicator.
*   **Required:** `function=PLUS_DI`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=PLUS_DI&symbol=IBM&interval=daily&time_period=10&apikey=demo'
print(requests.get(url).json())
```

### MINUS_DM
Minus directional movement.
*   **Required:** `function=MINUS_DM`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=MINUS_DM&symbol=IBM&interval=daily&time_period=10&apikey=demo'
print(requests.get(url).json())
```

### PLUS_DM
Plus directional movement.
*   **Required:** `function=PLUS_DM`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=PLUS_DM&symbol=IBM&interval=daily&time_period=10&apikey=demo'
print(requests.get(url).json())
```

### BBANDS `Trending`
Bollinger bands.
*   **Required:** `function=BBANDS`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
*   **Optional:** `nbdevup`, `nbdevdn`, `matype` (0-8)
```python
url = 'https://www.alphavantage.co/query?function=BBANDS&symbol=IBM&interval=weekly&time_period=5&series_type=close&nbdevup=3&nbdevdn=3&apikey=demo'
print(requests.get(url).json())
```

### MIDPOINT
Midpoint = (highest value + lowest value)/2.
*   **Required:** `function=MIDPOINT`, `symbol`, `interval`, `time_period`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=MIDPOINT&symbol=IBM&interval=daily&time_period=10&series_type=close&apikey=demo'
print(requests.get(url).json())
```

### MIDPRICE
Midpoint price = (highest high + lowest low)/2.
*   **Required:** `function=MIDPRICE`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=MIDPRICE&symbol=IBM&interval=daily&time_period=10&apikey=demo'
print(requests.get(url).json())
```

### SAR
Parabolic SAR.
*   **Required:** `function=SAR`, `symbol`, `interval`, `apikey`
*   **Optional:** `acceleration`, `maximum`
```python
url = 'https://www.alphavantage.co/query?function=SAR&symbol=IBM&interval=weekly&acceleration=0.05&maximum=0.25&apikey=demo'
print(requests.get(url).json())
```

### TRANGE
True range.
*   **Required:** `function=TRANGE`, `symbol`, `interval`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=TRANGE&symbol=IBM&interval=daily&apikey=demo'
print(requests.get(url).json())
```

### ATR
Average true range.
*   **Required:** `function=ATR`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=ATR&symbol=IBM&interval=daily&time_period=14&apikey=demo'
print(requests.get(url).json())
```

### NATR
Normalized average true range.
*   **Required:** `function=NATR`, `symbol`, `interval`, `time_period`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=NATR&symbol=IBM&interval=weekly&time_period=14&apikey=demo'
print(requests.get(url).json())
```

### AD `Trending`
Chaikin A/D line.
*   **Required:** `function=AD`, `symbol`, `interval`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=AD&symbol=IBM&interval=daily&apikey=demo'
print(requests.get(url).json())
```

### ADOSC
Chaikin A/D oscillator.
*   **Required:** `function=ADOSC`, `symbol`, `interval`, `apikey`
*   **Optional:** `fastperiod`, `slowperiod`
```python
url = 'https://www.alphavantage.co/query?function=ADOSC&symbol=IBM&interval=daily&fastperiod=5&apikey=demo'
print(requests.get(url).json())
```

### OBV `Trending`
On balance volume.
*   **Required:** `function=OBV`, `symbol`, `interval`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=OBV&symbol=IBM&interval=weekly&apikey=demo'
print(requests.get(url).json())
```

### HT_TRENDLINE
Hilbert transform, instantaneous trendline.
*   **Required:** `function=HT_TRENDLINE`, `symbol`, `interval`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=HT_TRENDLINE&symbol=IBM&interval=daily&series_type=close&apikey=demo'
print(requests.get(url).json())
```

### HT_SINE
Hilbert transform, sine wave.
*   **Required:** `function=HT_SINE`, `symbol`, `interval`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=HT_SINE&symbol=IBM&interval=daily&series_type=close&apikey=demo'
print(requests.get(url).json())
```

### HT_TRENDMODE
Hilbert transform, trend vs cycle mode.
*   **Required:** `function=HT_TRENDMODE`, `symbol`, `interval`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=HT_TRENDMODE&symbol=IBM&interval=weekly&series_type=close&apikey=demo'
print(requests.get(url).json())
```

### HT_DCPERIOD
Hilbert transform, dominant cycle period.
*   **Required:** `function=HT_DCPERIOD`, `symbol`, `interval`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=HT_DCPERIOD&symbol=IBM&interval=daily&series_type=close&apikey=demo'
print(requests.get(url).json())
```

### HT_DCPHASE
Hilbert transform, dominant cycle phase.
*   **Required:** `function=HT_DCPHASE`, `symbol`, `interval`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=HT_DCPHASE&symbol=IBM&interval=daily&series_type=close&apikey=demo'
print(requests.get(url).json())
```

### HT_PHASOR
Hilbert transform, phasor components.
*   **Required:** `function=HT_PHASOR`, `symbol`, `interval`, `series_type`, `apikey`
```python
url = 'https://www.alphavantage.co/query?function=HT_PHASOR&symbol=IBM&interval=weekly&series_type=close&apikey=demo'
print(requests.get(url).json())
```
