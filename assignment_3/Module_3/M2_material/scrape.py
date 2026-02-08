# scrape.py
import urllib3
from bs4 import BeautifulSoup
import re
import time
from typing import Optional

http = urllib3.PoolManager(
    headers={"User-Agent": "Mozilla/5.0"}
)

LAST_STOP_REASON = None
LAST_ATTEMPTED_ID = None


def get_last_stop_reason():
    return LAST_STOP_REASON


def get_last_attempted_id():
    return LAST_ATTEMPTED_ID


def _fetch_survey_added_map() -> dict[int, str]:
    try:
        url = "https://www.thegradcafe.com/survey/"
        response = http.request("GET", url, timeout=urllib3.Timeout(5.0))
        if response.status != 200:
            return {}
        html = response.data.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")

        table = None
        added_idx = None
        for t in soup.find_all("table"):
            headers = [th.get_text(" ", strip=True) for th in t.find_all("th")]
            for i, h in enumerate(headers):
                if h.lower() == "added on":
                    table = t
                    added_idx = i
                    break
            if table is not None:
                break
        if table is None or added_idx is None:
            return {}

        mapping: dict[int, str] = {}
        for row in table.find_all("tr"):
            link = row.find("a", href=re.compile(r"/result/\d+"))
            if not link:
                continue
            match = re.search(r"/result/(\d+)", link.get("href", ""))
            if not match:
                continue
            entry_id = int(match.group(1))
            cells = row.find_all(["td", "th"])
            if added_idx < len(cells):
                added_on = cells[added_idx].get_text(" ", strip=True)
                if added_on:
                    mapping[entry_id] = added_on
        return mapping
    except Exception:
        return {}


def get_latest_survey_id() -> Optional[int]:
    """
    Fetch the GradCafe survey page and return the highest result ID found.
    Returns None if the page can't be fetched or parsed.
    """
    try:
        url = "https://www.thegradcafe.com/survey/"
        response = http.request("GET", url, timeout=urllib3.Timeout(5.0))
        if response.status != 200:
            return None
        html = response.data.decode("utf-8", errors="ignore")
        ids = [int(m.group(1)) for m in re.finditer(r"/result/(\d+)", html)]
        return max(ids) if ids else None
    except Exception:
        return None


def scrape_data(start_entry: int, end_entry: Optional[int] = None, stop_on_placeholder_streak: bool = True, placeholder_limit: int = 10):
    """
    Generator function to scrape GradCafe entries one by one.

    Yields:
        dict: {"url": <url>, "html": <html content>}
    """
    global LAST_STOP_REASON, LAST_ATTEMPTED_ID
    LAST_STOP_REASON = None
    LAST_ATTEMPTED_ID = None
    placeholder_streak = 0
    survey_added_map = _fetch_survey_added_map()
    entry_id = start_entry
    while True:
        if end_entry is not None and entry_id >= end_entry:
            break
        LAST_ATTEMPTED_ID = entry_id
        url = f"https://www.thegradcafe.com/result/{entry_id}"

        try:
            response = http.request("GET", url, timeout=urllib3.Timeout(5.0))
            if response.status != 200:
                continue

            html = response.data.decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text("\n")

            # Placeholder pages: skip, optionally stop after N in a row
            if re.search(r"\bon\s*31/12/1969\b", text, re.IGNORECASE) or re.search(r"\b31/12/1969\b", text):
                placeholder_streak += 1
                if stop_on_placeholder_streak and placeholder_streak >= placeholder_limit:
                    LAST_STOP_REASON = "placeholder_streak"
                    print(f"Reached {placeholder_limit} placeholder entries in a row (31/12/1969). Stopping scrape.")
                    break
                continue
            else:
                placeholder_streak = 0

            added_on = survey_added_map.get(entry_id)

            # Yield valid page immediately
            yield {"url": url, "html": html, "date_added": added_on}

            # Live terminal update for attempted entries (optional)
            print(f"Scraped entry: {entry_id}")

            # Optional: polite delay
            # time.sleep(0.2)

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            continue
        finally:
            entry_id += 1
