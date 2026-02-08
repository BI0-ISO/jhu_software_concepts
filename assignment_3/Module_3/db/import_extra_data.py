"""
Import a large cleaned JSON/JSONL file into the applicants table.

Features:
- Normalizes fields into the SCHEMA_OVERVIEW structure.
- Avoids duplicates by URL (upsert-style update).
- Writes last_100_entries.json and invalidates analysis cache.
"""

import json
import os
import re
from datetime import datetime, date

import psycopg

from db_config import DB_CONFIG

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_PATH = os.path.join(BASE_DIR, "M3_material", "data", "extra_llm_applicant_data.json")
LAST_ENTRIES_PATH = os.path.join(BASE_DIR, "db", "last_100_entries.json")
ANALYSIS_CACHE_PATH = os.path.join(BASE_DIR, "db", "analysis_cache.json")
REPORT_PATH = os.path.join(BASE_DIR, "static", "reports", "module_3_report.pdf")


def load_records(path):
    """Load JSON array or JSONL into a list of dicts."""
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
    """Return GPA only when it is between 0 and 4.0."""
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
    """Prefer program+university combined display when available."""
    if program and university and university not in program:
        return f"{university} - {program}"
    return program or university


def clean_text(value):
    """Strip NUL bytes and whitespace for Postgres text fields."""
    if value is None:
        return None
    text = str(value)
    # Remove NUL bytes that Postgres cannot store
    return text.replace("\x00", "").strip() or None


def normalize_status(value):
    """Normalize decision text into accepted/rejected/waitlisted."""
    if not value:
        return None
    v = str(value).strip().lower()
    if "accept" in v:
        return "accepted"
    if "reject" in v or "deny" in v:
        return "rejected"
    if "wait" in v:
        return "waitlisted"
    return v


def parse_semester_year(value):
    """Parse a 'Fall 2026' style string into term/year components."""
    if not value:
        return None, None
    text = str(value).strip()
    parts = text.split()
    if len(parts) >= 2:
        term = parts[0].title()
        year = to_int(parts[1])
        return term, year
    return None, None


def parse_decision_date(value, fallback_year):
    """Parse short decision dates (e.g., '21 Jan') with fallback year."""
    if not value or not fallback_year:
        return None
    text = str(value).strip()
    # e.g., "21 Jan" -> "21 Jan 2026"
    for fmt in ("%d %b", "%d %B"):
        try:
            dt = datetime.strptime(text, fmt)
            return f"{fallback_year}-{dt.month:02d}-{dt.day:02d}"
        except ValueError:
            continue
    return None


def normalize_term(status, start_term):
    """Normalize the term string to Title Case."""
    if not start_term:
        return None
    return str(start_term).strip().title()


def normalize_record(r):
    """Normalize a raw record to the applicants schema."""
    university = clean_text(r.get("university"))
    program = clean_text(r.get("program"))
    status = normalize_status(clean_text(r.get("applicant_status") or r.get("status")))
    start_term = r.get("start_term")
    start_year = r.get("start_year")
    semester_year = clean_text(r.get("semester_year_start"))
    if not start_term or not start_year:
        term_from_sem, year_from_sem = parse_semester_year(r.get("semester_year_start"))
        start_term = start_term or term_from_sem
        start_year = start_year or year_from_sem
    term = clean_text(semester_year) or normalize_term(status, start_term)
    date_added_iso = to_date(r.get("date_added"))
    if not term and date_added_iso:
        try:
            month = int(date_added_iso[5:7])
            year = date_added_iso[:4]
            if 1 <= month <= 5 or status == "accepted":
                term = f"Fall {year}"
        except (ValueError, TypeError):
            pass
    acceptance_date = to_date(r.get("acceptance_date"))
    if not acceptance_date and status == "accepted":
        acceptance_date = parse_decision_date(r.get("decision_date"), (start_year or (date_added_iso or "")[:4]))
    program_value = clean_text(combine_program_university(program, university))
    if not program_value:
        program_value = clean_text(combine_program_university(r.get("llm-generated-program"), r.get("llm-generated-university")))
    return {
        "program": program_value,
        "comments": clean_text(r.get("comments")),
        "date_added": date_added_iso,
        "acceptance_date": acceptance_date,
        "url": clean_text(r.get("url")),
        "term": term,
        "status": status,
        "us_or_international": clean_text(r.get("citizenship") or r.get("us_or_international")),
        "degree": clean_text(r.get("degree_type") or r.get("masters_or_phd") or r.get("degree")),
        "gpa": to_gpa(r.get("gpa")),
        "gre": to_numeric(r.get("gre_total") or r.get("gre")),
        "gre_v": to_numeric(r.get("gre_verbal") or r.get("gre_v")),
        "gre_aw": to_numeric(r.get("gre_aw")),
        "llm_generated_program": clean_text(r.get("llm_generated_program") or r.get("llm-generated-program")),
        "llm_generated_university": clean_text(r.get("llm_generated_university") or r.get("llm-generated-university")),
    }


def ensure_table(conn):
    """Create the applicants table if missing."""
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            p_id SERIAL PRIMARY KEY,
            program TEXT,
            comments TEXT,
            date_added DATE,
            acceptance_date DATE,
            url TEXT,
            status TEXT,
            term TEXT,
            us_or_international TEXT,
            gpa FLOAT,
            gre FLOAT,
            gre_v FLOAT,
            gre_aw FLOAT,
            degree TEXT,
            llm_generated_program TEXT,
            llm_generated_university TEXT
        )
        """)
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS comments TEXT")
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS date_added DATE")
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS acceptance_date DATE")
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS url TEXT")
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS us_or_international TEXT")


def url_exists(conn, url):
    """Return True if the given URL already exists."""
    if not url:
        return False
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM applicants WHERE url = %s", (url,))
        return cur.fetchone() is not None


def insert_records(conn, records):
    """Insert new records and update duplicates with missing values."""
    inserted = 0
    duplicates = 0
    with conn.cursor() as cur:
        for r in records:
            url = r.get("url")
            if url and url_exists(conn, url):
                duplicates += 1
                cur.execute("""
                    UPDATE applicants SET
                        program = COALESCE(NULLIF(program, ''), %(program)s),
                        comments = COALESCE(NULLIF(comments, ''), %(comments)s),
                        date_added = COALESCE(date_added, %(date_added)s),
                        acceptance_date = COALESCE(acceptance_date, %(acceptance_date)s),
                        status = COALESCE(NULLIF(status, ''), %(status)s),
                        term = COALESCE(NULLIF(term, ''), %(term)s),
                        us_or_international = COALESCE(NULLIF(us_or_international, ''), %(us_or_international)s),
                        degree = COALESCE(NULLIF(degree, ''), %(degree)s),
                        llm_generated_program = COALESCE(NULLIF(llm_generated_program, ''), %(llm_generated_program)s),
                        llm_generated_university = COALESCE(NULLIF(llm_generated_university, ''), %(llm_generated_university)s),
                        gpa = COALESCE(gpa, %(gpa)s),
                        gre = COALESCE(gre, %(gre)s),
                        gre_v = COALESCE(gre_v, %(gre_v)s),
                        gre_aw = COALESCE(gre_aw, %(gre_aw)s)
                    WHERE url = %(url)s
                """, r)
                continue
            cur.execute("""
                INSERT INTO applicants (
                    program, comments, date_added, acceptance_date, url, status, term, us_or_international, gpa, gre, gre_v, gre_aw,
                    degree, llm_generated_program, llm_generated_university
                ) VALUES (
                    %(program)s, %(comments)s, %(date_added)s, %(acceptance_date)s, %(url)s, %(status)s, %(term)s, %(us_or_international)s, %(gpa)s, %(gre)s, %(gre_v)s, %(gre_aw)s,
                    %(degree)s, %(llm_generated_program)s, %(llm_generated_university)s
                )
            """, r)
            inserted += 1
    return inserted, duplicates


def write_last_entries(conn, path, limit=100):
    """Write the newest N entries to disk for inspection."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM applicants ORDER BY p_id DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    entries = [dict(zip(columns, row)) for row in rows]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(entries, f, indent=2, default=str)


def invalidate_analysis_cache():
    """Remove cached analysis and report to force recompute."""
    for path in (ANALYSIS_CACHE_PATH, REPORT_PATH):
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def _recreate_table(conn):
    """Drop and recreate the applicants table."""
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS applicants")
    ensure_table(conn)


def main(path=DEFAULT_PATH, recreate=False):
    """Import cleaned data into the database."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing data file: {path}")

    records = load_records(path)
    normalized = [normalize_record(r) for r in records]
    conn = psycopg.connect(**DB_CONFIG, autocommit=True)
    if recreate:
        _recreate_table(conn)
    else:
        ensure_table(conn)
    inserted, duplicates = insert_records(conn, normalized)
    write_last_entries(conn, LAST_ENTRIES_PATH)
    conn.close()
    invalidate_analysis_cache()
    print(f"Import complete. Inserted {inserted}, skipped {duplicates} duplicates.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=DEFAULT_PATH)
    parser.add_argument("--recreate", action="store_true")
    args = parser.parse_args()
    main(args.path, recreate=args.recreate)
