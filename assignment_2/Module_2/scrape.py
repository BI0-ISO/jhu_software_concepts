
# # Dealing with HTTP requests 
# import urllib3

# from bs4 import BeautifulSoup

# import re

# # Sends requests to GrabCafe - Acts as a browser engine 
# http = urllib3.PoolManager()


# # My goal for this script is to collect a bunch of information from applicant entries 
# # Thus, I want to scrape from a starting entry to an end entry, ideally => 30,000 entries 

# # I want a function that will do this: 

# def scrape_data(start_entry, end_entry):

#     # Now I need a variable that will store this raw information 

#     raw_data = []; 

#     # After exploring GrabCafe, I found that the URL that holds this applicant information usally follows this 
#     # format https://www.thegradcafe.com/result/{entry_number}, is this always the case, no, but we could do a 
#     # check that sees if 1) this page actually loads, and 2) if the information loads 
#     # I found that when I vary the {entry_#} manually, sometimes the information doesn't load 

#     # I can make a for loop to go through each applicant entry 

#     for entry_num in range(start_entry,end_entry):

#         #First I access an applicant's entry 

#         url = f"https://www.thegradcafe.com/result/{entry_num}"

#         # Next I make a HTTP request to access this information using this url provided
#         try: 
#             response = http.request("GET", url)

#             # Now I do a check to make sure the site works properly, and if so, save the information 

#             # Something I found when trying to break this code, is that when you input an entry that is not valid 
#             # the website still works but only a notifcation entry is provided and spits out 31/12/1969
        

#             soup = BeautifulSoup(response.data.decode("utf-8"), "html.parser")

#             # Converting the html data into a nicer for to find the information that I want 

#             text = soup.get_text(separator="\n")

#             # Using Regex to find the notification date 

#             error_check = re.search(r"on\s+(\d{2}/\d{2}/\d{4})", text)
            

#             # If a date is found then, boom we have a new variable, if not, no worries, it is None 

#             if error_check:
#                 invalid_entry_check = error_check.group(1).strip()
#             else:
#                 invalid_entry_check = None


#             # Here I do 2 checks, 1) is the website good, and 2) does the date match the error date I am looking for 
#             if response.status == 200:
#                 if invalid_entry_check == "31/12/1969":
#                     print(f"Invalid Entry Detected for {url}")
                
#                 # If I get a 200 and the date does not match, I want to save the data
#                 else:
#                     raw_data.append({
#                         "url": url,
#                         "html": response.data.decode("utf-8")
#                     })

#         # If the response is not a 200 for some reason, I want to know 1) why my code didn't work and 2) what error did I get 
#         except Exception as e:
#             print(f"HTTP error for {url}: {e}")
#             continue

#     return raw_data
    

# # This is a check to make sure the code catches entries that aren't actually entries 

# #test_Invalid = scrape_data(9000000,9000001)


# scrape.py
import urllib3
import time
from bs4 import BeautifulSoup
import re

http = urllib3.PoolManager(
    headers={"User-Agent": "Mozilla/5.0"}
)


def scrape_data(start_entry: int, end_entry: int):
    """
    Scrapes raw applicant HTML pages from GradCafe.
    Invalid or missing entries are skipped.
    Returns a list of dicts containing URL + raw HTML.
    """

    raw_pages = []

    for entry_id in range(start_entry, end_entry):
        url = f"https://www.thegradcafe.com/result/{entry_id}"

        try:
            response = http.request("GET", url, timeout=urllib3.Timeout(5.0))

            if response.status != 200:
                continue

            html = response.data.decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text("\n")

            # GradCafe invalid pages often contain this epoch date
            invalid_date = re.search(r"\b31/12/1969\b", text)
            if invalid_date:
                continue

            raw_pages.append({
                "url": url,
                "html": html
            })

            # Polite scraping
            #time.sleep(0.3)

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            continue
        print(entry_id)

    return raw_pages



