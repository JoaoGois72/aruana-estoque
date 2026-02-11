from flask import Blueprint

estoque_bp = Blueprint('estoque', __name__)

from . import routes  # noqa
