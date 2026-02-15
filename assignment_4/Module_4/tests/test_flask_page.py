"""
Beginner-friendly tests for the Flask analysis page.

These tests focus on:
- Whether the app factory creates an app with required routes.
- Whether the /analysis page loads and contains key UI elements.
"""

import pytest
from bs4 import BeautifulSoup

from run import create_app


@pytest.mark.web
def test_app_factory_registers_routes():
    # Ensure the app factory returns a Flask app with required routes.
    # This is a pure Flask configuration test; it doesn't touch DB/network.
    app = create_app({"TESTING": True})
    # Collect the registered URL rules so we can assert our routes exist.
    routes = {rule.rule for rule in app.url_map.iter_rules()}
    expected = {
        "/analysis",
        "/pull-data",
        "/update-analysis",
        "/projects/module-3",
        "/projects/module-3/pull-data",
        "/projects/module-3/update-analysis",
        "/projects/module-3/pull-status",
        "/projects/module-3/cancel-pull",
    }
    # .issubset means "all expected routes appear in the actual route list".
    assert expected.issubset(routes)


@pytest.mark.web
def test_get_analysis_page_loads(client):
    # Basic page-load test for the analysis dashboard.
    # The pytest fixture "client" uses Flask's test client (no real server).
    resp = client.get("/analysis")
    assert resp.status_code == 200
    # Parse the HTML so we can reliably find elements by attributes/text.
    soup = BeautifulSoup(resp.data.decode("utf-8"), "html.parser")

    # Buttons must be present for UI control tests.
    # We locate them by their stable data-testid attributes.
    update_btn = soup.find(attrs={"data-testid": "update-analysis-btn"})
    pull_btn = soup.find(attrs={"data-testid": "pull-data-btn"})
    assert update_btn is not None
    assert pull_btn is not None

    # Page should communicate analysis context and answer labels.
    page_text = soup.get_text()
    assert "Analysis" in page_text
    assert "Answer:" in page_text
