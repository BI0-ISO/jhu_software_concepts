"""
Tests for db.load_data and db.import_extra_data helpers.

These use a real PostgreSQL connection but avoid large data sets.
"""

import json
from pathlib import Path

import pytest
import psycopg

from db import load_data, import_extra_data
from db.db_config import get_db_config
from db.migrate import migrate

pytestmark = pytest.mark.db


@pytest.fixture()
def sample_record():
    # Fully-populated record matching the applicants schema.
    return {
        "program": "Test University, Computer Science",
        "comments": "sample",
        "date_added": "2026-01-01",
        "acceptance_date": "2026-01-02",
        "url": "https://www.thegradcafe.com/result/999901",
        "status": "accepted",
        "term": "Fall",
        "us_or_international": "American",
        "gpa": 3.7,
        "gre": 160,
        "gre_v": 155,
        "gre_aw": 4.0,
        "degree": "Masters",
        "llm_generated_program": "Computer Science",
        "llm_generated_university": "Test University",
    }


def test_load_data_main_inserts(tmp_path, sample_record, monkeypatch):
    # Create a minimal JSON file so load_data.main passes its file-exists check.
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps([sample_record]))

    # Short-circuit normalization to keep the test focused on load/insert.
    monkeypatch.setattr(load_data, "load_records", lambda path: [sample_record])
    monkeypatch.setattr(load_data, "normalize_records", lambda records: records)

    load_data.main(path=str(data_path))

    # Verify the row is actually inserted.
    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants")
            assert cur.fetchone()[0] == 1


def test_load_data_main_missing_file(tmp_path):
    # Missing input files should raise FileNotFoundError.
    with pytest.raises(FileNotFoundError):
        load_data.main(path=str(tmp_path / "missing.json"))


def test_import_extra_data_main_recreate(tmp_path, sample_record, monkeypatch):
    # Provide a JSON file and patch paths to use temp locations.
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps([sample_record]))

    monkeypatch.setattr(import_extra_data, "load_records", lambda path: [sample_record])
    monkeypatch.setattr(import_extra_data, "normalize_records", lambda records: records)

    # Redirect output artifacts so we do not write into the repo tree.
    monkeypatch.setattr(import_extra_data, "LAST_ENTRIES_PATH", str(tmp_path / "last_entries.json"))
    monkeypatch.setattr(import_extra_data, "ANALYSIS_CACHE_PATH", str(tmp_path / "analysis_cache.json"))
    monkeypatch.setattr(import_extra_data, "REPORT_PATH", str(tmp_path / "report.pdf"))

    # Create fake cache/report files to ensure invalidate_analysis_cache removes them.
    (tmp_path / "analysis_cache.json").write_text("{}")
    (tmp_path / "report.pdf").write_text("fake")

    import_extra_data.main(path=str(data_path), recreate=True)

    # Confirm rows are inserted after recreate.
    with psycopg.connect(**get_db_config(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applicants")
            assert cur.fetchone()[0] == 1

    assert not (tmp_path / "analysis_cache.json").exists()
    assert not (tmp_path / "report.pdf").exists()


def test_import_extra_data_main_non_recreate(tmp_path, sample_record, monkeypatch):
    # Ensure the non-recreate path uses ensure_table.
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps([sample_record]))

    monkeypatch.setattr(import_extra_data, "load_records", lambda path: [sample_record])
    monkeypatch.setattr(import_extra_data, "normalize_records", lambda records: records)

    called = {"count": 0}
    monkeypatch.setattr(import_extra_data, "ensure_table", lambda: called.update(count=called["count"] + 1))
    monkeypatch.setattr(import_extra_data, "insert_records", lambda *a, **k: None)
    monkeypatch.setattr(import_extra_data, "write_last_entries", lambda *a, **k: None)

    class DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(import_extra_data.psycopg, "connect", lambda **kwargs: DummyConn())

    import_extra_data.main(path=str(data_path), recreate=False)
    assert called["count"] == 1


def test_import_extra_data_missing_file(tmp_path):
    # Missing files should raise FileNotFoundError.
    with pytest.raises(FileNotFoundError):
        import_extra_data.main(path=str(tmp_path / "missing.json"))


def test_invalidate_analysis_cache_oserror(monkeypatch):
    # OSError during cache removal should be swallowed.
    monkeypatch.setattr(import_extra_data.os.path, "exists", lambda *_: True)
    monkeypatch.setattr(import_extra_data.os, "remove", lambda *_: (_ for _ in ()).throw(OSError("fail")))
    import_extra_data.invalidate_analysis_cache()


def test_import_extra_data_ensure_table_calls_migrate(monkeypatch):
    # Ensure ensure_table triggers migrate().
    called = {"count": 0}
    monkeypatch.setattr(import_extra_data, "migrate", lambda: called.update(count=called["count"] + 1))
    import_extra_data.ensure_table()
    assert called["count"] == 1


def test_import_extra_data_main_script_entry(monkeypatch, tmp_path, sample_record):
    # Run the module as __main__ to cover the argparse entrypoint.
    import runpy
    import sys
    import types

    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps([sample_record]))

    # Provide fake modules so the script can run without a real DB.
    fake_db = types.ModuleType("db_config")
    fake_db.get_db_config = lambda: {}
    fake_migrate = types.ModuleType("migrate")
    fake_migrate.migrate = lambda: None
    fake_norm = types.ModuleType("normalize")
    fake_norm.load_records = lambda *_: []
    fake_norm.normalize_records = lambda records: records

    class DummyCursor:
        description = []

        def execute(self, *a, **k):
            pass

        def executemany(self, *a, **k):
            pass

        def fetchall(self):
            return []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyConn:
        def cursor(self):
            return DummyCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_psycopg = types.ModuleType("psycopg")
    fake_psycopg.connect = lambda **kwargs: DummyConn()

    monkeypatch.setitem(sys.modules, "db_config", fake_db)
    monkeypatch.setitem(sys.modules, "migrate", fake_migrate)
    monkeypatch.setitem(sys.modules, "normalize", fake_norm)
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)

    monkeypatch.setattr(sys, "argv", ["import_extra_data.py", "--path", str(data_path)])
    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / "src" / "db" / "import_extra_data.py"), run_name="__main__")


def test_import_extra_data_fallback_imports(monkeypatch):
    # Execute the module via runpy with no package context to hit fallback imports.
    import runpy
    import types
    import sys

    fake_db = types.ModuleType("db_config")
    fake_db.get_db_config = lambda: {}
    fake_migrate = types.ModuleType("migrate")
    fake_migrate.migrate = lambda: None
    fake_norm = types.ModuleType("normalize")
    fake_norm.load_records = lambda *_: []
    fake_norm.normalize_records = lambda *_: []

    monkeypatch.setitem(sys.modules, "db_config", fake_db)
    monkeypatch.setitem(sys.modules, "migrate", fake_migrate)
    monkeypatch.setitem(sys.modules, "normalize", fake_norm)

    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / "src" / "db" / "import_extra_data.py"), run_name="import_extra_data_test")


def test_load_data_script_entry(monkeypatch, tmp_path, sample_record):
    # Run the load_data module as __main__ to cover argparse entrypoint.
    import runpy
    import sys
    import types

    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps([sample_record]))

    fake_db = types.ModuleType("db_config")
    fake_db.get_db_config = lambda: {}
    fake_migrate = types.ModuleType("migrate")
    fake_migrate.migrate = lambda: None
    fake_norm = types.ModuleType("normalize")
    fake_norm.load_records = lambda *_: []
    fake_norm.normalize_records = lambda records: records

    class DummyCursor:
        def executemany(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyConn:
        def cursor(self):
            return DummyCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_psycopg = types.ModuleType("psycopg")
    fake_psycopg.connect = lambda **kwargs: DummyConn()

    monkeypatch.setitem(sys.modules, "db_config", fake_db)
    monkeypatch.setitem(sys.modules, "migrate", fake_migrate)
    monkeypatch.setitem(sys.modules, "normalize", fake_norm)
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)

    root = Path(__file__).resolve().parents[1]
    # Ensure the default data file exists so the script entrypoint doesn't error.
    default_path = root / "src" / "M3_material" / "data" / "extra_llm_applicant_data.json"
    created = False
    if not default_path.exists():
        default_path.parent.mkdir(parents=True, exist_ok=True)
        default_path.write_text("[]")
        created = True
    try:
        runpy.run_path(str(root / "src" / "db" / "load_data.py"), run_name="__main__")
    finally:
        if created and default_path.exists():
            default_path.unlink()


def test_load_data_fallback_imports(monkeypatch):
    # Execute the module via runpy with no package context to hit fallback imports.
    import runpy
    import types
    import sys

    fake_db = types.ModuleType("db_config")
    fake_db.get_db_config = lambda: {}
    fake_migrate = types.ModuleType("migrate")
    fake_migrate.migrate = lambda: None
    fake_norm = types.ModuleType("normalize")
    fake_norm.load_records = lambda *_: []
    fake_norm.normalize_records = lambda *_: []

    monkeypatch.setitem(sys.modules, "db_config", fake_db)
    monkeypatch.setitem(sys.modules, "migrate", fake_migrate)
    monkeypatch.setitem(sys.modules, "normalize", fake_norm)

    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / "src" / "db" / "load_data.py"), run_name="load_data_test")
