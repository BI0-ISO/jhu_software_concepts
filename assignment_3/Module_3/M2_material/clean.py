"""
GradCafe HTML cleaner.

This module takes raw HTML pages from the scraper and converts them into a
consistent dict shape used by the database loader. It focuses on extracting:
- core program/university fields
- applicant status/decision dates
- term/year, citizenship, GRE/GPA
- sanitized comments/notes
"""
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
        # Parse the HTML into text so regex extraction is consistent.
        soup = BeautifulSoup(page["html"], "html.parser")
        text = soup.get_text("\n")

        # The decision line can include a date string ("Accepted on Jan 31").
        decision_raw = _extract(r"Decision\s*(.*)", text)
        decision_date = None
        if decision_raw:
            match = re.search(r"\bon\s+(.+)$", decision_raw, re.IGNORECASE)
            if match:
                decision_date = match.group(1).strip()
        status = _normalize_decision(decision_raw)
        acceptance_date = _extract(r"Accepted on\s*(.*)", text)
        term = _extract(r"\b(Fall|Spring|Summer|Winter)\b", text)

        # Build a normalized record. More numeric cleanup happens later.
        record = {
            "program": _extract(r"Program\s*(.*)", text),
            "university": _extract(r"Institution\s*(.*)", text),
            "comments": _sanitize_text(_extract_notes(text)),  # sanitized
            "date_added": page.get("date_added") or _extract_date_added(text),
            "url": page["url"],
            "applicant_status": status,
            "acceptance_date": acceptance_date,
            "decision_date": decision_date,
            "rejection_date": _extract(r"Rejected on\s*(.*)", text),
            "degree_type": _extract_degree_type(text),
            "start_term": term,
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
    """Utility helper to persist cleaned data for debugging."""
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def load_data(filename="applicant_data.json"):
    """Utility helper to load cleaned data back into memory."""
    with open(filename, "r") as f:
        return json.load(f)


# ---------- Private helper functions ----------

def _extract(pattern, text, group=1):
    """Regex helper that returns the requested capture group or None."""
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(group).strip() if match else None


def _extract_date_added(text):
    """Extract a usable date-added string while ignoring placeholder values."""
    match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", text)
    if match:
        value = match.group(1)
        return None if value == "31/12/1969" else value
    match = re.search(r"([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})", text)
    if match:
        return match.group(1)
    match = re.search(r"(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})", text)
    if match:
        return match.group(1)
    return None


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
    """Extract the degree type block from the result page."""
    match = re.search(r"Type\s*(.*?)\s*Degree", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    degree = re.sub(r"\s+", " ", match.group(1)).strip()
    return degree if degree else None


def _extract_gpa(text):
    """Extract the GPA string; numeric normalization happens downstream."""
    match = re.search(r"Undergrad\s*GPA\s*[:\n]+\s*([^\n]+?)\s*(?=GRE General)", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    gpa = re.sub(r"\s+", "", match.group(1).strip())
    if gpa.upper() == "NONE" or gpa == "0" or gpa == "":
        return None
    return gpa


def _none_if_zero(value):
    """Convert zero-like values to None to avoid skewing averages."""
    if value is None:
        return None
    try:
        return None if float(value) == 0 else value
    except ValueError:
        return value


def _normalize_decision(value):
    """Map raw decision text to accepted/rejected/waitlisted or None."""
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
