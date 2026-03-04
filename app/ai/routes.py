from flask import jsonify, render_template
from flask_login import current_user, login_required
from flask_jwt_extended import create_access_token

from app.decorators import role_required
from app.models.ai_analysis import AiAnalysis
from app.models.machine import Machine
from app.security import get_active_company_id, dev_show_all_data_enabled
from app.utils.markdown_renderer import render_markdown
from . import ai_bp


def _get_machine_or_404(machine_id: int) -> Machine:
    company_id = get_active_company_id()
    return Machine.query.filter_by(id=machine_id, company_id=company_id).first_or_404()


@ai_bp.route("/<int:machine_id>")
@login_required
@role_required("admin", "manager", "viewer")
def ai_insights(machine_id: int):
    machine = _get_machine_or_404(machine_id)
    return render_template("ai/insights.html", machine=machine)


@ai_bp.route("/<int:machine_id>/latest")
@login_required
@role_required("admin", "manager", "viewer")
def ai_latest(machine_id: int):
    machine = _get_machine_or_404(machine_id)
    latest = (
        AiAnalysis.query.filter_by(machine_id=machine.id)
        .order_by(AiAnalysis.created_at.desc())
        .first()
    )
    if not latest:
        return jsonify({"status": "pending", "message": "No AI analysis yet."})

    maintenance_html = str(render_markdown(latest.maintenance_suggestion or ""))
    explanation_html = str(render_markdown(latest.explanation or ""))

    return jsonify(
        {
            "status": latest.status,
            "machine_id": machine.id,
            "health_score": latest.health_score,
            "risk_level": latest.risk_level,
            "anomaly": latest.anomaly,
            "maintenance_suggestion": latest.maintenance_suggestion,
            "maintenance_suggestion_html": maintenance_html,
            "explanation": latest.explanation,
            "explanation_html": explanation_html,
            "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
            "created_at": latest.created_at.isoformat() if latest.created_at else None,
        }
    )


@ai_bp.route("/dashboard")
@login_required
@role_required("ADMIN", "MANAGER", "VIEWER", "PLANT_MANAGER", "MAINTENANCE_HEAD", "TECHNICIAN", "SUPER_ADMIN", "ENTERPRISE_ADMIN")
def ai_dashboard():
    company_id = get_active_company_id() or current_user.company_id
    machines_query = Machine.query.filter_by(company_id=company_id)
    if not dev_show_all_data_enabled():
        role = (current_user.active_role or current_user.role or "").upper()
        if role not in {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN"}:
            mapping_ids = {m.plant_id for m in current_user.plant_mappings}
            machines_query = machines_query.filter(Machine.plant_id.in_(mapping_ids))
    machines = machines_query.order_by(Machine.machine_name.asc()).all()
    access_token = create_access_token(identity=str(current_user.id))
    return render_template(
        "dashboard/ai_dashboard.html",
        machines=machines,
        access_token=access_token,
        active_company_id=company_id,
    )
