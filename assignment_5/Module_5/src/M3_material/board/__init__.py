"""Blueprint registration for Module 3 pages."""

# pylint: disable=wrong-import-position,cyclic-import

from flask import Blueprint

# Point templates to M3_material/templates and use a unique blueprint name.
bp = Blueprint("m3_pages", __name__, template_folder="../templates")

# Import routes after blueprint creation to avoid circular imports.
from M3_material.board import pages
