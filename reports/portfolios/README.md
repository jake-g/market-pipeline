# Yahoo Finance API Credentials Setup

To use the Yahoo Finance Portfolio Fetcher (`yahoo_portfolio_fetcher.py`), you need to provide authentication details from your logged-in session.

## 🚨 IP Ban Bypass (Manual JSON Import)

If your machine's IP address gets temporarily banned by Yahoo (resulting in endless `429 Too Many Requests` errors even with a valid cookie), you can manually download your portfolio data from the browser:

1. Open Chrome and navigate directly to this API URL:
   `https://query1.finance.yahoo.com/v7/finance/desktop/portfolio?formatted=true&includeBetaVersion=1&keyMetricsModules=portfolioReturns%2CdividendPayouts%2CassetAllocation%2CsectorAllocation&lang=en-US&region=US&crumb=YOUR_CRUMB_HERE`
   *(Note: You can find this full URL in the Network tab when visiting the Portfolios page).*
2. Save the raw JSON output to a file named `portfolio.json` in the `reports/portfolios` directory.
3. Run the full pipeline wrapper in offline mode to process the localized data:
   ```bash
   ./reports/portfolios/run_pipeline.sh --offline
   ```

---

## Required Dependencies (`curl_cffi`)

Yahoo Finance has heavily increased bot detection by fingerprinting python's default `requests` library in the TLS handshake. You **MUST** use `curl_cffi` so the python script can perfectly impersonate Google Chrome, otherwise every request will be met with `429 Too Many Requests` errors.

```bash
pip install curl_cffi
```

## Extracting Credentials from Chrome

1. Open Google Chrome and navigate to [Yahoo Finance Portfolios](https://finance.yahoo.com/portfolios).
2. Ensure you are **logged in** to your Yahoo account.
3. Open **Developer Tools** (`Cmd+Option+I` on Mac or `F12` on Windows), or right-click anywhere on the page and select **Inspect**.
4. Go to the **Network** tab in Developer Tools.
5. In the top-left filter box, type `portfolio`.
6. Refresh the page (`Cmd+R` or `Ctrl+R`). Look for a network request named something like `portfolio?formatted=true...` and click on it.
7. Right-click on the request, select **Copy**, and then select **Copy as cURL**.

## Setting Up Your `.env` File

Instead of manually finding the cookie and crumb, the fetcher script will automatically prompt you for the copied cURL command if your `.env` file is missing or incomplete:

1. Copy the cURL command as described above.
2. Run the fetcher script:
   ```bash
   python reports/portfolios/yahoo_portfolio_fetcher.py --dump
   ```
3. If prompted, paste the `Copy as cURL` text and press `Enter`, then press `Ctrl+D` to finish input.
4. The script will automatically parse your `YF_COOKIE` and `YF_CRUMB` and create a `.env` file in the `reports/portfolios/` directory.

### Finding Your `YF_USER_ID`

The Yahoo portfolio API *requires* a User ID. However, the initial `portfolio` network request often **does not** contain the User ID in its URL.

If the fetcher script fails because it cannot find your User ID automatically, you will need to find it manually:

1. Go back to your Yahoo Finance Portfolios page with Developer Tools open (Network tab).
2. Create a temporary new portfolio, rename an existing one, or delete one.
3. Look for a network request that just appeared (e.g., `update`, `importPortfolio`, or just `portfolio`).
4. Click on that request and look at the **Payload** or the **Request URL**.
5. You should see a parameter called `userId=xxxxxxxxxxxxx`.
6. Copy that value (it's usually a long string of letters and numbers).
7. Open `reports/portfolios/.env` and update the `YF_USER_ID` field:
   ```env
   YF_USER_ID="xxxxxxxxxxxxx"
   ```

> [!WARNING]
> Keep these credentials private and **do not** commit the `.env` file to version control. The repository's gitignore should exclude `.env` files automatically, but double-check to be safe.


# Portfolio Processing & Reporting

The entire intelligence pipeline is automated, running unit validation, code formatting, parsing, quantitative enhancement, and finally exhaustively generating the Markdown view. Operations are heavily logged and cached into internal data siloes to maintain project cleanliness.

```bash
./reports/portfolios/run_pipeline.sh
```

**Architecture & Footprint**:
- **Logs**: Execution STDOUT and background terminal outputs are piped automatically into `logs/` at the project root via per-command `tee` hooks. Let this populate to track errors or debug missing dependencies without fighting raw console dumps.
- **TSVs**: All dynamically generated raw Yahoo CSV exports (and post-processor combined metrics files) are generated discretely inside the `reports/portfolios/tsvs/` subset directory.
- **Diff Constraints**: When fetching live Yahoo data, the code will dynamically diff your terminal responses against your cache and report raw absolute asset changes.
- **Offline Mode**: Passing `--offline` executes calculations exclusively utilizing the `reports/portfolios/portfolio.json` snapshot payload safely avoiding `api bans`.

This generates `REPORT.md` in the current folder, embedding aggregate metrics, visualizations of asset allocation, and individual breakdowns of every processed portfolio.

---

# Alternative Portfolio Fetching Approaches

While Yahoo Finance acts as a free aggregator for external accounts (like Vanguard and Schwab), it is bound by fragile DOM updates and rate limits. If you wish to build a more robust integration in the future, consider:

1. **Charles Schwab Developer API**: Official and reliable. Provides real-time positions for Schwab-held assets, but requires a formal OAuth app setup. External/linked accounts are not returned.
2. **Plaid Developer API**: The industry standard for aggregation. Connects natively to almost all brokerages uniformly, but requires hosting a Plaid-Link frontend UI to generate the access tokens.
3. **Browser Automation**: Manual CSV exports via Selenium/Playwright (e.g. logging into Schwab normally), though this is highly susceptible to 2FA restrictions and UI changes.
