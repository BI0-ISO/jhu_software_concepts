import urllib3
from bs4 import BeautifulSoup
import json

# Create a PoolManager instance
http = urllib3.PoolManager()

# Fetch the webpage
url = "https://www.thegradcafe.com/result/900000"
response = http.request("GET", url)

# Decode bytes to string
html = response.data.decode("utf-8")

# Parse HTML with BeautifulSoup
soup = BeautifulSoup(html, "html.parser")

# Now you can use soup to find elements
print(soup.title.text)  # Example: prints the page title

# test_df = {
#         "Program Name": ,
#         "University": ,
#         "Comments": ,
#         "Date of Information Added to Grad Café": ,
#         "URL link to applicant entry": ,
#         "Applicant Status": ,
#         "Accepted: Acceptance Date": ,
#         "Rejected: Rejection Date": ,
#         "Semester and Year of Program Start": ,
#         "International / American Student": ,
#         "GRE Score": ,
#         "GRE V Score": ,
#         "Masters or PhD": ,
#         "GPA": ,
#         "GRE AW": 
#     }



