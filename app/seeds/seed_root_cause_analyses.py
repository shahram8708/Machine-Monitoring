from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import AlertGroup, Machine, RootCauseAnalysis

MIN_DATE = date(2026, 3, 1)
MAX_DATE = date(2026, 3, 3)
ANCHOR_NOW = datetime(2026, 3, 3, 12, 0, 0)


def _clamp_dt(value: datetime) -> datetime:
    if value.date() < MIN_DATE:
        return value.replace(year=2026, month=3, day=1)
    if value.date() > MAX_DATE:
        return value.replace(year=2026, month=3, day=3)
    return value


SEED_METADATA = {
    "name": "root_cause_analyses",
    "order": 380,
    "description": "AI-generated root cause summaries",
}


def run():
    machines = {m.machine_code: m for m in Machine.query.all()}
    groups = {(g.machine_id, g.group_reason): g for g in AlertGroup.query.all()}
    now = ANCHOR_NOW

    rows = [
        {
            "machine_code": "NW-AHD-PRESS-01",
            "group_reason": "Pressure ripple above threshold",
            "primary_root_cause": "Hydraulic accumulator pre-charge below spec",
            "contributing_factors": ["Seal wear", "Pump cavitation"],
            "probability_breakdown": {"accumulator": 0.46, "seal_wear": 0.32, "pump": 0.22},
            "timeline_explanation": "Pressure ripple started after accumulator temperature drop post shift change.",
            "sensor_interactions": "Pressure and vibration correlated with hydraulic loop temperature dip.",
            "confidence_score": 0.78,
            "created_at": _clamp_dt(now - timedelta(hours=1, minutes=20)),
        },
        {
            "machine_code": "EV-NOI-PACK-01",
            "group_reason": "Seal temperature instability",
            "primary_root_cause": "Inconsistent film tension causing heater oscillation",
            "contributing_factors": ["Humidity spike", "Film batch variance"],
            "probability_breakdown": {"tension": 0.41, "humidity": 0.36, "heater": 0.23},
            "timeline_explanation": "Heater PID began oscillating after humidity rose past 60% in the hall.",
            "sensor_interactions": "Humidity sensor and seal temperature deviations moved in phase.",
            "confidence_score": 0.71,
            "created_at": _clamp_dt(now - timedelta(hours=1)),
        },
    ]

    for data in rows:
        machine = machines.get(data["machine_code"])
        group = groups.get((machine.id, data["group_reason"])) if machine else None
        if not machine or not group:
            continue
        rca = RootCauseAnalysis.query.filter_by(machine_id=machine.id, alert_group_id=group.id).first()
        if not rca:
            rca = RootCauseAnalysis(
                machine_id=machine.id,
                alert_group_id=group.id,
                primary_root_cause=data["primary_root_cause"],
                contributing_factors=data.get("contributing_factors"),
                probability_breakdown=data.get("probability_breakdown"),
                timeline_explanation=data.get("timeline_explanation"),
                sensor_interactions=data.get("sensor_interactions"),
                confidence_score=data.get("confidence_score"),
                created_at=_clamp_dt(data.get("created_at", now)),
            )
            db.session.add(rca)
        else:
            rca.primary_root_cause = data["primary_root_cause"]
            rca.contributing_factors = data.get("contributing_factors")
            rca.probability_breakdown = data.get("probability_breakdown")
            rca.timeline_explanation = data.get("timeline_explanation")
            rca.sensor_interactions = data.get("sensor_interactions")
            rca.confidence_score = data.get("confidence_score")
