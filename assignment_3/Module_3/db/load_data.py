"""
Load JSON/JSONL data into the applicants table.

This is a one-time or batch loader that normalizes raw fields into the
schema defined in SCHEMA_OVERVIEW.md.
"""

import json
import re
from datetime import datetime, date
import psycopg
from db_config import DB_CONFIG
from migrate import migrate

def load_records(path):
    """Load either JSON array or JSONL file into a list of dicts."""
    with open(path, "r") as f:
        # Detect JSON array vs JSONL by first non-whitespace char
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

def to_int(value):
    """Safe int conversion."""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def to_float(value):
    """Safe float conversion (legacy)."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def extract_number(value):
    """Extract the first numeric token from a string."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "")
    match = re.search(r"[-+]?\d*\.?\d+", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except (TypeError, ValueError):
        return None

def to_numeric(value):
    """Convert values like '165Q' into floats."""
    return extract_number(value)

def to_gpa(value):
    """Return GPA only when it falls between 0 and 4.0."""
    num = extract_number(value)
    if num is None:
        return None
    if 0 <= num <= 4.0:
        return num
    return None

def to_date(value):
    """Normalize dates into YYYY-MM-DD strings."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if not text:
        return None
    if len(text) >= 10 and text[:10].count("-") == 2 and text[:10][:4].isdigit():
        return text[:10]
    for fmt in (
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %d %Y",
        "%B %d %Y",
        "%d %b %Y",
        "%d %B %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None

def combine_program_university(program, university):
    """Prefer program+university display when both are present."""
    if program and university and university not in program:
        return f"{university} - {program}"
    return program or university

def normalize_record(r):
    """Map a raw record into the applicants schema."""
    university = r.get("university")
    program = r.get("program")
    status = r.get("applicant_status")
    term = r.get("start_term")
    year = to_int(r.get("start_year"))
    term_year = f"{term} {year}" if term and year else term
    return {
        "program": combine_program_university(program, university),
        "comments": r.get("comments"),
        "date_added": to_date(r.get("date_added")),
        "acceptance_date": to_date(r.get("acceptance_date")),
        "url": r.get("url"),
        "term": term_year,
        "status": status,
        "us_or_international": r.get("citizenship"),
        "degree": r.get("degree_type"),
        "gpa": to_gpa(r.get("gpa")),
        "gre": to_numeric(r.get("gre_total")),
        "gre_v": to_numeric(r.get("gre_verbal") or r.get("gre_v")),
        "gre_aw": to_numeric(r.get("gre_aw")),
        "llm_generated_program": r.get("llm-generated-program"),
        "llm_generated_university": r.get("llm-generated-university"),
    }

def create_table(conn):
    """Create the applicants table if it does not exist."""
    migrate()
    print("Table 'applicants' ready.")

def insert_data(conn, records):
    """Insert normalized records into the applicants table."""
    with conn.cursor() as cur:
        for r in records:
            try:
                cur.execute("""
                    INSERT INTO applicants (
                        program, comments, date_added, acceptance_date, url, status, term, us_or_international, gpa, gre, gre_v, gre_aw,
                        degree, llm_generated_program, llm_generated_university
                    ) VALUES (
                        %(program)s, %(comments)s, %(date_added)s, %(acceptance_date)s, %(url)s, %(status)s, %(term)s, %(us_or_international)s, %(gpa)s, %(gre)s, %(gre_v)s, %(gre_aw)s,
                        %(degree)s, %(llm_generated_program)s, %(llm_generated_university)s
                    )
                """, r)
            except Exception as e:
                print(f"Error inserting record: {e}")

def main():
    """Run a full load from the default JSON file."""
    conn = psycopg.connect(**DB_CONFIG, autocommit=True)
    create_table(conn)
    raw_records = load_records("M3_material/data/llm_extend_applicant_data.json")
    records = [normalize_record(r) for r in raw_records]
    insert_data(conn, records)
    conn.close()
    print("Data load complete.")

if __name__ == "__main__":
    main()
