"""
Normalization utilities for applicant data.

Designed to be small, testable, and easy to reuse in loaders.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Iterable, Tuple


DATE_FORMATS = (
    "%Y-%m-%d",
    "%B %d, %Y",
    "%b %d, %Y",
    "%m/%d/%Y",
    "%d/%m/%Y",
)


def load_records(path: str) -> list[dict]:
    """Load JSON array or JSONL file into a list of dicts."""
    with open(path, "r") as f:
        first = ""
        while True:
            ch = f.read(1)
            if not ch:
                break
            if not ch.isspace():
                first = ch
                break
        f.seek(0)

        if first == "[":
            return json.load(f)

        records = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
        return records


def clean_text(value):
    """Strip whitespace and NUL bytes from text fields."""
    if value is None:
        return None
    text = str(value).replace("\x00", "").strip()
    return text or None


def extract_number(value):
    """Extract the first numeric token as float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"[-+]?\d*\.?\d+", str(value).replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_date(value):
    """Parse a date-like value to YYYY-MM-DD string."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    if len(text) >= 10 and text[:10].count("-") == 2 and text[:4].isdigit():
        return text[:10]
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def normalize_status(value):
    """Normalize decision text into consistent lowercase labels."""
    if not value:
        return None
    v = str(value).strip().lower()
    if v.startswith("accept"):
        return "accepted"
    if v.startswith("reject"):
        return "rejected"
    if v.startswith("wait"):
        return "waitlisted"
    if v.startswith("interview"):
        return "interview"
    return v


def term_from_semester_year(value):
    """Extract the term text (e.g., 'Fall' from 'Fall 2026')."""
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = re.match(r"[A-Za-z]+", text)
    if not match:
        return None
    return match.group(0).title()


def extract_year(value):
    """Extract a 4-digit year from a string."""
    if not value:
        return None
    match = re.search(r"(19|20)\d{2}", str(value))
    return match.group(0) if match else None


def parse_decision_date(value, year):
    """Parse short decision dates (e.g., '17 Jan') with a fallback year."""
    if not value or not year:
        return None
    text = str(value).strip()
    for fmt in ("%d %b", "%d %B"):
        try:
            dt = datetime.strptime(text, fmt)
            return f"{year}-{dt.month:02d}-{dt.day:02d}"
        except ValueError:
            continue
    return None


def split_program_university(raw_program: str | None) -> Tuple[str | None, str | None]:
    """Split 'Program, University' into (program, university)."""
    text = clean_text(raw_program)
    if not text:
        return None, None
    idx = text.rfind(", University")
    if idx != -1:
        program = text[:idx].strip().strip(",")
        university = text[idx + 2 :].strip()
        return program or None, university or None
    if ", " in text:
        program, university = text.split(", ", 1)
        return program.strip() or None, university.strip() or None
    return text, None


def format_program(university, program):
    """Return a combined 'University, Program' string."""
    university = clean_text(university)
    program = clean_text(program)
    if university and program:
        return f"{university}, {program}"
    return program or university


def normalize_record(r: dict) -> dict:
    """Normalize a raw record to the applicants schema."""
    raw_program = r.get("program")
    program_part, university_part = split_program_university(raw_program)
    university_part = university_part or clean_text(r.get("university"))

    llm_program = clean_text(r.get("llm-generated-program") or r.get("llm_generated_program"))
    llm_university = clean_text(r.get("llm-generated-university") or r.get("llm_generated_university"))
    program_part = program_part or llm_program
    university_part = university_part or llm_university

    term = term_from_semester_year(r.get("semester_year_start"))
    if not term:
        term = term_from_semester_year(r.get("start_term"))

    status = normalize_status(r.get("applicant_status") or r.get("status"))
    date_added = parse_date(r.get("date_added"))
    year = extract_year(r.get("semester_year_start")) or (date_added[:4] if date_added else None)
    acceptance_date = parse_date(r.get("acceptance_date"))
    if not acceptance_date and status == "accepted":
        acceptance_date = parse_decision_date(r.get("decision_date"), year)

    return {
        "program": format_program(university_part, program_part),
        "comments": clean_text(r.get("comments")),
        "date_added": date_added,
        "acceptance_date": acceptance_date,
        "url": clean_text(r.get("url")),
        "status": status,
        "term": term,
        "us_or_international": clean_text(r.get("citizenship") or r.get("us_or_international")),
        "gpa": extract_number(r.get("gpa")),
        "gre": extract_number(r.get("gre_total") or r.get("gre")),
        "gre_v": extract_number(r.get("gre_verbal") or r.get("gre_v")),
        "gre_aw": extract_number(r.get("gre_aw")),
        "degree": clean_text(r.get("degree_type") or r.get("masters_or_phd") or r.get("degree")),
        "llm_generated_program": llm_program,
        "llm_generated_university": llm_university,
    }


def normalize_records(records: Iterable[dict]) -> list[dict]:
    """Normalize a list of raw records."""
    return [normalize_record(r) for r in records]
