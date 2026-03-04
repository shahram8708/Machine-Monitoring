from __future__ import annotations

from flask import jsonify, abort
from flask_jwt_extended import jwt_required

from app.audit import log_action
from app.decorators import rate_limit
from app.models import AlertGroup
from app.services import rca_service
from .management_routes import _resolve_user, _user_role, _check_company_access, _check_plant_access
from . import api_bp

_ALLOWED_ROLES = {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN", "PLANT_MANAGER", "MAINTENANCE_HEAD", "TECHNICIAN", "MANAGER", "VIEWER"}


def _ensure_group_access(user, group: AlertGroup):
    _check_company_access(user, group.machine.company_id)
    if group.machine.plant_id:
        _check_plant_access(user, group.machine.plant_id)
    if _user_role(user) not in _ALLOWED_ROLES:
        abort(403)


@api_bp.route("/rca/<int:machine_id>", methods=["GET"])
# Allow session users or JWT via headers; avoid cookie CSRF 422s.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def latest_rca(machine_id: int):
    user = _resolve_user()
    rca = rca_service.latest_rca_for_machine(machine_id)
    if not rca:
        abort(404)
    machine = rca.machine
    _check_company_access(user, machine.company_id)
    if machine.plant_id:
        _check_plant_access(user, machine.plant_id)
    if _user_role(user) not in _ALLOWED_ROLES:
        abort(403)
    log_action("rca_view", "root_cause_analysis", rca.id, company_id=machine.company_id, plant_id=machine.plant_id)
    return jsonify(_serialize_rca(rca))


@api_bp.route("/rca/group/<int:alert_group_id>", methods=["GET"])
# Allow session users or JWT via headers; avoid cookie CSRF 422s.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def rca_by_group(alert_group_id: int):
    user = _resolve_user()
    group = AlertGroup.query.get_or_404(alert_group_id)
    _ensure_group_access(user, group)
    rca = rca_service.rca_for_group(alert_group_id)
    if not rca:
        rca = rca_service.perform_root_cause_analysis(alert_group_id)
    log_action("rca_view_group", "root_cause_analysis", rca.id, company_id=group.machine.company_id, plant_id=group.machine.plant_id)
    return jsonify(_serialize_rca(rca))


def _serialize_rca(rca):
    return {
        "id": rca.id,
        "machine_id": rca.machine_id,
        "alert_group_id": rca.alert_group_id,
        "primary_root_cause": rca.primary_root_cause,
        "contributing_factors": rca.contributing_factors,
        "probability_breakdown": rca.probability_breakdown,
        "timeline_explanation": rca.timeline_explanation,
        "sensor_interactions": rca.sensor_interactions,
        "confidence_score": rca.confidence_score,
        "created_at": rca.created_at.isoformat(),
    }
