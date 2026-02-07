from flask import Blueprint

# Point templates to M1_material/templates
bp = Blueprint("m1_pages", __name__, template_folder="../templates")  # unique name for Module 1
from M1_material.board import pages
