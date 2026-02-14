from flask import Blueprint

machines_bp = Blueprint("machines", __name__, url_prefix="/machines")

from . import routes  # noqa: E402,F401
