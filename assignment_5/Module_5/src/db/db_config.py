"""Database connection settings for Module 3."""

from __future__ import annotations

import os

REQUIRED_ENV_VARS = ("DB_HOST", "DB_NAME", "DB_USER")


def get_db_config() -> dict:
    """Return connection kwargs, preferring DATABASE_URL when set."""
    url = os.getenv("DATABASE_URL")
    if url:
        return {"conninfo": url}
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing required DB environment variables: {', '.join(missing)}")
    cfg = {
        "host": os.getenv("DB_HOST"),
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
    }
    password = os.getenv("DB_PASSWORD")
    if password:
        cfg["password"] = password
    port = os.getenv("DB_PORT")
    if port:
        cfg["port"] = int(port) if port.isdigit() else port
    gss = os.getenv("DB_GSSENCMODE")
    if gss:
        cfg["gssencmode"] = gss
    return cfg
