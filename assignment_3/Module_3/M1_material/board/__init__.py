"""Blueprint registration for Module 1 pages."""

from flask import Blueprint

# Point templates to M1_material/templates and use a unique blueprint name.
bp = Blueprint("m1_pages", __name__, template_folder="../templates")
from M1_material.board import pages
