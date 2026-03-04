from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict

from sqlalchemy import func

from app.models import Machine, MachineKPI, MachineSpareMapping, SparePart
from app.services.predictive_service import latest_prediction, run_prediction


DEFAULT_WINDOW_DAYS = None


def _ensure_prediction(machine: Machine):
    pred = latest_prediction(machine.id, machine.company_id)
    if pred:
        return pred
    try:
        return run_prediction(machine)
    except Exception:  # noqa: BLE001
        return None


def _downtime_trend(machine_id: int, days: int | None = DEFAULT_WINDOW_DAYS) -> float:
    query = MachineKPI.query.with_entities(func.avg(MachineKPI.downtime_minutes)).filter_by(machine_id=machine_id)
    if days is not None:
        start_date = datetime.utcnow().date() - timedelta(days=days)
        query = query.filter(MachineKPI.date >= start_date)
    avg_minutes = query.scalar()
    return float(avg_minutes or 0.0) / 60.0  # hours


def revenue_loss_estimate(machine: Machine, downtime_hours: float) -> float:
    revenue_per_hour = float(machine.revenue_per_hour or 0)
    return round(revenue_per_hour * downtime_hours, 2)


def projected_downtime_cost(machine_id: int, company_id: int, window_days: int | None = DEFAULT_WINDOW_DAYS) -> Dict[str, float]:
    machine = Machine.query.filter_by(id=machine_id, company_id=company_id).first_or_404()
    pred = _ensure_prediction(machine)
    failure_prob = pred.failure_probability if pred else 40
    confidence = pred.confidence_score if pred else 0

    downtime_trend_hours = _downtime_trend(machine.id, days=window_days)
    expected_events = max(1.0, failure_prob / 50.0)
    projected_downtime_hours = round(expected_events * downtime_trend_hours, 2)

    downtime_cost = float(machine.cost_per_hour or 0) * projected_downtime_hours
    revenue_loss_val = revenue_loss_estimate(machine, projected_downtime_hours)

    return {
        "projected_downtime_cost": round(downtime_cost, 2),
        "projected_revenue_loss": round(revenue_loss_val, 2),
        "projected_downtime_hours": projected_downtime_hours,
        "confidence": confidence or 0,
    }


def cost_to_failure(machine_id: int, company_id: int, window_days: int | None = DEFAULT_WINDOW_DAYS) -> Dict[str, float]:
    machine = Machine.query.filter_by(id=machine_id, company_id=company_id).first_or_404()
    pred = _ensure_prediction(machine)
    failure_prob = pred.failure_probability if pred else 40
    confidence = pred.confidence_score if pred else 0

    trend_hours = _downtime_trend(machine.id, days=window_days)
    expected_downtime = max(1.0, failure_prob / 50.0) * trend_hours

    repair_cost = float(machine.cost_per_hour or 0) * max(1.0, expected_downtime)

    # Estimate spare part exposure based on mapped parts cost
    mapping_costs = (
        MachineSpareMapping.query.join(SparePart)
        .with_entities(func.avg(SparePart.cost_per_unit))
        .filter(MachineSpareMapping.machine_id == machine.id, SparePart.company_id == company_id)
        .scalar()
    )
    spare_cost = float(mapping_costs or 0) * max(1, int(expected_downtime or 1))

    downtime_cost = float(machine.cost_per_hour or 0) * expected_downtime
    revenue_loss_val = revenue_loss_estimate(machine, expected_downtime)

    total_risk = repair_cost + downtime_cost + spare_cost + revenue_loss_val

    return {
        "projected_downtime_cost": round(downtime_cost, 2),
        "projected_revenue_loss": round(revenue_loss_val, 2),
        "total_risk_exposure": round(total_risk, 2),
        "confidence": confidence or 0,
    }
