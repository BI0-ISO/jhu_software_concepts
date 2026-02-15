"""
Simple migration runner for Module 3.

Applies SQL files in db/migrations/ in sorted order, recording them in the
schema_migrations table so they are only applied once.
"""

from __future__ import annotations

import glob
import os

import psycopg

try:
    from .db_config import get_db_config
except ImportError:  # fallback when run as a script
    from db_config import get_db_config

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


def migrate() -> None:
    os.makedirs(MIGRATIONS_DIR, exist_ok=True)
    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "filename TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT NOW()"
                ")"
            )

            for path in sorted(glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql"))):
                filename = os.path.basename(path)
                cur.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", (filename,))
                if cur.fetchone():
                    continue

                with open(path, "r", encoding="utf-8") as f:
                    sql = f.read()
                if sql.strip():
                    cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (filename,),
                )
