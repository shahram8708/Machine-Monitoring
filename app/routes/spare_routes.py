from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.audit import log_action
from app.decorators import rate_limit
from app.extensions import csrf
from app.models import Machine
from app.services.spare_parts_service import inventory_view, predict_for_machine, recommendation_summary
from app.api.management_routes import _resolve_user, _user_role, _check_company_access, _check_plant_access


spare_bp = Blueprint("spare", __name__, url_prefix="/api/spare-parts")

_ALLOWED_ROLES = {
    "SUPER_ADMIN",
    "ENTERPRISE_ADMIN",
    "ADMIN",
    "MANAGER",
    "PLANT_MANAGER",
    "MAINTENANCE_HEAD",
    "TECHNICIAN",
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


@spare_bp.route("/predict/<int:machine_id>", methods=["GET"])
@csrf.exempt
@jwt_required()
@rate_limit()
def predict(machine_id: int):
    user = _resolve_user()
    machine = Machine.query.get_or_404(machine_id)
    _guard(machine, user)

    result = predict_for_machine(machine.id, machine.company_id)
    log_action("spare_prediction_view", "spare_part", machine.id, company_id=machine.company_id, plant_id=machine.plant_id)
    return jsonify(result)


@spare_bp.route("/inventory", methods=["GET"])
@csrf.exempt
@jwt_required()
@rate_limit()
def inventory():
    user = _resolve_user()
    role = _user_role(user)
    company_id = int(request.args.get("company_id") or user.company_id)
    _check_company_access(user, company_id)

    plant_ids = None
    if role not in {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN"}:
        plant_ids = [m.plant_id for m in user.plant_mappings]

    data = inventory_view(company_id, plant_ids)
    log_action("spare_inventory_view", "spare_inventory", user.id, company_id=company_id)
    return jsonify({"items": data})


@spare_bp.route("/recommendation-summary", methods=["GET"])
@csrf.exempt
@jwt_required()
@rate_limit()
def summary():
    user = _resolve_user()
    role = _user_role(user)
    company_id = int(request.args.get("company_id") or user.company_id)
    _check_company_access(user, company_id)

    plant_ids = None
    if role not in {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN"}:
        plant_ids = [m.plant_id for m in user.plant_mappings]

    data = recommendation_summary(company_id, plant_ids)
    log_action("spare_recommendation_summary", "spare_part", user.id, company_id=company_id)
    return jsonify(data)
