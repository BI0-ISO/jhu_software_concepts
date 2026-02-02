# scrape.py
import urllib3       # For sending HTTP requests to web pages
import time          # Optional: can be used for polite delays between requests
from bs4 import BeautifulSoup  # For parsing HTML and extracting text
import re            # For pattern matching using regular expressions

# Initialize a urllib3 PoolManager with a custom User-Agent header
# This mimics a browser so that GradCafe will allow our requests
http = urllib3.PoolManager(
    headers={"User-Agent": "Mozilla/5.0"}
)


def scrape_data(start_entry: int, end_entry: int):
    """
    Scrapes raw applicant HTML pages from GradCafe.

    Parameters:
        start_entry (int): Starting GradCafe entry number to scrape.
        end_entry (int): Ending GradCafe entry number to scrape (exclusive).

    Returns:
        List[Dict]: A list of dictionaries containing:
            - "url": the URL of the applicant entry
            - "html": the raw HTML content of the page
    Notes:
        - Skips entries that are invalid or missing.
        - Does not parse or clean the HTML here; raw HTML is returned.
    """

    # List to store all valid applicant pages
    raw_pages = []

    # Iterate over the requested range of GradCafe entry numbers
    for entry_id in range(start_entry, end_entry):

        # Construct the URL for the current applicant entry
        url = f"https://www.thegradcafe.com/result/{entry_id}"

        try:
            # Send a GET request to the URL with a 5-second timeout
            response = http.request("GET", url, timeout=urllib3.Timeout(5.0))

            # Skip this entry if the HTTP response status is not 200 (OK)
            if response.status != 200:
                continue

            # Decode the response data from bytes to string, ignoring any decoding errors
            html = response.data.decode("utf-8", errors="ignore")

            # Parse the HTML with BeautifulSoup for easier text extraction
            soup = BeautifulSoup(html, "html.parser")

            # Extract all text content from the page, separating lines with '\n'
            text = soup.get_text("\n")

            # GradCafe invalid or placeholder pages often contain the date "31/12/1969"
            # This regex search checks for that invalid placeholder date
            invalid_date = re.search(r"\b31/12/1969\b", text)
            if invalid_date:
                # Skip the page if it contains the invalid date
                continue

            # Append valid pages to the raw_pages list as a dictionary
            raw_pages.append({
                "url": url,   # Store the URL for reference
                "html": html  # Store the raw HTML for later cleaning
            })

            # Optional: polite scraping to avoid overloading the server
            # Uncomment the next line to add a short delay between requests
            # time.sleep(0.3)

        except Exception as e:
            # Catch any exceptions (e.g., connection errors, timeouts) and log them
            # Then continue to the next entry without stopping the pipeline
            print(f"Error scraping {url}: {e}")
            continue

        # Print the current entry number to track progress in the console
        print(entry_id)

    # Return the list of valid raw applicant pages
    return raw_pages
