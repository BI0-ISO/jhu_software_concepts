
# Dealing with HTTP requests 
import urllib3

# Sends requests to GrabCafe - Acts as a browser engine 
http = urllib3.PoolManager()


# My goal for this script is to collect a bunch of information from applicant entries 
# Thus, I want to scrape from a starting entry to an end entry, ideally => 30,000 entries 

# I want a function that will do this: 

def scrape_data(start_entry, end_entry):

    # Now I need a variable that will store this raw information 

    raw_data = []; 

    # After exploring GrabCafe, I found that the URL that holds this applicant information usally follows this 
    # format https://www.thegradcafe.com/result/{entry_number}, is this always the case, no, but we could do a 
    # check that sees if 1) this page actually loads, and 2) if the information loads 
    # I found that when I vary the {entry_#} manually, sometimes the information doesn't load 

