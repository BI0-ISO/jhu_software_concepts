"""Legacy Module 1 app factory (not used by run.py)."""

from flask import Flask

def create_app():
    """Create a simple Flask app with the Module 1 blueprint."""
    app = Flask(__name__)

    from Module_3.board import bp
    app.register_blueprint(bp)

    return app
