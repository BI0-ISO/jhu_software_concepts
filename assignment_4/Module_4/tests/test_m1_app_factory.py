"""
Tests for the legacy Module 1 app factory.

These are small sanity checks to ensure the factory can build a Flask app
and register a blueprint, even though Module 1 isn't used by run.py.
"""

import types

import pytest
from flask import Blueprint

import M1_material

pytestmark = pytest.mark.web


def test_m1_create_app_registers_blueprint(monkeypatch):
    # The legacy factory imports Module_3.board at call time, so we inject
    # a lightweight dummy module to satisfy that import.
    dummy_bp = Blueprint("dummy", __name__)
    module_pkg = types.ModuleType("Module_3")
    module_board = types.ModuleType("Module_3.board")
    module_board.bp = dummy_bp

    # Inject the dummy modules so the import inside create_app succeeds.
    monkeypatch.setitem(__import__("sys").modules, "Module_3", module_pkg)
    monkeypatch.setitem(__import__("sys").modules, "Module_3.board", module_board)

    app = M1_material.create_app()

    # The dummy blueprint should be registered by name.
    assert "dummy" in app.blueprints
