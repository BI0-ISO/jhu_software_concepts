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


def test_get_db_config_default(monkeypatch):
    # When DATABASE_URL is not set, default config should be returned.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    importlib.reload(db_config)
    cfg = db_config.get_db_config()
    assert cfg["dbname"] == "Johnny"
