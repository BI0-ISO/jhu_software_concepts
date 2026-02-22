"""Legacy Module 1 app factory (not used by run.py)."""

# pylint: disable=invalid-name,import-outside-toplevel

from flask import Flask

def create_app():
    """Create a simple Flask app with the Module 1 blueprint."""
    app = Flask(__name__)

    try:
        # Legacy import path used by tests and older code.
        from Module_3.board import bp
    except ImportError:
        # Fallback to the local Module 1 blueprint.
        from M1_material.board import bp
    app.register_blueprint(bp)

    return app
