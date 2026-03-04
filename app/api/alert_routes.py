from __future__ import annotations

from datetime import datetime, timedelta
from collections import defaultdict
from flask import jsonify, request, abort
from flask_jwt_extended import jwt_required

from app.audit import log_action
from app.decorators import rate_limit
from app.models import Alert
from app.services import alert_service
from app.services.alert_service import sla_status
from .management_routes import _resolve_user, _user_role, _check_company_access, _check_plant_access
from . import api_bp


_ALLOWED_ROLES = {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN", "PLANT_MANAGER", "MAINTENANCE_HEAD", "TECHNICIAN", "MANAGER", "VIEWER"}


def _ensure_access(user, alert: Alert):
    _check_company_access(user, alert.company_id)
    if alert.plant_id:
        _check_plant_access(user, alert.plant_id)
    role = _user_role(user)
    if role not in _ALLOWED_ROLES:
        abort(403)


@api_bp.route("/alerts/unread", methods=["GET"])
# Allow session users or JWT via headers to avoid CSRF cookie checks.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def unread_alerts_api():
    user = _resolve_user()
    role = _user_role(user)
    if role not in _ALLOWED_ROLES:
        abort(403)

    plant_id = request.args.get("plant_id", type=int)
    if plant_id:
        _check_plant_access(user, plant_id)

    base = Alert.query.filter_by(company_id=user.company_id, is_resolved=False)
    if plant_id:
        base = base.filter_by(plant_id=plant_id)

    count = base.count()
    recent = base.order_by(Alert.created_at.desc()).limit(5).all()

    return jsonify(
        {
            "count": count,
            "recent": [
                {
                    "id": alert.id,
                    "machine": alert.machine.machine_name if alert.machine else None,
                    "severity": alert.severity,
                    "sensor_type": alert.sensor_type,
                    "message": alert.message,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None,
                }
                for alert in recent
            ],
        }
    )


@api_bp.route("/alerts", methods=["GET"])
# Allow session users or JWT via headers to avoid CSRF cookie checks.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def list_alerts_api():
    user = _resolve_user()
    role = _user_role(user)
    if role not in _ALLOWED_ROLES:
        abort(403)
    plant_id = request.args.get("plant_id", type=int)
    status = request.args.get("status")
    severity = request.args.get("severity")
    grouped_alert_id = request.args.get("group_id", type=int)
    page = request.args.get("page", type=int)
    per_page = request.args.get("per_page", type=int)
    alerts = alert_service.list_alerts(
        user.company_id,
        plant_id=plant_id,
        status=status,
        severity=severity,
        grouped_alert_id=grouped_alert_id,
        page=page,
        per_page=per_page,
    )
    return jsonify([
        {
            "id": a.id,
            "machine_id": a.machine_id,
            "plant_id": a.plant_id,
            "alert_type": a.alert_type,
            "severity": a.severity,
            "status": a.status,
            "priority_score": a.priority_score,
            "created_at": a.created_at.isoformat(),
            "sla_deadline": a.sla_deadline.isoformat() if a.sla_deadline else None,
            "grouped_alert_id": a.grouped_alert_id,
        }
        for a in alerts
    ])


@api_bp.route("/alerts/<int:alert_id>", methods=["GET"])
# Allow session users or JWT via headers to avoid CSRF cookie checks.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def alert_detail_api(alert_id: int):
    user = _resolve_user()
    alert = alert_service.alert_detail(alert_id)
    _ensure_access(user, alert)
    return jsonify(
        {
            "id": alert.id,
            "machine_id": alert.machine_id,
            "plant_id": alert.plant_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "status": alert.status,
            "priority_score": alert.priority_score,
            "message": alert.message,
            "grouped_alert_id": alert.grouped_alert_id,
            "sla_deadline": alert.sla_deadline.isoformat() if alert.sla_deadline else None,
            "created_at": alert.created_at.isoformat(),
            "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        }
    )


@api_bp.route("/alerts/<int:alert_id>/acknowledge", methods=["POST"])
# Allow session users or JWT via headers to avoid CSRF cookie checks.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def acknowledge_alert_api(alert_id: int):
    user = _resolve_user()
    alert = alert_service.alert_detail(alert_id)
    _ensure_access(user, alert)
    updated = alert_service.acknowledge_alert(alert_id, user)
    log_action("alert_ack", "alert", alert_id, company_id=updated.company_id, plant_id=updated.plant_id)
    return jsonify({"status": "acknowledged", "response_time_minutes": updated.response_time_minutes})


@api_bp.route("/alerts/<int:alert_id>/resolve", methods=["POST"])
# Allow session users or JWT via headers to avoid CSRF cookie checks.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def resolve_alert_api(alert_id: int):
    user = _resolve_user()
    alert = alert_service.alert_detail(alert_id)
    _ensure_access(user, alert)
    updated = alert_service.resolve_alert(alert_id, user)
    log_action("alert_resolve", "alert", alert_id, company_id=updated.company_id, plant_id=updated.plant_id)
    return jsonify({"status": "resolved", "response_time_minutes": updated.response_time_minutes})


@api_bp.route("/alerts/sla-status", methods=["GET"])
# Allow session users or JWT via headers to avoid CSRF cookie checks.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def alert_sla_status_api():
    user = _resolve_user()
    alert_id = request.args.get("alert_id", type=int)
    if not alert_id:
        abort(400)
    alert = alert_service.alert_detail(alert_id)
    _ensure_access(user, alert)
    status_payload = sla_status(alert_id)
    if status_payload["breached"]:
        log_action("alert_sla_breach", "alert", alert_id, company_id=alert.company_id, plant_id=alert.plant_id)
    return jsonify(status_payload)


@api_bp.route("/alerts/analytics", methods=["GET"])
# Allow session users or JWT via headers to avoid CSRF cookie checks.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def alert_analytics_api():
    user = _resolve_user()
    role = _user_role(user)
    if role not in _ALLOWED_ROLES:
        abort(403)
    plant_id = request.args.get("plant_id", type=int)
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    start_date = None
    end_date = None
    try:
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str)
        if end_date_str:
            # include full end day by pushing to end-of-day
            end_date = datetime.fromisoformat(end_date_str) + timedelta(days=1, seconds=-1)
    except ValueError:
        # ignore bad date formats and fall back to no date filter
        start_date = None
        end_date = None

    alerts = alert_service.list_alerts(user.company_id, plant_id=plant_id, start_date=start_date, end_date=end_date)

    response_times = [a.response_time_minutes for a in alerts if a.response_time_minutes]
    avg_response = sum(response_times) / len(response_times) if response_times else 0

    now = datetime.utcnow()
    sla_breaches = [a for a in alerts if a.sla_deadline and a.sla_deadline < now and a.status not in {"RESOLVED", "ACKNOWLEDGED"}]
    open_alerts = [a for a in alerts if a.status not in {"RESOLVED"}]

    technicians = defaultdict(int)
    for a in alerts:
        if a.resolved_by_user_id:
            technicians[a.resolved_by_user_id] += 1

    severity_distribution = defaultdict(int)
    alerts_per_day = defaultdict(int)
    escalation_frequency = defaultdict(int)
    heatmap = defaultdict(int)
    resolution_minutes = []

    for a in alerts:
        day_key = a.created_at.date().isoformat() if a.created_at else "unknown"
        alerts_per_day[day_key] += 1
        severity_distribution[(a.severity or "UNKNOWN").upper()] += 1
        escalation_frequency[a.escalation_level or 0] += 1
        if a.created_at:
            heatmap[(a.created_at.date().isoformat(), a.created_at.hour)] += 1
        if a.resolved_at and a.created_at:
            delta = (a.resolved_at - a.created_at).total_seconds() / 60
            if delta >= 0:
                resolution_minutes.append(delta)

    avg_resolution_minutes = sum(resolution_minutes) / len(resolution_minutes) if resolution_minutes else 0
    resolved_count = len([a for a in alerts if a.status == "RESOLVED"])

    return jsonify(
        {
            "average_response_time_minutes": round(avg_response, 2),
            "average_resolution_minutes": round(avg_resolution_minutes, 2),
            "sla_breach_count": len(sla_breaches),
            "technician_performance": dict(technicians),
            "total_alerts": len(alerts),
            "open_alerts": len(open_alerts),
            "alerts_per_day": [{"date": k, "count": v} for k, v in sorted(alerts_per_day.items())],
            "severity_distribution": dict(severity_distribution),
            "escalation_frequency": dict(escalation_frequency),
            "heatmap": [
                {"date": d, "hour": h, "count": c} for (d, h), c in heatmap.items()
            ],
            "sla_compliance": {
                "resolved": resolved_count,
                "breached": len(sla_breaches),
                "open": len(open_alerts),
            },
        }
    )
