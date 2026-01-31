
from flask import Blueprint

bp = Blueprint("pages", __name__)

from Module_1.board import pages  # noqa
