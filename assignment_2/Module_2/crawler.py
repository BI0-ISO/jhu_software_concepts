
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

    # I can make a for loop to go through each applicant entry 

    for entry_num in range(start_entry,end_entry):

        #First I access an applicant's entry 

        url = f"https://www.thegradcafe.com/result/{entry_num}"

        # Next I make a HTTP request to access this information using this url provided
        try: 
            response = http.request("GET", url)

            # Now I do a check to make sure the site works properly, and if so, save the information 

            # Something I found when trying to break this code, is that when you input an entry that is not valid 
            # the website still works but only a notifcation entry is provided and spits out 31/12/1969

            if response.status == 200:

                print(response.status)

                raw_data.append({
                        "url": url,
                        "html": response.data.decode("utf-8")
                        })
                

        # If there is something that is wrong with this site, just keep on to the next one        
        except: 
            continue 

    return raw_data
    


test = scrape_data(9000000,9000001)



