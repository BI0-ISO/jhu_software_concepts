"""
Load a JSON/JSONL file into the applicants table (smaller batches).
"""

from __future__ import annotations

import os

import psycopg

from db_config import DB_CONFIG
from migrate import migrate
from normalize import load_records, normalize_records

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_PATH = os.path.join(BASE_DIR, "M3_material", "data", "extra_llm_applicant_data.json")

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


def create_table() -> None:
    migrate()


def insert_records(conn, records: list[dict]) -> None:
    with conn.cursor() as cur:
        cur.executemany(INSERT_SQL, records)


def main(path=DEFAULT_PATH) -> None:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing data file: {path}")

    records = normalize_records(load_records(path))
    with psycopg.connect(**DB_CONFIG, autocommit=True) as conn:
        create_table()
        insert_records(conn, records)
    print(f"Data load complete. Processed {len(records)} records.")


if __name__ == "__main__":
    main()
