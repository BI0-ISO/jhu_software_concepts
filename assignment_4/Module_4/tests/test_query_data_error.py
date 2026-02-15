"""
Focused tests for error handling in query_data.
"""

import pytest

from M3_material import query_data

pytestmark = pytest.mark.db


def test_get_connection_raises_runtime_error(monkeypatch):
    # Force psycopg.connect to raise so get_connection wraps the error.
    def _raise(*args, **kwargs):
        raise Exception("boom")

    monkeypatch.setattr(query_data.psycopg, "connect", _raise)
    with pytest.raises(RuntimeError):
        query_data.get_connection()
