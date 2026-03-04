from __future__ import annotations

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import jwt_required

from app.audit import log_action
from app.decorators import rate_limit
from app.extensions import csrf
from app.services.advanced_analytics_service import (
    analytics_summary,
    correlation,
    distribution,
    esg,
    financial,
    parse_filters,
    predictive,
    risk,
    time_series,
    twin,
    workforce,
    paginated_response,
)
from app.api.management_routes import _resolve_user, _user_role, _check_company_access, _check_plant_access

advanced_analytics_bp = Blueprint("advanced_analytics", __name__, url_prefix="/api/analytics")

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


def _authorize(user, filters):
    role = _user_role(user)
    if role not in _ALLOWED_ROLES:
        return False
    _check_company_access(user, filters["company_id"])
    if filters["plant_ids"]:
        for pid in filters["plant_ids"]:
            _check_plant_access(user, pid)
    return True


@advanced_analytics_bp.route("/summary", methods=["GET"])
@csrf.exempt
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def summary():
    user = _resolve_user()
    filters = parse_filters(request.args, user)
    if not _authorize(user, filters):
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    payload = analytics_summary(filters)
    log_action("analytics_summary_view", "analytics", user.id, company_id=filters["company_id"])
    return jsonify(paginated_response(filters, payload))


@advanced_analytics_bp.route("/time-series", methods=["GET"])
@csrf.exempt
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def time_series_view():
    user = _resolve_user()
    filters = parse_filters(request.args, user)
    if not _authorize(user, filters):
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    payload = time_series(filters)
    log_action("analytics_time_series", "analytics", user.id, company_id=filters["company_id"])
    return jsonify(paginated_response(filters, payload))


@advanced_analytics_bp.route("/distribution", methods=["GET"])
@csrf.exempt
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def distribution_view():
    user = _resolve_user()
    filters = parse_filters(request.args, user)
    if not _authorize(user, filters):
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    payload = distribution(filters)
    log_action("analytics_distribution", "analytics", user.id, company_id=filters["company_id"])
    return jsonify(paginated_response(filters, payload))


@advanced_analytics_bp.route("/correlation", methods=["GET"])
@csrf.exempt
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def correlation_view():
    user = _resolve_user()
    filters = parse_filters(request.args, user)
    if not _authorize(user, filters):
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    payload = correlation(filters)
    log_action("analytics_correlation", "analytics", user.id, company_id=filters["company_id"])
    return jsonify(paginated_response(filters, payload))


@advanced_analytics_bp.route("/financial", methods=["GET"])
@csrf.exempt
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def financial_view():
    user = _resolve_user()
    filters = parse_filters(request.args, user)
    if not _authorize(user, filters):
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    payload = financial(filters)
    log_action("analytics_financial", "analytics", user.id, company_id=filters["company_id"])
    return jsonify(paginated_response(filters, payload))


@advanced_analytics_bp.route("/workforce", methods=["GET"])
@csrf.exempt
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def workforce_view():
    user = _resolve_user()
    filters = parse_filters(request.args, user)
    if not _authorize(user, filters):
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    payload = workforce(filters)
    log_action("analytics_workforce", "analytics", user.id, company_id=filters["company_id"])
    return jsonify(paginated_response(filters, payload))


@advanced_analytics_bp.route("/esg", methods=["GET"])
@csrf.exempt
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def esg_view():
    user = _resolve_user()
    filters = parse_filters(request.args, user)
    if not _authorize(user, filters):
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    payload = esg(filters)
    log_action("analytics_esg", "analytics", user.id, company_id=filters["company_id"])
    return jsonify(paginated_response(filters, payload))


@advanced_analytics_bp.route("/predictive", methods=["GET"])
@csrf.exempt
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def predictive_view():
    user = _resolve_user()
    filters = parse_filters(request.args, user)
    if not _authorize(user, filters):
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    payload = predictive(filters)
    log_action("analytics_predictive", "analytics", user.id, company_id=filters["company_id"])
    return jsonify(paginated_response(filters, payload))


@advanced_analytics_bp.route("/twin", methods=["GET"])
@csrf.exempt
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def twin_view():
    user = _resolve_user()
    filters = parse_filters(request.args, user)
    if not _authorize(user, filters):
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    payload = twin(filters)
    log_action("analytics_twin", "analytics", user.id, company_id=filters["company_id"])
    return jsonify(paginated_response(filters, payload))


@advanced_analytics_bp.route("/risk", methods=["GET"])
@csrf.exempt
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def risk_view():
    user = _resolve_user()
    filters = parse_filters(request.args, user)
    if not _authorize(user, filters):
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    payload = risk(filters)
    log_action("analytics_risk", "analytics", user.id, company_id=filters["company_id"])
    return jsonify(paginated_response(filters, payload))


@advanced_analytics_bp.route("/export/json", methods=["GET"])
@csrf.exempt
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def export_json():
    user = _resolve_user()
    filters = parse_filters(request.args, user)
    if not _authorize(user, filters):
        return jsonify({"status": "error", "message": "Forbidden"}), 403
    payload = analytics_summary(filters)
    log_action("analytics_export_json", "analytics", user.id, company_id=filters["company_id"])
    return jsonify(payload)
