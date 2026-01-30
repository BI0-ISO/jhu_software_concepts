import urllib3
from bs4 import BeautifulSoup
import json
import re


http = urllib3.PoolManager()



all_data = {}

for entry_page in range(2):


    url = "https://www.thegradcafe.com/result/90000"+str(entry_page)

    # Check to make sure the url is looping correctly 
    print(url) 

    response = http.request("GET", url)


    html = response.data.decode("utf-8")



    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text(separator="\n")

    #print(text)

    #print(soup.title.text)  

    patterns = {
        "Institution": r"Institution\s*(.*)",
        "Degree Type": r"Degree Type\s*(.*)",
        "Decision": r"Decision\s*(.*)",
        "Undergrad GPA": r"Undergrad GPA\s*(.*)",
        "Program": r"Program\s*(.*)",
        "Notes": r"Notes\s*(.*)",
        # Still working on this to only grab the date, right now it grabs the on in front as well 
        "Notification": r"Notification\s*(.*)",
        "GRE General": r"GRE General:\s*(\d+)",
        "GRE Verbal": r"GRE Verbal:\s*(\d+)",
        "Analytical Writing": r"Analytical Writing:\s*(\d+\.?\d*)",
        "Applicant Link": r"Applicant Entry:\s*(https?://[^\s]+)"
    }


    applicant_data = {}

    # This will act as a for loop to go through the dictionary
    for field, pattern in patterns.items():
        # Using the re library, I will search for the pattern selected from the for loop iteration within the text html
        match = re.search(pattern, text)
        if match:
            # strip removes the spaces besides the word 
            applicant_data[field] = match.group(1).strip()
        else:
            # I want the field to be filled with something, so if there is nothing, it fills with "NA"
            applicant_data[field] = "NA" # If field not found

    #print (applicant_data)

    all_data[entry_page] = applicant_data


print(all_data)

with open("applicant.json", "w") as f:
    json.dump(applicant_data, f, indent=4)