from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from app.audit import log_action
from app.decorators import rate_limit
from app.extensions import csrf
from app.models import Machine
from app.services.esg_service import esg_summary
from app.api.management_routes import _resolve_user, _user_role, _check_company_access, _check_plant_access


esg_bp = Blueprint("esg", __name__, url_prefix="/api/esg")

_ALLOWED_ROLES = {
    "SUPER_ADMIN",
    "ENTERPRISE_ADMIN",
    "ADMIN",
    "MANAGER",
    "PLANT_MANAGER",
    "MAINTENANCE_HEAD",
    "VIEWER",
}


def _guard(machine: Machine, user):
    role = _user_role(user)
    if role not in _ALLOWED_ROLES:
        return False
    _check_company_access(user, machine.company_id)
    if machine.plant_id:
        _check_plant_access(user, machine.plant_id)
    return True


@esg_bp.route("/metrics/<int:machine_id>", methods=["GET"])
@csrf.exempt
@jwt_required()
@rate_limit()
def metrics(machine_id: int):
    user = _resolve_user()
    machine = Machine.query.get_or_404(machine_id)
    _guard(machine, user)

    data = esg_summary(machine.id, machine.company_id)
    log_action("esg_metrics_view", "esg", machine.id, company_id=machine.company_id, plant_id=machine.plant_id)
    return jsonify(data)
