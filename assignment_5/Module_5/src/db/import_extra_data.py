"""
Import a cleaned JSON/JSONL file into the applicants table.

Uses normalize.py for all field mapping and cleanup.
"""

# pylint: disable=duplicate-code

from __future__ import annotations

import json
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
LAST_ENTRIES_PATH = os.path.join(BASE_DIR, "db", "last_100_entries.json")
ANALYSIS_CACHE_PATH = os.path.join(BASE_DIR, "db", "analysis_cache.json")
REPORT_PATH = os.path.join(BASE_DIR, "static", "reports", "module_3_report.pdf")
MAX_LIMIT = 100
_BASE_SEEDED = False

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


def _clamp_limit(value: int | None, default: int = 100) -> int:
    """Clamp limit values to a safe 1..MAX_LIMIT range."""
    try:
        limit_value = int(value) if value is not None else default
    except (TypeError, ValueError):
        limit_value = default
    if limit_value < 1:
        return 1
    if limit_value > MAX_LIMIT:
        return MAX_LIMIT
    return limit_value


def seed_base_dataset(path: str = DEFAULT_PATH) -> int:
    """
    Ensure the base JSON/JSONL dataset is loaded into the applicants table.

    This is idempotent: rows with duplicate URLs are ignored via ON CONFLICT.
    """
    global _BASE_SEEDED
    if _BASE_SEEDED:
        return 0
    if os.getenv("PYTEST_CURRENT_TEST"):
        return 0
    if not os.path.exists(path):
        return 0

    records = normalize_records(load_records(path))
    # Skip records without a URL to avoid duplicate NULL entries.
    records = [r for r in records if r.get("url")]
    if not records:
        _BASE_SEEDED = True
        return 0

    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.executemany(INSERT_SQL, records)

    _BASE_SEEDED = True
    return len(records)


def ensure_table() -> None:
    """Ensure the applicants table exists."""
    migrate()


def recreate_table(conn) -> None:
    """Drop and recreate the applicants table and migration table."""
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS applicants")
        cur.execute("DROP TABLE IF EXISTS schema_migrations")
    migrate()


def insert_records(conn, records: list[dict]) -> None:
    """Insert normalized records into the database."""
    with conn.cursor() as cur:
        cur.executemany(INSERT_SQL, records)


def write_last_entries(conn, path, limit=100) -> None:
    """Write the newest entries to disk for inspection."""
    limit = _clamp_limit(limit)
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM applicants ORDER BY p_id DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
    entries = [dict(zip(columns, row)) for row in rows]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file_handle:
        json.dump(entries, file_handle, indent=2, default=str)


def invalidate_analysis_cache() -> None:
    """Remove cached analysis artifacts to force recompute."""
    for path in (ANALYSIS_CACHE_PATH, REPORT_PATH):
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def main(path=DEFAULT_PATH, recreate=False) -> None:
    """Import the cleaned data file into the applicants table."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing data file: {path}")

    records = load_records(path)
    normalized = normalize_records(records)

    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
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
