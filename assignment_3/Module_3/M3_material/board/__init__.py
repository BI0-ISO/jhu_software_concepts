from flask import Blueprint

# Point templates to M3_material/templates
bp = Blueprint("m3_pages", __name__, template_folder="../templates")  # unique name for Module 3
from M3_material.board import pages
