import os
import re
import sys
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuration ---
URL = "https://www.alphavantage.co/support/"
TOTAL_KEYS = 10
START_N = 1  # Resuming from where it got blocked
BASE_EMAIL = "stonkytonk"
EMAIL_DOMAIN = "@gmail.com"
COMPANY = "stonk"
OUTPUT_FILE = "alpha_vantage.tsv"


def get_existing_keys():
  """Helper to read keys currently in the TSV file."""
  if not os.path.exists(OUTPUT_FILE):
    return []

  keys = []
  with open(OUTPUT_FILE, "r") as f:
    for line in f:
      line = line.strip()
      if not line:
        continue

      parts = line.split("\t")
      if len(parts) >= 2:
        keys.append(parts[1].strip())
  return keys


def main():
  options = webdriver.ChromeOptions()
  # options.add_argument("--headless")
  options.add_argument("--window-size=1200,800")

  driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                            options=options)

  print(f"--- Starting Auto Key Gen (Starting at N={START_N}) ---")

  try:
    for i in range(START_N, START_N + TOTAL_KEYS):
      email = f"{BASE_EMAIL}{i}{EMAIL_DOMAIN}"
      print(f"\n[{i}] Processing: {email}")

      try:
        driver.get(URL)

        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.ID, "post-form")))

        # Fill Form
        Select(driver.find_element(By.NAME,
                                   "occupation")).select_by_value("Investor")

        org = driver.find_element(By.NAME, "organization")
        org.clear()
        org.send_keys(COMPANY)

        em = driver.find_element(By.NAME, "email")
        em.clear()
        em.send_keys(email)

        # Click Submit
        btn = driver.find_element(By.ID, "submit-btn")
        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
        time.sleep(0.5)
        btn.click()

        print("    -> Form submitted. Polling for API key...")

        # --- MANUAL POLLING & DEBUGGING ---
        key_found = False
        api_key = None
        rate_limit_hit = False

        # Wait up to 15 seconds
        for attempt in range(15):
          page_source = driver.page_source

          # 1. CHECK FOR RATE LIMIT ("redundant origins")
          if "redundant origins" in page_source.lower():
            rate_limit_hit = True
            break

          # 2. CHECK FOR API KEY
          match = re.search(r"key(?: is)?:\s*([A-Z0-9]{10,30})", page_source)
          if match:
            key_found = True
            api_key = match.group(1)
            break

          # Optional: Print debug info to see it polling
          try:
            talk_text = driver.find_element(By.ID, "talk").text.strip()
            if talk_text:
              print(".", end="", flush=True)
          except:
            pass

          time.sleep(1)

        print()  # Print new line after the dots

        # --- Handle Results ---
        if rate_limit_hit:
          print("    -> [WARNING] IP Rate Limit Hit! ('redundant origins')")
          print(
              "    -> Alpha Vantage has temporarily blocked this IP from generating more keys."
          )
          print("    -> Stopping the script to prevent a permanent ban.")
          break  # Break out of the main 'for' loop entirely

        elif key_found:
          print(f"    -> SUCCESS! Found Key: {api_key}")
          with open(OUTPUT_FILE, "a") as f:
            f.write(f"{email}\t{api_key}\n")
        else:
          print(
              "    -> FAILURE: Timed out waiting for key. Dumping page text snippet:"
          )
          body_text = driver.find_element(By.TAG_NAME, "body").text
          print("-------- BODY TEXT SNIPPET --------")
          if "key" in body_text.lower():
            lines = body_text.split('\n')
            for line in lines:
              if "key" in line.lower():
                print(f"       MATCHING LINE: {line}")
          else:
            print(body_text[:1000])
          print("-----------------------------------")

      except Exception as e:
        print(f"    -> ERROR on {email}: {e}")

      time.sleep(2)

  except KeyboardInterrupt:
    print("\nStopped by user.")
  finally:
    driver.quit()

    # --- Final Output ---
    print("\n" + "=" * 50)
    print(f"ALL KEYS EXTRACTED SO FAR (Comma-Separated):")
    print("=" * 50)

    keys = get_existing_keys()
    if keys:
      csv_string = ",".join(keys)
      print(csv_string)
      print(f"\nTotal keys in file: {len(keys)}")
    else:
      print("No keys found in file.")
    print("=" * 50)


if __name__ == "__main__":
  main()
