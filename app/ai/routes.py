from flask import jsonify, render_template
from flask_login import current_user, login_required

from app.decorators import role_required
from app.models.ai_analysis import AiAnalysis
from app.models.machine import Machine
from app.security import get_active_company_id
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

    return jsonify(
        {
            "status": latest.status,
            "machine_id": machine.id,
            "health_score": latest.health_score,
            "risk_level": latest.risk_level,
            "anomaly": latest.anomaly,
            "maintenance_suggestion": latest.maintenance_suggestion,
            "explanation": latest.explanation,
            "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
            "created_at": latest.created_at.isoformat() if latest.created_at else None,
        }
    )
