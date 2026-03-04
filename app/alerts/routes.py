from flask import jsonify, redirect, render_template, request, url_for, flash
from flask_login import login_required, current_user

from app.decorators import role_required
from app.models.alert import Alert
from app.security import get_active_company_id
from app.services.alert_service import resolve_alert
from . import alerts_bp


@alerts_bp.route("/")
@login_required
@role_required("admin", "manager", "viewer")
def list_alerts():
    company_id = get_active_company_id()
    page = request.args.get("page", 1, type=int)
    pagination = (
        Alert.query.filter_by(company_id=company_id)
        .order_by(Alert.created_at.desc())
        .paginate(page=page, per_page=15, error_out=False)
    )
    alerts = pagination.items
    return render_template("alerts/list.html", alerts=alerts, pagination=pagination)


@alerts_bp.route("/<int:alert_id>/resolve", methods=["POST"])
@login_required
@role_required("admin", "manager")
def resolve(alert_id: int):
    company_id = get_active_company_id()
    alert = Alert.query.filter_by(id=alert_id, company_id=company_id).first_or_404()
    resolve_alert(alert.id, current_user)
    flash("Alert marked as resolved.", "success")
    next_url = request.referrer or url_for("alerts.list_alerts")
    return redirect(next_url)


@alerts_bp.route("/unread")
@login_required
@role_required("admin", "manager", "viewer")
def unread_api():
    company_id = get_active_company_id()
    recent = (
        Alert.query.filter_by(company_id=company_id, is_resolved=False)
        .order_by(Alert.created_at.desc())
        .limit(5)
        .all()
    )
    return jsonify(
        {
            "count": Alert.query.filter_by(company_id=company_id, is_resolved=False).count(),
            "recent": [
                {
                    "id": alert.id,
                    "machine": alert.machine.machine_name,
                    "severity": alert.severity,
                    "sensor_type": alert.sensor_type,
                    "message": alert.message,
                    "created_at": alert.created_at.isoformat(),
                }
                for alert in recent
            ],
        }
    )
