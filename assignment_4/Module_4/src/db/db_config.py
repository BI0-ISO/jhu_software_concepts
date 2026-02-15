"""Database connection settings for Module 3."""

from __future__ import annotations

import os

DEFAULT_DB_CONFIG = {
    "host": "localhost",
    "dbname": "Johnny",
    "user": "mckeysa1",
    "password": "",
    "gssencmode": "disable",
}


def get_db_config() -> dict:
    """Return connection kwargs, preferring DATABASE_URL when set."""
    url = os.getenv("DATABASE_URL")
    if url:
        return {"conninfo": url}
    return dict(DEFAULT_DB_CONFIG)


DB_CONFIG = get_db_config()
