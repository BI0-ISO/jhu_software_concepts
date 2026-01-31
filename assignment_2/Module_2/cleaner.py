import re
import json
from bs4 import BeautifulSoup

def clean_data(raw_pages):
    cleaned = []

    for page in raw_pages:
        soup = BeautifulSoup(page["html"], "html.parser")
        text = soup.get_text("\n")

        data = {
            "program_name": _extract(r"Program\s*(.*)", text),
            "university": _extract(r"Institution\s*(.*)", text),
            "comments": _extract(r"Notes\s*(.*)", text),
            "date_added": _extract(r"on\s+(\d{2}/\d{2}/\d{4})", text),
            "applicant_status": _extract(r"Decision\s*(.*)", text),
            "degree_type": _extract(r"Degree Type\s*(.*)", text),
            "gpa": _extract(r"Undergrad GPA\s*(.*)", text),
            "gre_total": _extract(r"GRE General:\s*(\d+)", text),
            "gre_verbal": _extract(r"GRE Verbal:\s*(\d+)", text),
            "gre_aw": _extract(r"Analytical Writing:\s*(\d+\.?\d*)", text),
            "url": page["url"]
        }

        cleaned.append(data)

    return cleaned


def save_data(data, filename="applicant_data.json"):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


def load_data(filename="applicant_data.json"):
    with open(filename, "r") as f:
        return json.load(f)


def _extract(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None
