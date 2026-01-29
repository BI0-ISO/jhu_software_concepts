import urllib3
from bs4 import BeautifulSoup
import json
import re


http = urllib3.PoolManager()


url = "https://www.thegradcafe.com/result/900000"
response = http.request("GET", url)


html = response.data.decode("utf-8")


soup = BeautifulSoup(html, "html.parser")

text = soup.get_text(separator="\n")

print(text)

print(soup.title.text)  

patterns = {
    "Institution": r"Institution\s*(.*)",
    "Degree Type": r"Degree Type\s*(.*)",
    "Decision": r"Decision\s*(.*)",
    "Undergrad GPA": r"Undergrad GPA\s*(.*)",
    "Program": r"Program\s*(.*)",
    "Notes": r"Notes\s*(.*)",
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

print (applicant_data)