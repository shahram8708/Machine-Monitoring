from flask import abort, jsonify, request
from flask_jwt_extended import jwt_required

from app.audit import log_action
from app.decorators import rate_limit
from app.extensions import csrf
from app.models import Machine
from app.services.predictive_service import (
    history,
    latest_prediction,
    plant_summary,
    run_prediction,
)
from .management_routes import _resolve_user, _user_role, _check_company_access, _check_plant_access
from . import api_bp


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


def _assert_role(user):
    role = _user_role(user)
    if role not in _ALLOWED_ROLES:
        abort(403)
    return role


def _serialize(prediction):
    return {
        "id": prediction.id,
        "machine_id": prediction.machine_id,
        "plant_id": prediction.plant_id,
        "company_id": prediction.company_id,
        "failure_probability": prediction.failure_probability,
        "remaining_useful_life_hours": prediction.remaining_useful_life_hours,
        "degradation_score": prediction.degradation_score,
        "anomaly_score": prediction.anomaly_score,
        "risk_level": prediction.risk_level,
        "early_warning_flag": prediction.early_warning_flag,
        "ai_explanation": prediction.ai_explanation,
        "confidence_score": prediction.confidence_score,
        "created_at": prediction.created_at.isoformat() if prediction.created_at else None,
    }


@api_bp.route("/ai/prediction/machine/<int:machine_id>", methods=["GET", "POST"])
@csrf.exempt
@jwt_required()
@rate_limit()
def prediction_latest(machine_id: int):
    user = _resolve_user()
    _assert_role(user)
    machine = Machine.query.get_or_404(machine_id)
    _check_company_access(user, machine.company_id)
    if machine.plant_id:
        _check_plant_access(user, machine.plant_id)

    force = request.method == "POST" or request.args.get("run") == "1"
    pred = latest_prediction(machine.id, machine.company_id)
    if not pred or force:
        try:
            pred = run_prediction(machine)
        except Exception as exc:  # noqa: BLE001
            return jsonify({"status": "error", "message": "AI prediction failed", "detail": str(exc)}), 500

    log_action("ai_prediction_view", "ai_prediction", pred.id, company_id=machine.company_id, plant_id=machine.plant_id)
    return jsonify(_serialize(pred))


@api_bp.route("/ai/prediction/history/<int:machine_id>", methods=["GET"])
@jwt_required()
@rate_limit()
def prediction_history(machine_id: int):
    user = _resolve_user()
    _assert_role(user)
    machine = Machine.query.get_or_404(machine_id)
    _check_company_access(user, machine.company_id)
    if machine.plant_id:
        _check_plant_access(user, machine.plant_id)

    trend = history(machine.id, machine.company_id)
    return jsonify({"machine_id": machine.id, "history": trend})


@api_bp.route("/ai/prediction/plant-summary", methods=["GET"])
@jwt_required()
@rate_limit()
def prediction_plant_summary():
    user = _resolve_user()
    role = _assert_role(user)
    company_id = int(request.args.get("company_id") or user.company_id)
    _check_company_access(user, company_id)

    plant_ids = None
    if role not in {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN"}:
        plant_ids = [m.plant_id for m in user.plant_mappings]
    summary = plant_summary(company_id, plant_ids)
    return jsonify({"company_id": company_id, "plants": summary})
