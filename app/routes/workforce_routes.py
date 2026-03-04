from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.audit import log_action
from app.decorators import rate_limit
from app.extensions import csrf
from app.services.workforce_service import analytics_overview, technician_detail, workload_balance
from app.api.management_routes import _resolve_user, _user_role, _check_company_access


workforce_bp = Blueprint("workforce", __name__, url_prefix="/api/workforce")

_ALLOWED_ROLES = {
    "SUPER_ADMIN",
    "ENTERPRISE_ADMIN",
    "ADMIN",
    "MANAGER",
    "PLANT_MANAGER",
    "MAINTENANCE_HEAD",
}


def _plant_scope(user):
    role = _user_role(user)
    if role in {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN"}:
        return None
    return [m.plant_id for m in user.plant_mappings]


@workforce_bp.route("/analytics", methods=["GET"])
@csrf.exempt
@jwt_required()
@rate_limit()
def analytics():
    user = _resolve_user()
    if _user_role(user) not in _ALLOWED_ROLES:
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    company_id = int(request.args.get("company_id") or user.company_id)
    _check_company_access(user, company_id)

    data = analytics_overview(company_id, _plant_scope(user))
    log_action("workforce_analytics_view", "workforce", user.id, company_id=company_id)
    return jsonify(data)


@workforce_bp.route("/technician/<int:tech_id>", methods=["GET"])
@csrf.exempt
@jwt_required()
@rate_limit()
def technician(tech_id: int):
    user = _resolve_user()
    company_id = int(request.args.get("company_id") or user.company_id)
    _check_company_access(user, company_id)
    data = technician_detail(tech_id)
    log_action("technician_view", "workforce", tech_id, company_id=company_id)
    return jsonify(data)


@workforce_bp.route("/workload-balance", methods=["GET"])
@csrf.exempt
@jwt_required()
@rate_limit()
def balance():
    user = _resolve_user()
    company_id = int(request.args.get("company_id") or user.company_id)
    _check_company_access(user, company_id)

    data = workload_balance(company_id, _plant_scope(user))
    log_action("workload_balance_view", "workforce", user.id, company_id=company_id)
    return jsonify(data)
