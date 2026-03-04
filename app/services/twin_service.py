from __future__ import annotations

from datetime import datetime, timedelta, date
from statistics import mean
from typing import Dict, List, Tuple

from app.extensions import db
from app.models import (
    AIPrediction,
    DigitalTwin,
    Machine,
    MachineHealthScore,
    MachineKPI,
    TwinSimulationHistory,
)


def _avg(values: List[float], default: float = 0.0) -> float:
    cleaned = [float(v) for v in values if v is not None]
    if not cleaned:
        return default
    return round(mean(cleaned), 4)


def _degradation_rate(kpis: List[MachineKPI], health_scores: List[MachineHealthScore]) -> float:
    if len(kpis) >= 2:
        ordered = sorted(kpis, key=lambda k: k.date)
        span_days = max(1, (ordered[-1].date - ordered[0].date).days)
        delta = ordered[0].oee - ordered[-1].oee
        return round(max(0.0005, abs(delta) / span_days), 4)
    if len(health_scores) >= 2:
        ordered = sorted(health_scores, key=lambda h: h.calculated_at)
        span_days = max(1, (ordered[-1].calculated_at.date() - ordered[0].calculated_at.date()).days)
        delta = ordered[0].health_score - ordered[-1].health_score
        return round(max(0.0005, abs(delta) / (span_days * 100.0)), 4)
    return 0.01


def get_or_create_twin(machine: Machine) -> DigitalTwin:
    twin = DigitalTwin.query.filter_by(machine_id=machine.id, company_id=machine.company_id).first()
    if twin:
        return twin
    twin = DigitalTwin(
        machine_id=machine.id,
        plant_id=machine.plant_id,
        company_id=machine.company_id,
        baseline_oee=0,
        baseline_health_score=0,
        baseline_failure_probability=0,
        baseline_energy_efficiency=0,
        degradation_rate=0.01,
        configuration_json={"initialized": True},
        last_updated=datetime.utcnow(),
    )
    db.session.add(twin)
    db.session.commit()
    return twin


def generate_baseline(machine: Machine, window_days: int | None = None) -> DigitalTwin:
    twin = get_or_create_twin(machine)
    earliest_day = date(1970, 1, 1)
    earliest_dt = datetime(1970, 1, 1)
    start_day = earliest_day if window_days is None else date.today() - timedelta(days=window_days)
    start_dt = earliest_dt if window_days is None else datetime.utcnow() - timedelta(days=window_days)

    kpis = (
        MachineKPI.query.filter_by(machine_id=machine.id, plant_id=machine.plant_id)
        .filter(MachineKPI.date >= start_day)
        .order_by(MachineKPI.date.asc())
        .all()
    )
    health_scores = (
        MachineHealthScore.query.filter_by(machine_id=machine.id, plant_id=machine.plant_id)
        .filter(MachineHealthScore.calculated_at >= start_dt)
        .order_by(MachineHealthScore.calculated_at.asc())
        .all()
    )
    predictions = (
        AIPrediction.query.filter_by(machine_id=machine.id, company_id=machine.company_id)
        .filter(AIPrediction.created_at >= start_dt)
        .order_by(AIPrediction.created_at.asc())
        .all()
    )

    twin.baseline_oee = _avg([k.oee for k in kpis], default=0.0)
    twin.baseline_energy_efficiency = _avg([k.energy_efficiency for k in kpis], default=0.0)
    twin.baseline_health_score = _avg([h.health_score for h in health_scores], default=75.0)
    twin.baseline_failure_probability = _avg([p.failure_probability for p in predictions], default=15.0)
    twin.degradation_rate = _degradation_rate(kpis, health_scores)
    twin.last_updated = datetime.utcnow()
    twin.configuration_json = {
        "window_days": window_days,
        "kpi_samples": len(kpis),
        "health_samples": len(health_scores),
        "prediction_samples": len(predictions),
    }

    db.session.add(twin)
    db.session.commit()
    return twin


def serialize_history(record: TwinSimulationHistory) -> Dict:
    return {
        "id": record.id,
        "digital_twin_id": record.digital_twin_id,
        "simulation_type": record.simulation_type,
        "input_parameters": record.input_parameters or {},
        "simulated_oee": record.simulated_oee,
        "simulated_failure_probability": record.simulated_failure_probability,
        "simulated_health_score": record.simulated_health_score,
        "simulated_energy_efficiency": record.simulated_energy_efficiency,
        "risk_delta": record.risk_delta,
        "impact_level": record.impact_level,
        "ai_analysis": record.ai_analysis or {},
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def serialize_twin(twin: DigitalTwin, include_latest: bool = True) -> Dict:
    latest = twin.simulations.order_by(TwinSimulationHistory.created_at.desc()).first() if include_latest else None
    return {
        "id": twin.id,
        "machine_id": twin.machine_id,
        "plant_id": twin.plant_id,
        "company_id": twin.company_id,
        "baseline_oee": twin.baseline_oee,
        "baseline_health_score": twin.baseline_health_score,
        "baseline_failure_probability": twin.baseline_failure_probability,
        "baseline_energy_efficiency": twin.baseline_energy_efficiency,
        "degradation_rate": twin.degradation_rate,
        "configuration_json": twin.configuration_json or {},
        "last_updated": twin.last_updated.isoformat() if twin.last_updated else None,
        "created_at": twin.created_at.isoformat() if twin.created_at else None,
        "latest_simulation": serialize_history(latest) if latest else None,
    }


def record_simulation(
    twin: DigitalTwin,
    simulation_type: str,
    params: Dict,
    result: Dict,
    ai_analysis: Dict | None = None,
) -> TwinSimulationHistory:
    history = TwinSimulationHistory(
        digital_twin_id=twin.id,
        simulation_type=simulation_type,
        input_parameters=params,
        simulated_oee=result.get("simulated_oee", 0),
        simulated_failure_probability=result.get("simulated_failure_probability", 0),
        simulated_health_score=result.get("simulated_health_score", 0),
        simulated_energy_efficiency=result.get("simulated_energy_efficiency", 0),
        risk_delta=result.get("risk_delta", 0),
        impact_level=result.get("impact_level", "LOW"),
        ai_analysis=ai_analysis,
        created_at=datetime.utcnow(),
    )
    db.session.add(history)
    db.session.commit()
    return history


def fetch_history(twin: DigitalTwin, page: int = 1, per_page: int = 25) -> Tuple[List[Dict], int]:
    pagination = twin.simulations.order_by(TwinSimulationHistory.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return [serialize_history(item) for item in pagination.items], pagination.total
