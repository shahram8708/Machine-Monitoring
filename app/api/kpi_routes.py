from datetime import date, datetime, timedelta
from flask import jsonify, abort
from flask_jwt_extended import jwt_required
from app.audit import log_action
from app.decorators import rate_limit
from app.models.machine import Machine
from app.models.plant import Plant
from app.models.company import Company
from app.security import get_active_company_id
from app.services.kpi_service import (
    company_kpi_summary,
    compute_daily_kpi,
    downtime_trend,
    get_machine_kpi,
    mtbf_hours,
    mttr_hours,
    plant_downtime_trend,
    plant_kpi_summary,
)
from app.services.health_service import compute_health_score, latest_health, plant_health_distribution, company_health_distribution
from app.services.comparison_service import compare_plants, compare_machines, underperforming
from .management_routes import _resolve_user, _user_role, _check_company_access, _check_plant_access
from . import api_bp


@api_bp.route("/kpi/machine/<int:machine_id>", methods=["GET"])
# Allow session users or JWT via headers to avoid CSRF cookie checks.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def machine_kpi_api(machine_id: int):
    user = _resolve_user()
    role = _user_role(user)
    machine = Machine.query.get_or_404(machine_id)
    _check_company_access(user, machine.company_id)
    if machine.plant_id:
        _check_plant_access(user, machine.plant_id)
    if role not in {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN", "PLANT_MANAGER", "MAINTENANCE_HEAD", "TECHNICIAN", "VIEWER", "MANAGER"}:
        abort(403)

    kpi = get_machine_kpi(machine_id, machine.company_id)
    if not kpi:
        abort(404)
    trend = downtime_trend(machine)
    log_action("kpi_view", "machine", machine.id, company_id=machine.company_id, plant_id=machine.plant_id)
    return jsonify(
        {
            "machine_id": machine.id,
            "plant_id": machine.plant_id,
            "date": kpi.date.isoformat(),
            "oee": kpi.oee,
            "availability": kpi.availability,
            "performance": kpi.performance,
            "quality": kpi.quality,
            "utilization_rate": kpi.utilization_rate,
            "energy_efficiency": kpi.energy_efficiency,
            "downtime_minutes": kpi.downtime_minutes,
            "cost_of_downtime": float(kpi.cost_of_downtime or 0),
            "downtime_trend": trend,
        }
    )


@api_bp.route("/kpi/plant/<int:plant_id>", methods=["GET"])
# Allow either JWT (if present via headers) or logged-in session users; avoid cookie CSRF 422s.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def plant_kpi_api(plant_id: int):
    user = _resolve_user()
    role = _user_role(user)
    plant = Plant.query.get_or_404(plant_id)
    _check_company_access(user, plant.company_id)
    _check_plant_access(user, plant.id)
    if role not in {
        "SUPER_ADMIN",
        "ENTERPRISE_ADMIN",
        "ADMIN",
        "PLANT_MANAGER",
        "MAINTENANCE_HEAD",
        "MANAGER",
        "TECHNICIAN",
        "VIEWER",
    }:
        abort(403)

    summary = plant_kpi_summary(plant_id)
    trend = plant_downtime_trend(plant_id)
    log_action("kpi_view", "plant", plant.id, company_id=plant.company_id, plant_id=plant.id)
    return jsonify({"plant_id": plant.id, **summary, "downtime_trend": trend})


@api_bp.route("/kpi/company-summary", methods=["GET"])
# Allow either JWT (if present) via headers or logged-in session users; skip cookies to avoid CSRF 422s.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def company_kpi_api():
    user = _resolve_user()
    role = _user_role(user)
    company_id = get_active_company_id() or user.company_id
    _check_company_access(user, company_id)
    if role not in {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN", "MANAGER", "PLANT_MANAGER", "MAINTENANCE_HEAD", "TECHNICIAN", "VIEWER"}:
        abort(403)

    summary = company_kpi_summary(company_id)
    log_action("kpi_view", "company", company_id, company_id=company_id)
    return jsonify({"company_id": company_id, **summary})


@api_bp.route("/health/machine/<int:machine_id>", methods=["GET"])
# Allow session users or JWT via headers to avoid CSRF cookie checks.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def machine_health_api(machine_id: int):
    user = _resolve_user()
    role = _user_role(user)
    machine = Machine.query.get_or_404(machine_id)
    _check_company_access(user, machine.company_id)
    if machine.plant_id:
        _check_plant_access(user, machine.plant_id)
    if role not in {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN", "PLANT_MANAGER", "MAINTENANCE_HEAD", "TECHNICIAN", "MANAGER"}:
        abort(403)

    score = latest_health(machine.id, machine.company_id)
    if not score:
        score = compute_health_score(machine)
    if not score:
        abort(404)
    log_action("health_view", "machine", machine.id, company_id=machine.company_id, plant_id=machine.plant_id)
    return jsonify(
        {
            "machine_id": machine.id,
            "plant_id": machine.plant_id,
            "score": score.health_score,
            "risk_level": score.risk_level,
            "calculated_at": score.calculated_at.isoformat(),
        }
    )


@api_bp.route("/health/plant/<int:plant_id>", methods=["GET"])
# Allow either JWT (if present via headers) or logged-in session users; avoid cookie CSRF 422s.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def plant_health_api(plant_id: int):
    user = _resolve_user()
    role = _user_role(user)
    if role not in {
        "SUPER_ADMIN",
        "ENTERPRISE_ADMIN",
        "ADMIN",
        "PLANT_MANAGER",
        "MAINTENANCE_HEAD",
        "MANAGER",
        "TECHNICIAN",
        "VIEWER",
    }:
        abort(403)
    # Allow dashboards to call with 0 when the user is not tied to a specific plant.
    plant = Plant.query.get_or_404(plant_id) if plant_id > 0 else None
    if plant:
        _check_company_access(user, plant.company_id)
        _check_plant_access(user, plant.id)
        dist = plant_health_distribution(plant.id)
        log_action("health_view", "plant", plant.id, company_id=plant.company_id, plant_id=plant.id)
        return jsonify({"plant_id": plant.id, "distribution": dist})

    mapping = user.plant_mappings.first() if hasattr(user, "plant_mappings") else None
    if mapping:
        plant = mapping.plant
        _check_company_access(user, plant.company_id)
        _check_plant_access(user, plant.id)
        dist = plant_health_distribution(plant.id)
        log_action("health_view", "plant", plant.id, company_id=plant.company_id, plant_id=plant.id)
        return jsonify({"plant_id": plant.id, "distribution": dist})

    company_id = get_active_company_id() or user.company_id
    _check_company_access(user, company_id)
    dist = company_health_distribution(company_id)
    log_action("health_view", "company", company_id, company_id=company_id)
    return jsonify({"plant_id": None, "company_id": company_id, "distribution": dist})


@api_bp.route("/comparison/plants", methods=["GET"])
# Allow either JWT (if present) via headers or logged-in session users; skip cookies to avoid CSRF 422s.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def comparison_plants_api():
    user = _resolve_user()
    role = _user_role(user)
    company_id = get_active_company_id() or user.company_id
    _check_company_access(user, company_id)
    if role not in {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN", "MANAGER"}:
        abort(403)
    data = compare_plants(company_id)
    return jsonify({"plants": data})


@api_bp.route("/comparison/machines", methods=["GET"])
# Allow either JWT (if present) via headers or logged-in session users; skip cookies to avoid CSRF 422s.
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def comparison_machines_api():
    user = _resolve_user()
    role = _user_role(user)
    company_id = get_active_company_id() or user.company_id
    _check_company_access(user, company_id)
    if role not in {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN", "MANAGER", "MAINTENANCE_HEAD", "PLANT_MANAGER", "TECHNICIAN"}:
        abort(403)
    data = compare_machines(company_id)
    return jsonify(data | underperforming(company_id))
