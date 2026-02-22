"""
Coverage tests for limit clamping helpers.

These tests ensure defensive limit logic clamps invalid values and
out-of-range values to safe defaults.
"""

import pytest

from M2_material import pull_data
from M3_material import query_data
from db import import_extra_data

pytestmark = pytest.mark.db


def test_pull_data_clamp_limit_bounds():
    assert pull_data._clamp_limit("bad") == 100
    assert pull_data._clamp_limit(0) == 1
    assert pull_data._clamp_limit(1000) == pull_data.MAX_LIMIT


def test_query_data_clamp_limit_bounds():
    assert query_data._clamp_limit("bad") == 1
    assert query_data._clamp_limit(0) == 1
    assert query_data._clamp_limit(1000) == query_data.MAX_LIMIT


def test_import_extra_data_clamp_limit_bounds():
    assert import_extra_data._clamp_limit("bad") == 100
    assert import_extra_data._clamp_limit(0) == 1
    assert import_extra_data._clamp_limit(1000) == import_extra_data.MAX_LIMIT
