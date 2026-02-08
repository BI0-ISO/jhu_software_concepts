"""Module 1 basic page routes (home/about/projects)."""

from flask import render_template
from datetime import datetime
from . import bp

@bp.route("/")
def home():
    """Landing page."""
    return render_template("home.html")

@bp.route("/about")
def about():
    """About page."""
    return render_template("about.html")

@bp.route("/projects")
def projects():
    """Projects landing page."""
    return render_template("projects.html")

@bp.route("/projects/module-1")
def module_1_project():
    """Module 1 project page."""
    return render_template("project_module_1.html")

@bp.app_context_processor
def inject_year():
    """Inject current year into templates."""
    return {"current_year": datetime.now().year}
