"""
Tests for busy-state behavior on JSON endpoints.

These verify that the server returns a 409 and does not perform work
when a pull is already running.
"""

import pytest


@pytest.mark.buttons
def test_pull_data_calls_handler_when_not_busy(app, client):
    # When not busy, /pull-data should call the injected handler.
    called = {"count": 0}

    def handler():
        called["count"] += 1
        return {"inserted": 0}

    # Override the busy-state check so this request should proceed.
    app.config["PULL_RUNNING_CHECK"] = lambda: False
    # Inject a fake pull handler to avoid network/LLM work in tests.
    app.config["PULL_HANDLER"] = handler

    resp = client.post("/pull-data")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    assert called["count"] == 1


@pytest.mark.buttons
def test_pull_data_busy_returns_409(app, client):
    # Force busy state and assert the JSON API returns 409/{"busy": true}.
    # We replace the busy-check function via app.config.
    app.config["PULL_RUNNING_CHECK"] = lambda: True
    # No handler should run when busy; route should short-circuit.
    resp = client.post("/pull-data")
    assert resp.status_code == 409
    assert resp.get_json() == {"busy": True}


@pytest.mark.buttons
def test_update_analysis_busy_returns_409(app, client):
    # Ensure update is not executed while a pull is running.
    called = {"count": 0}

    def _update():
        called["count"] += 1

    # Simulate a running pull and inject the update handler.
    app.config["PULL_RUNNING_CHECK"] = lambda: True
    app.config["UPDATE_HANDLER"] = _update

    resp = client.post("/update-analysis")
    assert resp.status_code == 409
    assert resp.get_json() == {"busy": True}
    # Busy gate should prevent any update call.
    assert called["count"] == 0


@pytest.mark.buttons
def test_update_analysis_returns_200_when_not_busy(app, client):
    # When not busy, /update-analysis should run and return ok.
    called = {"count": 0}

    def _update():
        called["count"] += 1

    # Allow the update and inject a fake update handler.
    app.config["PULL_RUNNING_CHECK"] = lambda: False
    app.config["UPDATE_HANDLER"] = _update

    resp = client.post("/update-analysis")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}
    assert called["count"] == 1
