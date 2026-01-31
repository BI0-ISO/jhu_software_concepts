# from flask import Blueprint, render_template
# from datetime import datetime

# bp = Blueprint("pages", __name__)

# @bp.route("/")
# def home():
#     return render_template("home.html")

# @bp.route("/about")
# def about():
#     return render_template("about.html")

# @bp.route("/projects")
# def projects():
#     return render_template("projects.html")

# @bp.route("/projects/module-1")
# def module_1_project():
#     return render_template("project_module_1.html")

# @bp.app_context_processor
# def inject_year():
#     return {"current_year": datetime.now().year}


from flask import render_template
from datetime import datetime
from . import bp   # 👈 import the blueprint

@bp.route("/")
def home():
    return render_template("home.html")

@bp.route("/about")
def about():
    return render_template("about.html")

@bp.route("/projects")
def projects():
    return render_template("projects.html")

@bp.route("/projects/module-1")
def module_1_project():
    return render_template("project_module_1.html")

@bp.app_context_processor
def inject_year():
    return {"current_year": datetime.now().year}
