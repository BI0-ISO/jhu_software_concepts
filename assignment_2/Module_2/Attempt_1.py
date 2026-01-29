import urllib3
from bs4 import BeautifulSoup
import json


http = urllib3.PoolManager(cert_reqs=ssl.CERT_NONE)

url = http.request("GET", "https://www.thegradcafe.com/result/900000")
html = url.data.decode("utf-8")



with urllib.request.urlopen(url) as response:
    html = response.read()

soup = BeautifulSoup(html, "html.parser")


test_df = {
        "Program Name": ,
        "University": ,
        "Comments": ,
        "Date of Information Added to Grad Café": ,
        "URL link to applicant entry": ,
        "Applicant Status": ,
        "Accepted: Acceptance Date": ,
        "Rejected: Rejection Date": ,
        "Semester and Year of Program Start": ,
        "International / American Student": ,
        "GRE Score": ,
        "GRE V Score": ,
        "Masters or PhD": ,
        "GPA": ,
        "GRE AW": 
    }



