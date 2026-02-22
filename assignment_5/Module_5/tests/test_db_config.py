"""
Tests for db_config environment handling.
"""

import importlib
import os

import pytest

import db.db_config as db_config

pytestmark = pytest.mark.db


def test_get_db_config_uses_database_url(monkeypatch):
    # When DATABASE_URL is set, get_db_config should return conninfo.
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    importlib.reload(db_config)
    cfg = db_config.get_db_config()
    assert cfg == {"conninfo": "postgresql://example"}


def test_get_db_config_from_env(monkeypatch):
    # When DATABASE_URL is not set, env vars should be used.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_NAME", "test_db")
    monkeypatch.setenv("DB_USER", "tester")
    monkeypatch.setenv("DB_PASSWORD", "secret")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_GSSENCMODE", "disable")
    importlib.reload(db_config)
    cfg = db_config.get_db_config()
    assert cfg["dbname"] == "test_db"
    assert cfg["user"] == "tester"
    assert cfg["host"] == "localhost"
    assert cfg["password"] == "secret"
    assert cfg["port"] == 5432
    assert cfg["gssencmode"] == "disable"


def test_get_db_config_missing_env(monkeypatch):
    # Missing env vars should raise a clear error.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    importlib.reload(db_config)
    with pytest.raises(RuntimeError):
        db_config.get_db_config()
