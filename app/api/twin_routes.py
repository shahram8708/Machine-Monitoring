from dataclasses import asdict
from flask import jsonify, request, abort
from flask_jwt_extended import jwt_required

from app.audit import log_action
from app.decorators import rate_limit
from app.extensions import csrf, db
from app.models import Machine, TwinSimulationHistory
from app.services.simulation_engine import run_simulation
from app.services.twin_service import (
    fetch_history,
    generate_baseline,
    get_or_create_twin,
    record_simulation,
    serialize_history,
    serialize_twin,
)
from app.services.whatif_service import run_what_if_analysis
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


def _load_machine(machine_id: int, user):
    machine = Machine.query.get_or_404(machine_id)
    _check_company_access(user, machine.company_id)
    if machine.plant_id:
        _check_plant_access(user, machine.plant_id)
    return machine


def _validate_sim_params(payload: dict) -> dict:
    def _num(key, default=0.0, min_val=None, max_val=None):
        val = payload.get(key, default)
        try:
            num = float(val)
        except (TypeError, ValueError):
            abort(400)
        if min_val is not None and num < min_val:
            abort(400)
        if max_val is not None and num > max_val:
            abort(400)
        return num

    return {
        "load_pct": _num("load_pct", 0.0, -50.0, 200.0),
        "production_pct": _num("production_pct", 0.0, -25.0, 200.0),
        "sensor_drift_pct": _num("sensor_drift_pct", 0.0, -50.0, 100.0),
        "manual_risk_adjustment": _num("manual_risk_adjustment", 0.0, -50.0, 50.0),
        "simulation_type": str(payload.get("simulation_type", "composite") or "composite").strip()[:64],
    }


@api_bp.route("/twin/<int:machine_id>", methods=["GET"])
@jwt_required()
@rate_limit()
def get_twin(machine_id: int):
    user = _resolve_user()
    _assert_role(user)
    machine = _load_machine(machine_id, user)
    twin = get_or_create_twin(machine)
    return jsonify(serialize_twin(twin))


@api_bp.route("/twin/<int:machine_id>/generate-baseline", methods=["POST"])
@csrf.exempt
@jwt_required()
@rate_limit()
def generate_baseline_api(machine_id: int):
    user = _resolve_user()
    _assert_role(user)
    machine = _load_machine(machine_id, user)
    twin = generate_baseline(machine)
    log_action("twin_baseline_generated", "digital_twin", twin.id, company_id=machine.company_id, plant_id=machine.plant_id)
    return jsonify(serialize_twin(twin)), 201


@api_bp.route("/twin/<int:machine_id>/simulate", methods=["POST"])
@csrf.exempt
@jwt_required()
@rate_limit()
def simulate_twin(machine_id: int):
    user = _resolve_user()
    _assert_role(user)
    machine = _load_machine(machine_id, user)
    twin = get_or_create_twin(machine)

    payload = request.get_json(silent=True) or {}
    params = _validate_sim_params(payload)
    result = run_simulation(twin, params, simulation_type=params.pop("simulation_type", "composite"))
    history = record_simulation(twin, payload.get("simulation_type", "composite") or "composite", params, asdict(result))
    log_action("twin_simulated", "digital_twin", twin.id, new_value=params, company_id=machine.company_id, plant_id=machine.plant_id)
    return jsonify({"twin": serialize_twin(twin), "simulation": serialize_history(history)})


@api_bp.route("/twin/<int:machine_id>/history", methods=["GET"])
@jwt_required()
@rate_limit()
def twin_history(machine_id: int):
    user = _resolve_user()
    _assert_role(user)
    machine = _load_machine(machine_id, user)
    twin = get_or_create_twin(machine)
    page = int(request.args.get("page", 1))
    per_page = min(100, int(request.args.get("per_page", 25)))
    history, total = fetch_history(twin, page=page, per_page=per_page)
    return jsonify({"items": history, "total": total, "page": page, "per_page": per_page})


@api_bp.route("/twin/<int:machine_id>/whatif", methods=["POST"])
@csrf.exempt
@jwt_required()
@rate_limit()
def twin_what_if(machine_id: int):
    user = _resolve_user()
    _assert_role(user)
    machine = _load_machine(machine_id, user)
    twin = get_or_create_twin(machine)

    payload = request.get_json(silent=True) or {}
    history_id = payload.get("history_id")
    history = None
    if history_id:
        history = TwinSimulationHistory.query.filter_by(id=history_id, digital_twin_id=twin.id).first()
    else:
        history = twin.simulations.order_by(TwinSimulationHistory.created_at.desc()).first()
    if not history:
        return jsonify({"status": "error", "message": "No simulation history available"}), 404

    simulation_result = serialize_history(history)
    try:
        analysis = run_what_if_analysis(twin, simulation_result)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"status": "error", "message": "AI what-if analysis failed", "detail": str(exc)}), 500

    history.ai_analysis = analysis
    db.session.add(history)
    db.session.commit()

    log_action(
        "twin_what_if",
        "digital_twin",
        twin.id,
        new_value={"history_id": history.id, "analysis": analysis},
        company_id=machine.company_id,
        plant_id=machine.plant_id,
    )
    return jsonify({"history_id": history.id, "ai_analysis": analysis})
