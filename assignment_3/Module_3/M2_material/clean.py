# clean.py
import re
import json
from bs4 import BeautifulSoup

def clean_data(raw_pages):
    """
    Converts raw GradCafe HTML into structured applicant data.
    Sanitizes notes/comments to remove emojis/unwanted Unicode characters.
    """
    cleaned = []

    for page in raw_pages:
        soup = BeautifulSoup(page["html"], "html.parser")
        text = soup.get_text("\n")

        decision_raw = _extract(r"Decision\s*(.*)", text)

        record = {
            "program": _extract(r"Program\s*(.*)", text),
            "university": _extract(r"Institution\s*(.*)", text),
            "comments": _sanitize_text(_extract_notes(text)),  # sanitized
            "date_added": _extract_date_added(text),
            "url": page["url"],
            "applicant_status": _normalize_decision(decision_raw),
            "acceptance_date": _extract(r"Accepted on\s*(.*)", text),
            "rejection_date": _extract(r"Rejected on\s*(.*)", text),
            "degree_type": _extract_degree_type(text),
            "start_term": _extract(r"\b(Fall|Spring|Summer|Winter)\b", text),
            "start_year": _extract(r"\b(20\d{2})\b", text),
            "citizenship": _extract(r"\b(International|American)\b", text),
            "gre_total": _none_if_zero(_extract(r"GRE General:\s*(\d{1,3})", text)),
            "gre_verbal": _none_if_zero(_extract(r"GRE Verbal:\s*(\d{1,3})", text)),
            "gre_aw": _none_if_zero(_extract(r"Analytical Writing:\s*(\d+\.?\d*)", text)),
            "gpa": _extract_gpa(text),
        }

        cleaned.append(record)

    return cleaned


def save_data(data, filename="applicant_data.json"):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def load_data(filename="applicant_data.json"):
    with open(filename, "r") as f:
        return json.load(f)


# ---------- Private helper functions ----------

def _extract(pattern, text, group=1):
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(group).strip() if match else None


def _extract_date_added(text):
    match = re.search(r"on\s+(\d{1,2}/\d{1,2}/\d{4})", text)
    if not match:
        return None
    return match.group(1)


def _extract_notes(text):
    """
    Extract Notes content up to the last character before 'Timeline'.
    """
    match = re.search(r"Notes\s*(.*?)(?=\s+Timeline\b)", text, re.DOTALL | re.IGNORECASE)
    if not match:
        return None
    notes = re.sub(r"\s+", " ", match.group(1)).strip()
    return notes if notes else None


def _extract_degree_type(text):
    match = re.search(r"Type\s*(.*?)\s*Degree", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    degree = re.sub(r"\s+", " ", match.group(1)).strip()
    return degree if degree else None


def _extract_gpa(text):
    match = re.search(r"Undergrad\s*GPA\s*[:\n]+\s*([^\n]+?)\s*(?=GRE General)", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    gpa = re.sub(r"\s+", "", match.group(1).strip())
    if gpa.upper() == "NONE" or gpa == "0" or gpa == "":
        return None
    return gpa


def _none_if_zero(value):
    if value is None:
        return None
    try:
        return None if float(value) == 0 else value
    except ValueError:
        return value


def _normalize_decision(value):
    if not value:
        return None
    value = value.lower()
    if "accept" in value:
        return "accepted"
    if "reject" in value:
        return "rejected"
    if "wait" in value:
        return "waitlisted"
    return None


def _sanitize_text(text):
    """
    Remove unwanted Unicode characters (e.g., emojis or fancy quotes) from text.
    Keeps letters, numbers, basic punctuation, and whitespace.
    """
    if not text:
        return None
    cleaned = ''.join(c if 32 <= ord(c) <= 126 else ' ' for c in text)
    cleaned = ' '.join(cleaned.split())
    return cleaned if cleaned else None
