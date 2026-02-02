# clean.py
import re                  # For regular expression matching
import json                # For saving/loading structured data
from bs4 import BeautifulSoup  # For parsing HTML content


def clean_data(raw_pages):
    """
    Converts raw GradCafe HTML into structured applicant data.

    Parameters:
        raw_pages (List[Dict]): List of dictionaries, each containing:
            - "url": URL of the applicant entry
            - "html": raw HTML content of the page

    Returns:
        List[Dict]: A list of cleaned applicant records with fields:
            program, university, comments, date_added, url,
            applicant_status, acceptance_date, rejection_date,
            degree_type, start_term, start_year,
            citizenship, gre_total, gre_verbal, gre_aw, gpa

    Notes:
        - Missing or zero-value fields are converted to None.
        - All HTML is stripped from the content.
    """

    # List to store structured applicant data
    cleaned = []

    # Iterate over each raw HTML page
    for page in raw_pages:

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(page["html"], "html.parser")

        # Extract text from HTML, separating lines by '\n'
        text = soup.get_text("\n")

        # Extract raw decision text (e.g., "Accepted", "Rejected", etc.)
        decision_raw = _extract(r"Decision\s*(.*)", text)

        # Create structured record dictionary for the applicant
        record = {
            # Program and institution
            "program": _extract(r"Program\s*(.*)", text),
            "university": _extract(r"Institution\s*(.*)", text),

            # Additional notes or comments, if available
            "comments": _extract_notes(text),

            # Date the applicant information was added to GradCafe
            "date_added": _extract_date_added(text),

            # URL of the applicant entry
            "url": page["url"],

            # Applicant decision/status normalized to accepted/rejected/waitlisted
            "applicant_status": _normalize_decision(decision_raw),

            # Acceptance and rejection dates (if provided)
            "acceptance_date": _extract(r"Accepted on\s*(.*)", text),
            "rejection_date": _extract(r"Rejected on\s*(.*)", text),

            # Program metadata
            "degree_type": _extract_degree_type(text),  # Masters/PhD
            "start_term": _extract(r"\b(Fall|Spring|Summer|Winter)\b", text),
            "start_year": _extract(r"\b(20\d{2})\b", text),

            # Citizenship status
            "citizenship": _extract(r"\b(International|American)\b", text),

            # GRE scores; zero or missing values converted to None
            "gre_total": _none_if_zero(_extract(r"GRE General:\s*(\d{1,3})", text)),
            "gre_verbal": _none_if_zero(_extract(r"GRE Verbal:\s*(\d{1,3})", text)),
            "gre_aw": _none_if_zero(_extract(r"Analytical Writing:\s*(\d+\.?\d*)", text)),

            # GPA extraction handles malformed text or missing values
            "gpa": _extract_gpa(text),
        }

        # Append structured record to cleaned list
        cleaned.append(record)

    # Return the list of cleaned applicant records
    return cleaned


def save_data(data, filename="applicant_data.json"):
    """
    Save cleaned applicant data to a JSON file.

    Parameters:
        data (List[Dict]): List of structured applicant records
        filename (str): Filename to save JSON data
    """
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)  # Pretty-print JSON with indentation


def load_data(filename="applicant_data.json"):
    """
    Load cleaned applicant data from a JSON file.

    Parameters:
        filename (str): Filename of JSON data to load

    Returns:
        List[Dict]: Loaded applicant records
    """
    with open(filename, "r") as f:
        return json.load(f)


# ---------- Private helper functions ----------

def _extract(pattern, text, group=1):
    """
    General regex extractor.

    Parameters:
        pattern (str): Regex pattern to search
        text (str): Text to search within
        group (int): Regex capture group to return (default 1)

    Returns:
        str or None: Matched string, stripped of whitespace, or None if not found
    """
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(group).strip() if match else None


def _extract_date_added(text):
    """
    Extracts the notification date in M/D/YYYY format from GradCafe entry.

    Example: "on 12/31/2022" → "12/31/2022"

    Returns None if not found.
    """
    match = re.search(r"on\s+(\d{1,2}/\d{1,2}/\d{4})", text)
    if not match:
        return None
    return match.group(1)


def _extract_notes(text):
    """
    Extract Notes content up to the last character before 'Timeline'.

    - Replaces multiple whitespace/newlines with a single space
    - Returns None if no notes found
    """
    match = re.search(r"Notes\s*(.*?)(?=\s+Timeline\b)", text, re.DOTALL | re.IGNORECASE)
    if not match:
        return None
    notes = re.sub(r"\s+", " ", match.group(1)).strip()
    return notes if notes else None


def _extract_degree_type(text):
    """
    Extract text between 'Type' and 'Degree', ignoring extra spaces.

    Example: 'Type   Masters   Degree' → 'Masters'
    Returns None if not found.
    """
    match = re.search(r"Type\s*(.*?)\s*Degree", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    degree = re.sub(r"\s+", " ", match.group(1)).strip()
    return degree if degree else None


def _extract_gpa(text):
    """
    Extracts undergrad GPA robustly from text between 'Undergrad GPA' and 'GRE General'.

    Handles:
        - numeric GPA
        - 'NONE' or '0'
        - Extra whitespace/newlines

    Returns:
        str or None: GPA as string, or None if missing or invalid
    """
    match = re.search(r"Undergrad\s*GPA\s*[:\n]+\s*([^\n]+?)\s*(?=GRE General)", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    gpa = match.group(1).strip()
    gpa = re.sub(r"\s+", "", gpa)  # Remove remaining spaces/newlines

    if gpa.upper() == "NONE" or gpa == "0" or gpa == "":
        return None

    return gpa


def _none_if_zero(value):
    """
    Convert numeric zero values to None.

    Parameters:
        value (str or number): Input value

    Returns:
        value or None
    """
    if value is None:
        return None
    try:
        return None if float(value) == 0 else value
    except ValueError:
        # If conversion to float fails, return original value
        return value


def _normalize_decision(value):
    """
    Normalize applicant decision text to one of:
    - "accepted"
    - "rejected"
    - "waitlisted"

    Returns None if no recognizable decision is found.
    """
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
