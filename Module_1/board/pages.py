# from flask import Blueprint

# bp = Blueprint("pages", __name__)

# @bp.route("/")
# def home():
#     return "Hello, Home!"

# @bp.route("/about")
# def about():
#     return "Hello, About!"

from flask import Blueprint, render_template

bp = Blueprint("pages", __name__)

@bp.route("/")
def home():
    return render_template("home.html")

@bp.route("/about")
def about():
    return render_template("about.html")
