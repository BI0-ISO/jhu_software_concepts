"""Blueprint registration for Module 1 pages."""

# pylint: disable=wrong-import-position,cyclic-import

from flask import Blueprint

# Point templates to M1_material/templates and use a unique blueprint name.
bp = Blueprint("m1_pages", __name__, template_folder="../templates")

# Import routes after blueprint creation to avoid circular imports.
from M1_material.board import pages
