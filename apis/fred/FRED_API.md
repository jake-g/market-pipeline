# 📈 FRED® API Developer Guide

The **FRED® API** provides programmatic access to over 800,000 economic time series from over 100 global sources.
* **API Version 1**: Ideal for querying incremental data on a series level (highly customizable).
* **API Version 2**: Ideal for pulling bulk historical data and full release observations.

---

## 🔑 1. How to Get an API Key
All requests to the FRED API require a free, 32-character alphanumeric API key.

1. **Create an account:** Register or log in with your Google account at [fred.stlouisfed.org](https://fred.stlouisfed.org/).
2. **Request a key:** Navigate to the [API Keys portal](https://fredaccount.stlouisfed.org/apikey) to generate your key.
3. **Usage:** Pass the key in all your requests using the `api_key` URL parameter.

---

## 🚦 2. Limits, Usage, & Terms of Use
*To avoid having your API access permanently revoked, you must strictly adhere to the following rules:*

### 📊 Rate Limits & Performance
* **Rate Limit:** FRED enforces a strict rate limit of **120 requests per minute**[3]. Exceeding this will return an `HTTP 429 (Too Many Requests)` error.
* **Bandwidth:** FRED reserves the right to throttle or block your key at any time if you use an unreasonable amount of bandwidth. Implement local caching for frequently accessed data [1].

### ⚖️ Legal & Attribution Requirements
* **Mandatory Attribution:** You **must** prominently display this exact notice on your application or website:
  > *"This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis."*
* **Copyrighted Data:** While the API is free, specific data series are owned by third parties and restricted by copyright. Search for the word `"Copyright"` in a series' notes to check. The API does *not* grant you rights to 3rd-party data.
* **Strict Prohibitions:**
  * ❌ Do not replicate or attempt to replace the core FRED® or ALFRED® website experience.
  * ❌ Do not use "FRED", "ALFRED", or "Federal Reserve Bank" in your app's domain/hostname (e.g., `fred.yourdomain.com` is forbidden).
  * ❌ Do not use the St. Louis Fed logo or state/imply that they endorse your application.
  * ❌ Do not cloak or conceal your identity/user-agent when making requests.

---

## 🛠 3. Pro-Tips for Developers
* **JSON Format:** By default, the FRED API returns **XML**. To get JSON (which is preferred for modern web/app development), you must append `&file_type=json` to your requests [6, 7].
* **ALFRED vs FRED:** FRED gives you the *latest* revised data. ALFRED gives you *vintage/historical* revisions (what the data actually looked like on a specific past date before revisions occurred).

---

## 📚 4. Core Endpoints Quick Reference

**Base URL:** `https://api.stlouisfed.org/`

### 📉 Series (Most Common)
| Endpoint | Description |
| :--- | :--- |
| `GET /fred/series` | Get metadata for an economic data series. |
| `GET /fred/series/observations` | **Most Used:** Fetch the actual time-series data values for a specific series. |
| `GET /fred/series/search` | Search for economic data series using keywords. |
| `GET /fred/series/updates` | Get series sorted by when they were last updated on the server. |
| `GET /fred/series/vintagedates` | Get the historical dates when a series' values were revised (ALFRED). |

### 🗂 Categories
| Endpoint | Description |
| :--- | :--- |
| `GET /fred/category` | Get metadata for a specific category by ID. |
| `GET /fred/category/children` | Get the child sub-categories for a specified parent. |
| `GET /fred/category/series` | Get all the data series within a specific category. |

### 📅 Releases & Sources
| Endpoint | Description |
| :--- | :--- |
| `GET /fred/releases` | Get all official releases of economic data. |
| `GET /fred/release/dates` | Get release dates for upcoming economic data. |
| `GET /fred/sources` | Get a list of all sources providing economic data to FRED. |

### 🏷 Tags & Maps
| Endpoint | Description |
| :--- | :--- |
| `GET /fred/tags` | Get all tags, search for tags, or get tags by name. |
| `GET /fred/tags/series` | Get the series matching specific tags. |
| `Maps API` | Allows fetching of geographic shape files and regional data. |

*(For full parameter details, visit the [Official FRED API Docs](https://fred.stlouisfed.org/docs/api/fred/)).*

---

## 💻 5. Quick Start Example (Python)

Here is a concise example of how to fetch the **US Consumer Price Index (CPI)** using Python's `requests` library and properly requesting JSON data [6, 7]:

```python
import requests

# 1. Define your credentials and target data
API_KEY = "YOUR_32_CHAR_API_KEY"
SERIES_ID = "CPIAUCSL" # Consumer Price Index ID

url = "https://api.stlouisfed.org/fred/series/observations"

# 2. Set your parameters (Notice the file_type specification)
params = {
    "series_id": SERIES_ID,
    "api_key": API_KEY,
    "file_type": "json"
}

# 3. Make the request
response = requests.get(url, params=params)

# 4. Parse the data safely
if response.status_code == 200:
    data = response.json()
    observations = data.get("observations",[])

    # Print the last 3 recorded observations
    for obs in observations[-3:]:
        print(f"Date: {obs['date']} | Value: {obs['value']}")

elif response.status_code == 429:
    print("Error 429: Rate limit of 120 req/min exceeded! Please wait.")
else:
    print(f"Failed with Status Code: {response.status_code}")
```
