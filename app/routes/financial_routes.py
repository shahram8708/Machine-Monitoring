from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from app.audit import log_action
from app.decorators import rate_limit
from app.extensions import csrf
from app.models import Machine
from app.services.financial_service import cost_to_failure, projected_downtime_cost
from app.api.management_routes import _resolve_user, _user_role, _check_company_access, _check_plant_access


financial_bp = Blueprint("financial", __name__, url_prefix="/api/financial")

_ALLOWED_ROLES = {
    "SUPER_ADMIN",
    "ENTERPRISE_ADMIN",
    "ADMIN",
    "MANAGER",
    "PLANT_MANAGER",
    "MAINTENANCE_HEAD",
}


def _guard(machine: Machine, user):
    role = _user_role(user)
    if role not in _ALLOWED_ROLES:
        return False
    _check_company_access(user, machine.company_id)
    if machine.plant_id:
        _check_plant_access(user, machine.plant_id)
    return True


@financial_bp.route("/forecast/<int:machine_id>", methods=["GET"])
@csrf.exempt
@jwt_required()
@rate_limit()
def forecast(machine_id: int):
    user = _resolve_user()
    machine = Machine.query.get_or_404(machine_id)
    _guard(machine, user)

    downtime_projection = projected_downtime_cost(machine.id, machine.company_id)
    risk = cost_to_failure(machine.id, machine.company_id)

    payload = {
        "projected_downtime_cost": downtime_projection.get("projected_downtime_cost"),
        "projected_revenue_loss": downtime_projection.get("projected_revenue_loss"),
        "total_risk_exposure": risk.get("total_risk_exposure"),
        "confidence": risk.get("confidence", 0),
    }
    log_action("financial_forecast_view", "financial", machine.id, company_id=machine.company_id, plant_id=machine.plant_id)
    return jsonify(payload)
