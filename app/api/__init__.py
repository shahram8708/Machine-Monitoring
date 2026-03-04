from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

from . import routes  # noqa: E402,F401
from . import management_routes  # noqa: E402,F401
from . import kpi_routes  # noqa: E402,F401
from . import ai_routes  # noqa: E402,F401
from . import alert_routes  # noqa: E402,F401
from . import rca_routes  # noqa: E402,F401
from . import twin_routes  # noqa: E402,F401
