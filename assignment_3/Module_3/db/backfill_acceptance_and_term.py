"""
Backfill acceptance_date and term for existing records.

This script updates rows using a local data file and a "spring -> fall" rule
when term is missing.
"""

import json
import os
from datetime import datetime, date

import psycopg

from db_config import DB_CONFIG

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PATH = os.path.join(BASE_DIR, "M3_material", "data", "llm_extend_applicant_data.json")
LAST_ENTRIES_PATH = os.path.join(BASE_DIR, "db", "last_100_entries.json")


def load_records(path):
    """Load JSON array or JSONL records."""
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


def normalize_term(status, start_term):
    """Normalize the term string to Title Case."""
    if not start_term:
        return None
    return str(start_term).strip().title()


def to_int(value):
    """Safe int conversion."""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def write_last_entries(conn, path, limit=100):
    """Write latest N entries to disk for inspection."""
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM applicants ORDER BY p_id DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    entries = [dict(zip(columns, row)) for row in rows]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(entries, f, indent=2, default=str)


def main():
    """Run the backfill against the applicants table."""
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Missing data file: {DATA_PATH}")

    records = load_records(DATA_PATH)
    conn = psycopg.connect(**DB_CONFIG, autocommit=True)
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS acceptance_date DATE")
        cur.execute("ALTER TABLE applicants ADD COLUMN IF NOT EXISTS term TEXT")

        updated = 0
        for r in records:
            url = r.get("url")
            if not url:
                continue
            acceptance_date = to_date(r.get("acceptance_date"))
            term = normalize_term(r.get("applicant_status"), r.get("start_term"))
            cur.execute(
                "UPDATE applicants SET acceptance_date = COALESCE(acceptance_date, %s), term = COALESCE(term, %s) WHERE url = %s",
                (acceptance_date, term, url),
            )
            updated += cur.rowcount

        # Fill missing term from date_added using the spring->fall rule
        cur.execute("""
            UPDATE applicants
            SET term = COALESCE(
                    term,
                    CASE
                        WHEN date_added IS NOT NULL
                         AND EXTRACT(MONTH FROM date_added) BETWEEN 1 AND 5
                        THEN 'Fall ' || EXTRACT(YEAR FROM date_added)::int
                        WHEN status ILIKE 'accept%'
                         AND date_added IS NOT NULL
                        THEN 'Fall ' || EXTRACT(YEAR FROM date_added)::int
                        ELSE term
                    END
                )
            WHERE term IS NULL
        """)

    write_last_entries(conn, LAST_ENTRIES_PATH)
    conn.close()
    print(f"Backfill complete. Updated {updated} rows.")


if __name__ == "__main__":
    main()
