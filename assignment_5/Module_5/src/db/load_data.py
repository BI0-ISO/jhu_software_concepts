"""
Load a JSON/JSONL file into the applicants table (smaller batches).
"""

# pylint: disable=duplicate-code

from __future__ import annotations

import os

import psycopg
from psycopg import sql

try:
    from .db_config import get_db_config
    from .migrate import migrate
    from .normalize import load_records, normalize_records
except ImportError:  # fallback when run as a script
    from db_config import get_db_config
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

INSERT_SQL = sql.SQL(
    "INSERT INTO applicants ({fields}) "
    "VALUES ({values}) "
    "ON CONFLICT (url) DO NOTHING"
).format(
    fields=sql.SQL(", ").join(sql.Identifier(col) for col in COLUMNS),
    values=sql.SQL(", ").join(sql.Placeholder(col) for col in COLUMNS),
)


def create_table() -> None:
    """Ensure the applicants table exists before insert."""
    migrate()


def insert_records(conn, records: list[dict]) -> None:
    """Insert normalized records into the database."""
    with conn.cursor() as cur:
        cur.executemany(INSERT_SQL, records)


def main(path=DEFAULT_PATH) -> None:
    """Run a full load from the default JSON/JSONL file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing data file: {path}")

    records = normalize_records(load_records(path))
    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        create_table()
        insert_records(conn, records)
    print(f"Data load complete. Processed {len(records)} records.")


if __name__ == "__main__":
    main()
