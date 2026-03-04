from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, Optional

from app.extensions import db
from app.models.machine import Machine
from app.models.machine_health import MachineHealthScore
from app.services.kpi_service import get_machine_kpi, mtbf_hours, mttr_hours, utilization_rate


WEIGHTS = {
    "oee": 0.30,
    "mtbf": 0.20,
    "downtime": 0.20,
    "severity": 0.15,
    "utilization": 0.15,
}


def _score_from_mtbf(mtbf: float) -> float:
    if mtbf <= 0:
        return 0.0
    return min(100.0, (mtbf / 24.0) * 100.0)


def _score_from_mttr(mttr: float) -> float:
    if mttr <= 0:
        return 100.0
    return max(0.0, 100.0 - min(100.0, (mttr / 8.0) * 100.0))


def _severity_score(alert_count: int) -> float:
    if alert_count <= 0:
        return 100.0
    return max(0.0, 100.0 - min(100.0, alert_count * 10.0))


def _risk_level(score: float) -> str:
    if score >= 80:
        return "LOW"
    if score >= 60:
        return "MEDIUM"
    if score >= 40:
        return "HIGH"
    return "CRITICAL"


def compute_health_score(machine: Machine, day: date | None = None) -> Optional[MachineHealthScore]:
    target_day = day or date.today()
    kpi = get_machine_kpi(machine.id, machine.company_id, target_day)
    if not kpi:
        return None
    metric_day = kpi.date if kpi else target_day
    start_dt = datetime.combine(metric_day - timedelta(days=6), datetime.min.time())
    end_dt = datetime.combine(metric_day, datetime.max.time())
    mtbf_val = mtbf_hours(machine, start_dt, end_dt)
    mttr_val = mttr_hours(machine, start_dt, end_dt)
    utilization_val = utilization_rate(machine, start_dt, end_dt)

    # Approximate downtime frequency using downtime minutes bucketed per day
    downtime_freq = 1.0 if kpi.downtime_minutes > 0 else 0.0
    downtime_score = max(0.0, 100.0 - min(100.0, downtime_freq * 20.0))

    severity_score = _severity_score(alert_count=int(downtime_freq))

    score = 0.0
    score += WEIGHTS["oee"] * (kpi.oee * 100.0)
    score += WEIGHTS["mtbf"] * _score_from_mtbf(mtbf_val)
    score += WEIGHTS["downtime"] * downtime_score
    score += WEIGHTS["severity"] * severity_score
    score += WEIGHTS["utilization"] * (utilization_val * 100.0)

    score = round(min(100.0, max(0.0, score)), 2)
    risk = _risk_level(score)

    existing = (
        MachineHealthScore.query.filter_by(
            machine_id=machine.id,
            calculated_at=datetime.combine(metric_day, datetime.min.time()),
        ).first()
    )
    if not existing:
        existing = MachineHealthScore(
            machine_id=machine.id,
            plant_id=machine.plant_id,
            company_id=machine.company_id,
        )

    existing.health_score = score
    existing.risk_level = risk
    existing.calculated_at = datetime.combine(metric_day, datetime.min.time())
    existing.company_id = machine.company_id

    db.session.add(existing)
    db.session.commit()
    return existing


def latest_health(machine_id: int, company_id: int) -> Optional[MachineHealthScore]:
    machine = Machine.query.filter_by(id=machine_id, company_id=company_id).first()
    if not machine:
        return None
    score = (
        MachineHealthScore.query.filter_by(machine_id=machine.id, company_id=company_id)
        .order_by(MachineHealthScore.calculated_at.desc())
        .first()
    )
    if not score:
        score = compute_health_score(machine)
    return score


def _empty_health_buckets() -> Dict[str, int]:
    return {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}


def plant_health_distribution(plant_id: int) -> Dict[str, int]:
    buckets = _empty_health_buckets()
    scores = MachineHealthScore.query.filter_by(plant_id=plant_id).order_by(MachineHealthScore.calculated_at.desc()).all()
    for score in scores:
        buckets[score.risk_level] = buckets.get(score.risk_level, 0) + 1
    return buckets


def company_health_distribution(company_id: int) -> Dict[str, int]:
    buckets = _empty_health_buckets()
    scores = (
        MachineHealthScore.query.filter_by(company_id=company_id)
        .order_by(MachineHealthScore.calculated_at.desc())
        .all()
    )
    for score in scores:
        buckets[score.risk_level] = buckets.get(score.risk_level, 0) + 1
    return buckets
