# scrape.py
import urllib3
from bs4 import BeautifulSoup
import re
import time

http = urllib3.PoolManager(
    headers={"User-Agent": "Mozilla/5.0"}
)

def scrape_data(start_entry: int, end_entry: int):
    """
    Generator function to scrape GradCafe entries one by one.

    Yields:
        dict: {"url": <url>, "html": <html content>}
    """
    for entry_id in range(start_entry, end_entry):
        url = f"https://www.thegradcafe.com/result/{entry_id}"

        try:
            response = http.request("GET", url, timeout=urllib3.Timeout(5.0))
            if response.status != 200:
                continue

            html = response.data.decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text("\n")

            # Skip invalid/placeholder pages
            if re.search(r"\b31/12/1969\b", text):
                continue

            # Yield valid page immediately
            yield {"url": url, "html": html}

            # Live terminal update for attempted entries (optional)
            print(f"Scraped entry: {entry_id}")

            # Optional: polite delay
            # time.sleep(0.2)

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            continue
