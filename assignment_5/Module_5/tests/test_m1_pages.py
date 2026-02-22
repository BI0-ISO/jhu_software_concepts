"""
Route tests for Module 1 pages.

These confirm the basic static pages render with HTTP 200 responses.
"""

import pytest

pytestmark = pytest.mark.web


def test_module_1_pages_render(client):
    # Each of these routes maps to a simple template in Module 1.
    for path in ("/", "/about", "/projects", "/projects/module-1"):
        resp = client.get(path)
        assert resp.status_code == 200
