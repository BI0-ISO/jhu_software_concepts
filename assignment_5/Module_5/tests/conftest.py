"""
Shared pytest fixtures and helpers.

Pytest automatically discovers this file and makes the fixtures available
to all tests in this folder. This is the recommended place for reusable
setup/teardown logic.
"""

import os
import sys
from pathlib import Path

import pytest
import psycopg


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
# Allow tests to import application modules from the src/ directory.
# Without this, `import run` or `import M3_material` would fail in tests.
sys.path.insert(0, str(SRC_DIR))

_TEST_DB_ENV_MAP = {
    "DB_HOST_TEST": "DB_HOST",
    "DB_PORT_TEST": "DB_PORT",
    "DB_NAME_TEST": "DB_NAME",
    "DB_USER_TEST": "DB_USER",
    "DB_PASSWORD_TEST": "DB_PASSWORD",
}


def _apply_test_db_overrides():
    # If *_TEST variables are set, copy them onto the standard DB_* vars
    # so tests can target a dedicated database without affecting production.
    for test_var, base_var in _TEST_DB_ENV_MAP.items():
        value = os.getenv(test_var)
        if value:
            os.environ[base_var] = value


def _build_database_url():
    # Build a DATABASE_URL from environment variables.
    user = os.getenv("DB_USER", "mckeysa1")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    dbname = os.getenv("DB_NAME", "Johnny")
    port = os.getenv("DB_PORT")
    auth = f"{user}:{password}" if password else user
    hostport = f"{host}:{port}" if port else host
    return f"postgresql://{auth}@{hostport}/{dbname}"


@pytest.fixture(scope="session", autouse=True)
def _set_database_url():
    # Ensure DATABASE_URL is always set for psycopg connection helpers.
    # Scope "session" means this runs once per test session.
    _apply_test_db_overrides()
    if not os.getenv("DATABASE_URL"):
        os.environ.setdefault("DB_HOST", "localhost")
        os.environ.setdefault("DB_NAME", "Johnny")
        os.environ.setdefault("DB_USER", "mckeysa1")
        os.environ.setdefault("DB_PASSWORD", "")
        os.environ["DATABASE_URL"] = _build_database_url()


@pytest.fixture(autouse=True)
def _reset_db():
    # Migrate and clear tables between tests to keep the suite deterministic.
    # autouse=True means every test gets a clean database state.
    from db.migrate import migrate
    from db.db_config import get_db_config

    migrate()
    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        with conn.cursor() as cur:
            # TRUNCATE removes all rows and resets primary key counters.
            cur.execute("TRUNCATE applicants RESTART IDENTITY")
            cur.execute("TRUNCATE pull_jobs RESTART IDENTITY")
    yield


@pytest.fixture()
def app(tmp_path):
    # Create a Flask app with injectable behavior and temp file paths.
    # tmp_path is a pytest-provided temporary directory fixture.
    from run import create_app

    app = create_app(
        {
            "TESTING": True,
            # Avoid dependency on the LLM during tests.
            "LLM_READY_CHECK": lambda: True,
            # Default to "not busy" unless a test overrides it.
            "PULL_RUNNING_CHECK": lambda: False,
            # Keep analysis artifacts in a temporary folder.
            "ANALYSIS_CACHE_PATH": str(tmp_path / "analysis_cache.json"),
            "REPORT_PATH": str(tmp_path / "module_3_report.pdf"),
        }
    )
    return app


@pytest.fixture()
def client(app):
    # Flask test client for HTTP requests.
    # The test client lets you call routes without starting a real server.
    return app.test_client()


@pytest.fixture()
def sample_record():
    # Factory for a fully-populated applicant row that matches the schema.
    # Returning a factory function lets tests override just the fields they need.
    def _record(**overrides):
        base = {
            "program": "Johns Hopkins University, Computer Science",
            "comments": "sample",
            "date_added": "2026-01-15",
            "acceptance_date": "2026-01-20",
            "url": "https://www.thegradcafe.com/result/999001",
            "status": "accepted",
            "term": "Fall",
            "us_or_international": "American",
            "gpa": 3.8,
            "gre": 168.0,
            "gre_v": 160.0,
            "gre_aw": 4.5,
            "degree": "Masters",
            "llm_generated_program": "Computer Science",
            "llm_generated_university": "Johns Hopkins University",
        }
        base.update(overrides)
        return base

    return _record


@pytest.fixture()
def insert_records():
    # Helper to insert rows with ON CONFLICT DO NOTHING semantics.
    # This mirrors the app behavior and prevents duplicate rows in tests.
    from db.db_config import get_db_config

    columns = [
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
    insert_sql = f"""
        INSERT INTO applicants ({", ".join(columns)})
        VALUES ({", ".join(f"%({c})s" for c in columns)})
        ON CONFLICT (url) DO NOTHING
    """

    def _insert(records):
        # Bulk insert via executemany to keep tests fast.
        with psycopg.connect(**get_db_config(), autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.executemany(insert_sql, records)

    return _insert
