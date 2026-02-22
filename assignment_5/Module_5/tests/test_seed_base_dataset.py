"""
Tests for the base dataset seeding helper.

These are focused unit tests that avoid real database access by mocking
psycopg connections and file checks.
"""

import pytest

from db import import_extra_data

pytestmark = pytest.mark.db


def test_seed_base_dataset_skips_when_already_seeded(monkeypatch):
    monkeypatch.setattr(import_extra_data, "_BASE_SEEDED", True)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    assert import_extra_data.seed_base_dataset("missing.jsonl") == 0


def test_seed_base_dataset_skips_missing_path(monkeypatch):
    monkeypatch.setattr(import_extra_data, "_BASE_SEEDED", False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(import_extra_data.os.path, "exists", lambda *_: False)
    assert import_extra_data.seed_base_dataset("missing.jsonl") == 0


def test_seed_base_dataset_no_records(monkeypatch):
    monkeypatch.setattr(import_extra_data, "_BASE_SEEDED", False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(import_extra_data.os.path, "exists", lambda *_: True)
    monkeypatch.setattr(import_extra_data, "load_records", lambda *_: [{"url": None}])
    monkeypatch.setattr(import_extra_data, "normalize_records", lambda records: records)

    called = {"connect": 0}

    def _connect(**_):
        called["connect"] += 1
        raise AssertionError("connect should not be called when no records exist")

    monkeypatch.setattr(import_extra_data.psycopg, "connect", _connect)
    assert import_extra_data.seed_base_dataset("data.jsonl") == 0
    assert import_extra_data._BASE_SEEDED is True
    assert called["connect"] == 0


def test_seed_base_dataset_inserts_records(monkeypatch):
    monkeypatch.setattr(import_extra_data, "_BASE_SEEDED", False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(import_extra_data.os.path, "exists", lambda *_: True)
    monkeypatch.setattr(import_extra_data, "load_records", lambda *_: ["raw"])
    records = [{"url": "https://example.com/result/1"}]
    monkeypatch.setattr(import_extra_data, "normalize_records", lambda *_: records)
    monkeypatch.setattr(import_extra_data, "get_db_config", lambda: {})

    class DummyCursor:
        def __init__(self):
            self.executed = None

        def executemany(self, stmt, rows):
            self.executed = (stmt, rows)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyConn:
        def __init__(self, cursor):
            self._cursor = cursor

        def cursor(self):
            return self._cursor

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    cursor = DummyCursor()
    monkeypatch.setattr(import_extra_data.psycopg, "connect", lambda **_: DummyConn(cursor))

    count = import_extra_data.seed_base_dataset("data.jsonl")
    assert count == 1
    assert import_extra_data._BASE_SEEDED is True
    assert cursor.executed is not None
