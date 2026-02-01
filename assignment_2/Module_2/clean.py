# clean.py
import re
import json
from bs4 import BeautifulSoup


def clean_data(raw_pages):
    """
    Converts raw GradCafe HTML into structured applicant data.
    All missing fields are stored as None.
    """

    cleaned = []

    for page in raw_pages:
        soup = BeautifulSoup(page["html"], "html.parser")
        text = soup.get_text("\n")

        decision_raw = _extract(r"Decision\s*(.*)", text)

        record = {
            "program_name": _extract(r"Program\s*(.*)", text),
            "university": _extract(r"Institution\s*(.*)", text),
            "comments": _extract_notes(text),
            "date_added": _extract_date(text),
            "url": page["url"],

            # Applicant status
            "applicant_status": _normalize_decision(decision_raw),

            # Dates
            "acceptance_date": _extract(r"Accepted on\s*(.*)", text),
            "rejection_date": _extract(r"Rejected on\s*(.*)", text),

            # Program metadata
            "degree_type": _extract(r"(PhD|Masters|MS|MA)", text),
            "start_term": _extract(r"(Fall|Spring|Summer|Winter)", text),
            "start_year": _extract(r"(20\d{2})", text),

            # Citizenship
            "citizenship": _extract(r"(International|American)", text),

            # GRE / GPA
            "gre_total": _extract(r"GRE General:\s*(\d{3})", text),
            "gre_verbal": _extract(r"GRE Verbal:\s*(\d{3})", text),
            "gre_aw": _extract(r"Analytical Writing:\s*(\d+\.?\d*)", text),
            "gpa": _extract(r"GPA:\s*([\d.]+)", text),

            # LLM standardized fields (filled later)
            "clean_program_name": None,
            "clean_university_name": None
        }

        cleaned.append(record)

    return cleaned


def save_data(data, filename="applicant_data.json"):
    """Save cleaned applicant data to JSON."""
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def load_data(filename="applicant_data.json"):
    """Load applicant data from JSON."""
    with open(filename, "r") as f:
        return json.load(f)


# ---------- Private helpers ----------

def _extract(pattern, text, group=1):
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(group).strip() if match else None


def _extract_date(text):
    match = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}",
        text
    )
    return match.group(0) if match else None


def _extract_notes(text):
    match = re.search(
        r"Notes\s*(.*?)\n(?:Timeline|Program|Institution|Decision)",
        text,
        re.DOTALL | re.IGNORECASE
    )

    if not match:
        return None

    notes = match.group(1).strip()
    return notes if notes else None


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
