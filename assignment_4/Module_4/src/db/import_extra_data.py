"""
Import a cleaned JSON/JSONL file into the applicants table.

Uses normalize.py for all field mapping and cleanup.
"""

from __future__ import annotations

import os

import psycopg

from db_config import DB_CONFIG
from migrate import migrate
from normalize import load_records, normalize_records

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_PATH = os.path.join(BASE_DIR, "M3_material", "data", "extra_llm_applicant_data.json")
LAST_ENTRIES_PATH = os.path.join(BASE_DIR, "db", "last_100_entries.json")
ANALYSIS_CACHE_PATH = os.path.join(BASE_DIR, "db", "analysis_cache.json")
REPORT_PATH = os.path.join(BASE_DIR, "static", "reports", "module_3_report.pdf")

COLUMNS = [
    "program",
    "comments",
    "date_added",
    "acceptance_date",
    "url",
    "status",
    "term",
    "us_or_international",
    "gpa",
    "gre",
    "gre_v",
    "gre_aw",
    "degree",
    "llm_generated_program",
    "llm_generated_university",
]

INSERT_SQL = f"""
    INSERT INTO applicants ({", ".join(COLUMNS)})
    VALUES ({", ".join(f"%({c})s" for c in COLUMNS)})
    ON CONFLICT (url) DO NOTHING
"""


def ensure_table() -> None:
    migrate()


def recreate_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS applicants")
        cur.execute("DROP TABLE IF EXISTS schema_migrations")
    migrate()


def insert_records(conn, records: list[dict]) -> None:
    with conn.cursor() as cur:
        cur.executemany(INSERT_SQL, records)


def write_last_entries(conn, path, limit=100) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM applicants ORDER BY p_id DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    entries = [dict(zip(columns, row)) for row in rows]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        import json

        json.dump(entries, f, indent=2, default=str)


def invalidate_analysis_cache() -> None:
    for path in (ANALYSIS_CACHE_PATH, REPORT_PATH):
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def main(path=DEFAULT_PATH, recreate=False) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing data file: {path}")

    records = load_records(path)
    normalized = normalize_records(records)

    with psycopg.connect(**DB_CONFIG, autocommit=True) as conn:
        if recreate:
            recreate_table(conn)
        else:
            ensure_table()
        insert_records(conn, normalized)
        write_last_entries(conn, LAST_ENTRIES_PATH)

    invalidate_analysis_cache()
    print(f"Import complete. Processed {len(normalized)} records.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=DEFAULT_PATH)
    parser.add_argument("--recreate", action="store_true")
    args = parser.parse_args()
    main(args.path, recreate=args.recreate)
