"""Fetches portfolio data from Yahoo Finance."""

import argparse
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

# Add the project root to sys.path so 'config' can be resolved
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
  sys.path.insert(0, PROJECT_ROOT)

from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs
from urllib.parse import urlparse

from curl_cffi import requests
from fake_useragent import UserAgent
import pandas as pd

import config

logger = logging.getLogger(__name__)

# Portfolios
IGNORED_PORTFOLIO_PREFIXES = ["wealthfront", "vanguard : employee_retirement"]


def parse_curl_command(curl_text: str) -> dict:
  """Extracts cookie, crumb, and userId from a cURL command."""
  try:
    # First, handle line continuations if the string was copy/pasted
    curl_text = curl_text.replace('\\\n', ' ')

    # Try shlex split, but if it fails due to mismatched quotes, just extract manually
    try:
      parts = shlex.split(curl_text)
    except ValueError:
      parts = curl_text.split()

    url = ""
    cookie = ""

    for i, part in enumerate(parts):
      if part.startswith('http'):
        url = part
      elif part in ('-H', '--header') and i + 1 < len(parts):
        header = parts[i + 1]
        if ':' in header:
          key, val = header.split(":", 1)
          key = key.strip()
          val = val.strip()
          if key.lower() == 'cookie':
            cookie = val
      elif part in ('-b', '--cookie') and i + 1 < len(parts):
        cookie = parts[i + 1]

    # If parsing failed, fallback to simple string matching
    if not url:
      # Just find the first thing starting with http
      url_match = re.search(r'(https?://[^\s\'"]+)', curl_text)
      if url_match:
        url = url_match.group(1)

    if not cookie:
      # Try regex for cookie
      cookie_match = re.search(
          r'(?:-H|-b|--header|--cookie)\s+[\'"]?(?:[Cc]ookie\s*:\s*)?([^\'"]+)[\'"]?',
          curl_text)
      if cookie_match:
        cookie = cookie_match.group(1)

    if not url:
      logger.error("Could not find a URL in the cURL command.")
      return {}

    # Extract ALL headers
    headers = {}
    for i, part in enumerate(parts):
      if part in ('-H', '--header') and i + 1 < len(parts):
        header = parts[i + 1]
        if ':' in header:
          key, val = header.split(":", 1)
          headers[key.strip()] = val.strip()

    # If cookie wasn't in -b, check headers
    if not cookie and 'cookie' in (k.lower() for k in headers):
      for k, v in headers.items():
        if k.lower() == 'cookie':
          cookie = v
          break

    # Add cookie explicitly if we got it from -b and it's not in headers
    if cookie and 'cookie' not in (k.lower() for k in headers):
      headers['cookie'] = cookie

    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    crumb = query_params.get('crumb', [None])[0]
    user_id = query_params.get('userId', [None])[0]

    return {
        "cookie": cookie,
        "crumb": crumb,
        "user_id": user_id,
        "headers": headers
    }
  except Exception as e:
    logger.error("Error parsing cURL: %s", e)
    return {}


def save_credentials_to_env(
    env_path: str,
    cookie: str,
    crumb: str,
    user_id: str,
    headers: Optional[dict] = None,
) -> None:
  """Saves Yahoo Finance credentials to .env file and updates os.environ."""
  active_line = None
  if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
      for line in f:
        if line.startswith("ACTIVE_TRADING_PORTFOLIOS="):
          active_line = line
          break

  try:
    with open(env_path, "w", encoding="utf-8") as f:
      f.write(f'YF_COOKIE="{cookie}"\n')
      f.write(f'YF_CRUMB="{crumb}"\n')
      f.write(f'YF_USER_ID="{user_id}"\n')
      if headers:
        f.write(f'YF_HEADERS=\'{json.dumps(headers)}\'\n')
      if active_line:
        f.write(active_line)

    logger.info("Successfully saved credentials to %s", env_path)

    os.environ["YF_COOKIE"] = cookie
    os.environ["YF_CRUMB"] = crumb
    os.environ["YF_USER_ID"] = user_id
    if headers:
      os.environ["YF_HEADERS"] = json.dumps(headers)
  except Exception as e:
    logger.error("Failed to write to .env file: %s", e)
    raise SystemExit(1) from e


def browser_capture_yahoo_creds(env_path: str) -> bool:
  """Automated browser capture of Yahoo Finance credentials using Playwright."""
  try:
    from playwright.sync_api import sync_playwright
  except ImportError:
    logger.warning("Playwright not installed.")
    return False

  profile_dir = Path.home() / ".yahoo_finance" / "browser_profile"
  profile_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

  logger.info("\n🔐 Spawning browser login flow for Yahoo Finance...")
  logger.info("Opening browser to: https://finance.yahoo.com/portfolios")
  logger.info("Using persistent profile: %s", profile_dir)
  login_email = os.environ.get("YF_LOGIN_EMAIL", "jakehgarrison@gmail.com")
  logger.info("\nInstructions:")
  logger.info("1. Log in to Yahoo Finance with account (%s) if signed out.",
              login_email)
  logger.info("2. View your Portfolios page.")
  logger.info(
      "3. Credentials will be automatically captured when portfolio data loads.\n"
  )

  captured: Dict[str, str] = {}
  captured_headers: Optional[dict] = None

  try:
    with sync_playwright() as p:
      context = p.chromium.launch_persistent_context(
          user_data_dir=str(profile_dir),
          headless=False,
          args=[
              "--disable-blink-features=AutomationControlled",
              "--password-store=basic",
          ],
          ignore_default_args=["--enable-automation"],
      )
      page = context.pages[0] if context.pages else context.new_page()

      def handle_request(request):
        nonlocal captured_headers
        url = request.url
        if ("query1.finance.yahoo.com" in url or "query2.finance.yahoo.com"
            in url) and ("portfolio" in url or "crumb" in url):
          parsed_url = urlparse(url)
          query_params = parse_qs(parsed_url.query)
          crumb = query_params.get("crumb", [None])[0]
          user_id = query_params.get("userId", [None])[0]
          req_headers = request.headers
          cookie = req_headers.get("cookie") or req_headers.get("Cookie")

          if cookie and crumb:
            captured["cookie"] = cookie
            captured["crumb"] = crumb
            if user_id:
              captured["user_id"] = user_id
            captured_headers = dict(req_headers)

      login_url = (
          "https://login.yahoo.com/?done=https%3A%2F%2Ffinance.yahoo.com%2Fportfolios&src=finance"
      )
      page.on("request", handle_request)
      logger.info("Opening browser directly to Yahoo Sign-In: %s", login_url)
      page.goto(login_url)
      try:
        page.bring_to_front()
      except Exception:
        pass

      start_wait = time.time()
      last_log = 0
      while time.time() - start_wait < 300:
        if captured.get("cookie") and captured.get("crumb"):
          logger.info(
              "✅ Automatically captured Yahoo Finance request from browser!")
          break
        elapsed = int(time.time() - start_wait)
        if elapsed - last_log >= 15:
          logger.info(
              "... waiting for Yahoo Finance login/portfolio data in browser (%ds)...",
              elapsed,
          )
          last_log = elapsed
        time.sleep(0.5)

      # Fallback check using context session cookies
      if not captured.get("cookie") or not captured.get("crumb"):
        try:
          cookies = context.cookies("https://finance.yahoo.com")
          if cookies:
            cookie_hdr = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
            resp = page.request.get(
                "https://query1.finance.yahoo.com/v1/test/getcrumb")
            if resp.status == 200:
              crumb_val = resp.text().strip()
              if crumb_val and "{" not in crumb_val:
                captured["cookie"] = cookie_hdr
                captured["crumb"] = crumb_val
                logger.info(
                    "✅ Captured Yahoo Finance crumb from API using browser session!"
                )
        except Exception as e:
          logger.debug("Page context crumb check: %s", e)

      context.close()

  except Exception as e:
    logger.warning("Playwright browser capture encountered an error: %s", e)
    return False

  if not captured.get("cookie") or not captured.get("crumb"):
    return False

  user_id = captured.get("user_id") or os.environ.get("YF_USER_ID", "")
  save_credentials_to_env(
      env_path,
      captured["cookie"],
      captured["crumb"],
      user_id,
      captured_headers,
  )
  return True


def update_yahoo_credentials(env_path: str) -> None:
  """Updates Yahoo Finance credentials using personal Google Chrome profile (zero verification required)."""
  logger.info("\n🚨 Yahoo Finance credentials expired or missing!")
  logger.info(
      "Opening personal Google Chrome browser (already logged in with %s)...",
      os.environ.get("YF_LOGIN_EMAIL", "jakehgarrison@gmail.com"),
  )
  prompt_for_curl_and_save_env(env_path)


def prompt_for_curl_and_save_env(env_path: str):
  """Prompts user to paste cURL, parses it, and saves to .env."""
  logger.info(
      "📋 MANUAL ACTION REQUIRED: Open Chrome -> Yahoo Portfolios -> Network Tab -> "
      "Right-click the 'portfolio' request -> Copy as cURL")

  chrome_url = "https://finance.yahoo.com/portfolios"
  logger.info("Opening Google Chrome with DevTools to: %s", chrome_url)
  try:
    # pylint: disable=consider-using-with
    subprocess.Popen([
        "open", "-a", "Google Chrome", "--args",
        "--auto-open-devtools-for-tabs", chrome_url
    ])
  except Exception as e:
    logger.warning("Failed to open Google Chrome automatically: %s", e)
    import webbrowser
    webbrowser.open(chrome_url)

  logger.info("\nChecking clipboard for 'Copy as cURL' command...")

  curl_text = ""
  if shutil.which('pbpaste'):
    logger.info("Waiting for cURL command in clipboard...")
    logger.info("Press Ctrl+C to abort at any time.")
    start_wait = time.time()
    last_heartbeat = 0
    try:
      while True:
        try:
          result = subprocess.run(['pbpaste'],
                                  capture_output=True,
                                  text=True,
                                  timeout=2,
                                  check=True)
          clipboard_content = result.stdout.strip()
          if (clipboard_content.startswith('curl') and
              'portfolio' in clipboard_content and
              ('query1.finance.yahoo.com' in clipboard_content or
               'query2.finance.yahoo.com' in clipboard_content)):
            logger.info("✅ Found cURL command in clipboard! Processing...")
            curl_text = clipboard_content
            break
        except Exception:
          pass

        elapsed = int(time.time() - start_wait)
        if elapsed - last_heartbeat >= 5:
          logger.info("... still waiting for cURL in clipboard (%ds)...",
                      elapsed)
          last_heartbeat = elapsed

        time.sleep(1.0)
    except KeyboardInterrupt:
      logger.info("\nAborted by user.")
      sys.exit(1)

  if not curl_text:
    logger.info("No pbpaste clipboard support, falling back to manual entry.")
    logger.info("Paste the 'Copy as cURL' text below.")
    logger.info("Press Ctrl+D (EOF) when finished (or Ctrl+C to abort):")
    try:
      curl_text = sys.stdin.read()
    except KeyboardInterrupt:
      logger.info("\nAborted by user.")
      sys.exit(1)

  if not curl_text.strip():
    logger.error("No input provided.")
    sys.exit(1)

  credentials = parse_curl_command(curl_text)
  if not credentials or not credentials['cookie'] or not credentials['crumb']:
    logger.error("Could not extract cookie or crumb from the provided cURL.")
    sys.exit(1)

  user_id = credentials.get('user_id')
  if not user_id:
    existing_user_id = os.environ.get('YF_USER_ID')
    if existing_user_id:
      logger.info("No User ID in cURL. Retaining existing YF_USER_ID.")
      user_id = existing_user_id
    else:
      logger.warning(
          "No User ID extracted. Please manually add YF_USER_ID to .env or you may face fetch errors."
      )
      user_id = ""

  save_credentials_to_env(
      env_path,
      credentials["cookie"],
      credentials["crumb"],
      user_id,
      credentials.get("headers"),
  )


def load_env_file(filepath: str):
  """Simple manual .env loader."""
  if not os.path.exists(filepath):
    return
  with open(filepath, 'r') as f:
    for line in f:
      line = line.strip()
      if not line or line.startswith('#'):
        continue
      if '=' in line:
        key, value = line.split('=', 1)
        val_clean = value.strip()
        # Remove surrounding single or double quotes
        if val_clean.startswith("'") and val_clean.endswith("'"):
          val_clean = val_clean[1:-1]
        elif val_clean.startswith('"') and val_clean.endswith('"'):
          val_clean = val_clean[1:-1]

        if key.strip() not in os.environ:
          os.environ[key.strip()] = val_clean


def verify_yahoo_auth(cookie: str,
                      crumb: str,
                      custom_headers: Optional[dict] = None) -> bool:
  """Quick pre-flight check to fail-fast if Yahoo auth cookie/crumb is stale."""
  logger.info("Running pre-flight Yahoo Finance Auth test...")
  url = "https://query1.finance.yahoo.com/v7/finance/desktop/portfolio"
  params = {"crumb": crumb}

  headers = {
      "User-Agent": UserAgent().random,
      "Accept": "*/*",
      "Cookie": cookie
  }
  if custom_headers:
    headers.update(custom_headers)

  # Ensure we have the minimum required
  if 'User-Agent' not in headers and 'user-agent' not in headers:
    headers["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) "
        "Gecko/20100101 Firefox/101.0")

  try:
    r = requests.get(url,
                     headers=headers,
                     params=params,
                     allow_redirects=False,
                     impersonate="chrome")
    if r.status_code in (401, 403):
      logger.error("Yahoo Auth Failed - HTTP %d. Credentials likely stale.",
                   r.status_code)
      logger.error("To update credentials:")
      logger.error("  1. Visit: https://finance.yahoo.com/portfolio/")
      logger.error("  2. Open DevTools (Network tab) and filter for:")
      logger.error("     'portfolio'")
      logger.error("  3. Right-click the 'portfolio' request -> Copy")
      logger.error("     -> Copy as cURL")
      logger.error("  4. Run 'make yahoo-creds' to update them.")
      return False
    if r.status_code == 200:
      logger.info("✅ Yahoo Auth Test Passed (HTTP 200)")
      return True
    logger.warning("Yahoo Auth Test returned unexpected Status Code: %d",
                   r.status_code)
    return False
  except Exception as e:
    logger.error("Auth Test failed due to network error: %s", e)
    return False


def fetch_yahoo_portfolios(cookie: str,
                           crumb: str,
                           user_id: str,
                           custom_headers: Optional[dict] = None) -> dict:
  """Fetches portfolios from Yahoo Finance using user credentials.

  Args:
      cookie (str): The Yahoo Finance session cookie.
      crumb (str): The Yahoo Finance crumb.
      user_id (str): The Yahoo Finance user ID.
      custom_headers (dict): Optional dict of headers parsed from cURL.

  Returns:
      dict: The JSON response containing portfolio data.
  """
  if user_id:
    url = (f"https://query1.finance.yahoo.com/v7/finance/desktop/portfolio"
           f"?formatted=true&crumb={crumb}&lang=en-US&region=US"
           f"&userId={user_id}&corsDomain=finance.yahoo.com")
  else:
    # Use the exact URL format that doesn't strictly need a userId
    url = (
        f"https://query1.finance.yahoo.com/v7/finance/desktop/portfolio"
        f"?formatted=true&includeBetaVersion=1"
        f"&keyMetricsModules=portfolioReturns%2CdividendPayouts%2CassetAllocation%2CsectorAllocation"
        f"&lang=en-US&region=US&crumb={crumb}")

  headers = custom_headers if custom_headers else {}

  # Ensure we have the minimum required
  if 'Cookie' not in headers and 'cookie' not in headers:
    headers['Cookie'] = cookie
  if 'User-Agent' not in headers and 'user-agent' not in headers:
    headers["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) "
        "Gecko/20100101 Firefox/101.0")

  # Ensure we ask for JSON explicitly
  headers["Accept"] = "application/json"

  logger.info("Fetching portfolios for user %s", user_id)

  try:
    response = requests.get(url, headers=headers, impersonate="chrome")
    response.raise_for_status()
  except Exception as e:
    logger.error("Failed to fetch portfolios from Yahoo Finance: %s", e)
    raise

  return response.json()


def main():
  """Main entry point for the script."""
  portfolios_base_dir = os.environ.get(
      "PORTFOLIOS_DATA_DIR") or os.path.dirname(__file__)
  parser = argparse.ArgumentParser(description="Fetch Yahoo Finance Portfolios")
  parser.add_argument(
      "--dump",
      action="store_true",
      help="Dump the raw JSON response to a file for inspection.",
  )
  parser.add_argument(
      "--update-creds",
      action="store_true",
      help=
      "Force update of Yahoo Finance credentials (prompts for new cURL string).",
  )
  parser.add_argument(
      "--local-json",
      type=str,
      help="Path to a manually saved portfolio.json file (skips fetching).",
  )
  parser.add_argument(
      "--force",
      action="store_true",
      help="Force a fresh fetch from Yahoo Finance, bypassing the 1-hour cache."
  )
  parser.add_argument("--check-auth",
                      action="store_true",
                      help="Verify Yahoo Finance credentials and exit.")
  args = parser.parse_args()

  logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

  env_path = os.path.join(os.path.dirname(__file__), ".env")
  load_env_file(env_path)

  cookie = os.environ.get("YF_COOKIE")
  crumb = os.environ.get("YF_CRUMB")
  user_id = os.environ.get("YF_USER_ID")
  headers_str = os.environ.get("YF_HEADERS")

  custom_headers = None
  if headers_str:
    try:
      custom_headers = json.loads(headers_str)
    except Exception:
      pass

  if args.check_auth:
    has_creds = cookie and crumb
    authed = False
    if has_creds:
      authed = verify_yahoo_auth(cookie, crumb, custom_headers=custom_headers)

    if authed:
      logger.info("✅ Yahoo Finance Auth Valid")
      sys.exit(0)

    if not has_creds:
      logger.error("Yahoo Finance credentials missing in .env")
      logger.error("To configure credentials:")
    else:
      logger.error("❌ Yahoo Finance Auth Expired or Invalid")
      logger.error("To update credentials:")

    logger.error("  1. Visit: https://finance.yahoo.com/portfolio/")
    logger.error("  2. Open DevTools (Network tab) and filter for:")
    logger.error("     'portfolio'")
    logger.error("  3. Right-click the 'portfolio' request -> Copy")
    logger.error("     -> Copy as cURL")
    logger.error("  4. Run 'make yahoo-creds' to update them.")

    if sys.stdin.isatty():
      logger.info("\n🔄 Interactive session detected. Starting update flow...")
      update_yahoo_credentials(env_path)
      cookie = os.environ.get("YF_COOKIE")
      crumb = os.environ.get("YF_CRUMB")
      headers_str = os.environ.get("YF_HEADERS")
      custom_headers = None
      if headers_str:
        try:
          custom_headers = json.loads(headers_str)
        except Exception:
          pass
      if (cookie and crumb and
          verify_yahoo_auth(cookie, crumb, custom_headers=custom_headers)):
        logger.info("✅ Yahoo Finance Auth Valid after update")
        sys.exit(0)
      else:
        logger.error("❌ Yahoo Finance Auth still invalid after update.")
        sys.exit(1)
    else:
      sys.exit(1)
  json_cache_path = os.path.join(portfolios_base_dir, "portfolio.json")

  # Auto-inject the cached file if it's less than 1 hour old and we aren't forcing an update
  if not args.local_json and not args.force and not args.dump:
    if os.path.exists(json_cache_path):
      age_seconds = time.time() - os.path.getmtime(json_cache_path)
      max_age = config.CACHE_YAHOO_PORTFOLIO_HOURS * 3600
      if age_seconds < max_age:
        logger.info(
            f"portfolio.json is only {int(age_seconds/60)} minutes old (Cache max: {config.CACHE_YAHOO_PORTFOLIO_HOURS}h). Using cached version. Use --force to override."
        )
        args.local_json = json_cache_path

  try:
    if args.local_json:
      logger.info(f"Loading local JSON from {args.local_json}")
      with open(args.local_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    else:
      needs_update = args.update_creds

      if not cookie or not crumb:
        logger.warning("Missing Cookie or Crumb in .env.")
        needs_update = True
      elif not verify_yahoo_auth(cookie, crumb, custom_headers=custom_headers):
        logger.warning(
            "Yahoo Auth check failed with existing credentials in .env.")
        needs_update = True

      if needs_update:
        logger.info("Prompting for new credentials...")
        update_yahoo_credentials(env_path)
        # Reload env vars
        cookie = os.environ.get("YF_COOKIE")
        crumb = os.environ.get("YF_CRUMB")
        user_id = os.environ.get("YF_USER_ID", "")
        headers_str = os.environ.get("YF_HEADERS")
        if headers_str:
          try:
            custom_headers = json.loads(headers_str)
          except:
            pass

        if not cookie or not crumb:
          logger.error("Still missing Cookie and Crumb after capture. Exiting.")
          sys.exit(1)

        # Pre-flight check after update
        if not verify_yahoo_auth(cookie, crumb, custom_headers=custom_headers):
          logger.error(
              "Yahoo Auth check failed with newly captured credentials! IP may be strictly banned (429)."
          )
          sys.exit(1)

      # Fail gracefully if user_id missing and required by API structure
      if not user_id:
        logger.error(
            "YF_USER_ID is completely missing. Please add it to reports/portfolios/.env"
        )
        sys.exit(1)

      # No fallback: if live fetch fails, crash the script so pipeline breaks explicitly
      data = fetch_yahoo_portfolios(cookie, crumb, user_id, custom_headers)

      # Diff against existing local portfolio.json (if present)
      json_path = os.path.join(os.path.dirname(__file__), "portfolio.json")
      if os.path.exists(json_path):
        try:
          with open(json_path, 'r', encoding="utf-8") as f:
            old_data = json.load(f)

          old_portfolios = old_data.get("finance",
                                        {}).get("result",
                                                [{}])[0].get("portfolios", [])
          new_portfolios = data.get("finance",
                                    {}).get("result",
                                            [{}])[0].get("portfolios", [])

          old_map = {p.get("name", "Unknown"): p for p in old_portfolios}

          logger.info("========== Live vs Local Cache Value Diff ==========")
          for p in new_portfolios:
            name = p.get("name", "Unknown")
            new_val = p.get("currentMarketValue", 0)
            if name in old_map:
              old_val = old_map[name].get("currentMarketValue", 0)
              diff = new_val - old_val
              if abs(diff) > 0.01:
                sign = "+" if diff > 0 else ""
                logger.info(
                    f"DIFF [{name}]: Value changed by {sign}${diff:,.2f} (from ${old_val:,.2f} to ${new_val:,.2f})"
                )
            else:
              logger.info(
                  f"DIFF: New portfolio added: {name} (${new_val:,.2f})")
          logger.info("====================================================")
        except Exception as e:
          logger.warning(
              f"Could not compute structural diff against existing portfolio.json: {e}"
          )
    if not args.local_json:
      with open(json_cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
      logger.info(f"Updated local portfolio cache at {json_cache_path}")

    if args.dump:
      logger.info(
          "Dump mode active: Updated cache and exiting early without processing TSVs."
      )
      sys.exit(0)
    else:
      try:

        portfolios = data.get("finance", {}).get("result",
                                                 [{}])[0].get("portfolios", [])
        logger.info("Found %d portfolios.", len(portfolios))

        meta_report_rows = []
        combined_positions = {}
        combined_active_positions = {}

        # Parse Active config from env to build combined active matrix
        env_active = os.environ.get("ACTIVE_TRADING_PORTFOLIOS", "")
        # Normalize list entries to match sanitized safe_name (single underscore, lowercase) using regex
        active_list = [
            re.sub(r'[^a-zA-Z0-9]+', '_', p).strip('_').lower()
            for p in env_active.split(",")
            if p.strip()
        ] if env_active else []

        # Get ignored portfolio prefixes
        ignored_prefixes = [p.lower() for p in IGNORED_PORTFOLIO_PREFIXES]

        # Ensure tsvs dir exists
        out_dir = os.path.join(portfolios_base_dir, "tsvs")
        os.makedirs(out_dir, exist_ok=True)

        for p in portfolios:
          name = p.get("pfName", p.get("name", "Unknown"))
          pf_id = p.get("pfId", p.get("id", "Unknown"))
          positions = p.get("positions", [])
          current_market_value = p.get("currentMarketValue", 0)

          if current_market_value == 0:
            logger.warning(
                "Skipping Portfolio '%s' (ID: %s) because its Current Market Value is 0.",
                name, pf_id)
            continue

          logger.info("Portfolio: %s (ID: %s) - %d positions", name, pf_id,
                      len(positions))

          # Check if this portfolio should be ignored for combining
          should_ignore = False
          for prefix in ignored_prefixes:
            if name.lower().startswith(prefix):
              should_ignore = True
              break

          if should_ignore:
            logger.info("Ignoring portfolio '%s' in combined aggregates.", name)

          if positions:
            # Flatten the position data into a DataFrame
            rows = []
            for pos in positions:
              sym = pos.get("symbol")
              lots = pos.get("lots", [])

              # Use the aggregate position total
              qty = pos.get("quantity", 0)
              cost_basis = pos.get("purchasePrice", 0)
              pos_current_value = pos.get("currentMarketValue", 0)
              current_price = round(pos_current_value /
                                    qty, 2) if qty > 0 else 0

              rows.append({
                  "Ticker": sym,
                  "Price": current_price,
                  "Quantity": qty,
                  "Current_Value": pos_current_value,
                  "Cost_Basis": pos_current_value - pos.get("totalGain", 0),
                  "Unrealized_PnL_Net": pos.get("totalGain", 0),
                  "Unrealized_PnL_Pct": pos.get("totalPercentGain", 0),
                  "Day_Change_Net": pos.get("dailyGain", 0),
                  "Day_Change_Pct": pos.get("dailyPercentGain", 0)
              })

              # Add to combined dictionaries
              if not should_ignore:
                if sym not in combined_positions:
                  combined_positions[sym] = {
                      "Quantity": 0.0,
                      "Current_Value": 0.0,
                      "Unrealized_PnL_Net": 0.0,
                      "Day_Change_Net": 0.0
                  }
                combined_positions[sym]["Quantity"] += qty
                combined_positions[sym]["Current_Value"] += pos_current_value
                combined_positions[sym]["Unrealized_PnL_Net"] += pos.get(
                    "totalGain", 0)
                combined_positions[sym]["Day_Change_Net"] += pos.get(
                    "dailyGain", 0)

                # Safe name generation for active check (robust regex normalization)
                safe_name = re.sub(r'[^a-zA-Z0-9]+', '_',
                                   name).strip('_').lower()

                if safe_name in active_list:
                  if sym not in combined_active_positions:
                    combined_active_positions[sym] = {
                        "Quantity": 0.0,
                        "Current_Value": 0.0,
                        "Unrealized_PnL_Net": 0.0,
                        "Day_Change_Net": 0.0
                    }
                  combined_active_positions[sym]["Quantity"] += qty
                  combined_active_positions[sym][
                      "Current_Value"] += pos_current_value
                  combined_active_positions[sym][
                      "Unrealized_PnL_Net"] += pos.get("totalGain", 0)
                  combined_active_positions[sym]["Day_Change_Net"] += pos.get(
                      "dailyGain", 0)

            # Check if there's a cash position
            cash = p.get("cashPosition", 0)
            if cash > 0:
              rows.append({
                  "Ticker": "CASH",
                  "Price": 1.0,
                  "Quantity": round(cash, 2),
                  "Current_Value": round(cash, 2),
                  "Cost_Basis": round(cash, 2),
                  "Unrealized_PnL_Net": 0.0,
                  "Unrealized_PnL_Pct": 0.0,
                  "Day_Change_Net": 0.0,
                  "Day_Change_Pct": 0.0
              })

              if not should_ignore:
                if "CASH" not in combined_positions:
                  combined_positions["CASH"] = {
                      "Quantity": 0.0,
                      "Current_Value": 0.0,
                      "Unrealized_PnL_Net": 0.0,
                      "Day_Change_Net": 0.0
                  }
                combined_positions["CASH"]["Quantity"] += cash
                combined_positions["CASH"]["Current_Value"] += cash

                safe_name = "".join(
                    c for c in name if c.isalnum() or c in (" ", "_")).strip()
                safe_name = safe_name.replace(" ", "_").lower().rstrip("_")

                if safe_name in active_list:
                  if "CASH" not in combined_active_positions:
                    combined_active_positions["CASH"] = {
                        "Quantity": 0.0,
                        "Current_Value": 0.0,
                        "Unrealized_PnL_Net": 0.0,
                        "Day_Change_Net": 0.0
                    }
                  combined_active_positions["CASH"]["Quantity"] += cash
                  combined_active_positions["CASH"]["Current_Value"] += cash

            df = pd.DataFrame(rows)
            if not df.empty:
              df = df.round(3)

            # Record metadata for this portfolio
            meta_report_rows.append({
                "Portfolio_Name": name,
                "Total_Value": current_market_value,
                "Position_Count": len(positions),
                "Total_Gain_Net": p.get("totalGain", 0),
                "Total_Gain_Pct": p.get("totalPercentGain", 0),
                "Daily_Gain_Net": p.get("dailyGain", 0),
                "Daily_Gain_Pct": p.get("dailyPercentGain", 0)
            })

            safe_name = "".join(
                c for c in name if c.isalnum() or c in (" ", "_")).strip()
            safe_name = safe_name.replace(" ", "_").lower()

            # Remove trailing underscores if any
            safe_name = safe_name.rstrip("_")

            output_file = os.path.join(out_dir, f"{safe_name}.tsv")
            df.to_csv(output_file, sep="\t", index=False)
            logger.info("Saved %s positions to %s", len(df), output_file)

        # Write out Meta Summary report
        if meta_report_rows:
          meta_df = pd.DataFrame(meta_report_rows)
          meta_df = meta_df.sort_values(by="Total_Value",
                                        ascending=False).round(2)
          meta_path = os.path.join(portfolios_base_dir, "portfolio_summary.tsv")
          meta_df.to_csv(meta_path, sep="\t", index=False)
          logger.info("Saved Meta Report to %s", meta_path)

        # Helper for saving combined TSVs locally
        def _save_combined(pos_dict, filename):
          if not pos_dict:
            return
          rows = []
          for sym, data in pos_dict.items():
            qty = data["Quantity"]
            val = data["Current_Value"]
            unr_net = data["Unrealized_PnL_Net"]
            day_net = data["Day_Change_Net"]

            avg_price = (val / qty) if qty > 0 else 0
            cost_basis = val - unr_net
            unr_pct = (unr_net / cost_basis * 100) if cost_basis > 0 else 0

            prev_val = val - day_net
            day_pct = (day_net / prev_val * 100) if prev_val > 0 else 0

            rows.append({
                "Ticker": sym,
                "Price": round(avg_price, 2),
                "Quantity": qty,
                "Current_Value": val,
                "Cost_Basis": cost_basis,
                "Unrealized_PnL_Net": unr_net,
                "Unrealized_PnL_Pct": round(unr_pct, 2),
                "Day_Change_Net": day_net,
                "Day_Change_Pct": round(day_pct, 2)
            })

          df = pd.DataFrame(rows)
          df = df.sort_values(by="Current_Value", ascending=False).round(3)
          path = os.path.join(out_dir, filename)
          df.to_csv(path, sep="\t", index=False)
          logger.info("Saved Combined Portfolio (%d unique tickers) to %s",
                      len(df), path)

        _save_combined(combined_positions, "_combined_portfolio.tsv")
        _save_combined(combined_active_positions,
                       "_combined_active_portfolio.tsv")

      except (IndexError, KeyError) as e:
        logger.error(
            "Failed to parse portfolios from response. Run with --dump to inspect."
        )
  except Exception as e:
    logger.error("Error during execution: %s", e)
    sys.exit(1)


if __name__ == "__main__":
  main()
