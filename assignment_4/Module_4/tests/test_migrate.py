"""
Tests for db.migrate behavior.

We drop the schema_migrations table to force migrations to re-run.
"""

import pytest
from pathlib import Path
import psycopg

from db.db_config import get_db_config
from db.migrate import migrate

pytestmark = pytest.mark.db


def test_migrate_reapplies_when_schema_table_missing():
    # Drop the schema_migrations table so migrate() re-applies SQL files.
    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS schema_migrations")

    migrate()

    # Verify the schema_migrations table exists after migration.
    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'schema_migrations')"
            )
            assert cur.fetchone()[0] is True


def test_migrate_fallback_imports(monkeypatch):
    # Execute migrate.py with no package context to cover the fallback import.
    import runpy
    import types
    import sys

    fake_db = types.ModuleType("db_config")
    fake_db.get_db_config = lambda: {}
    fake_psycopg = types.ModuleType("psycopg")

    class DummyConn:
        def cursor(self):
            return self

        def execute(self, *a, **k):
            pass

        def fetchone(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_psycopg.connect = lambda **kwargs: DummyConn()
    monkeypatch.setitem(sys.modules, "db_config", fake_db)
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)

    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / "src" / "db" / "migrate.py"), run_name="migrate_test")
