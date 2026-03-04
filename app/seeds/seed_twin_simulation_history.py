from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import DigitalTwin, TwinSimulationHistory

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
    "name": "twin_simulation_history",
    "order": 400,
    "description": "Simulation runs for digital twins",
}


def run():
    twins = {t.machine_id: t for t in DigitalTwin.query.all()}
    now = ANCHOR_NOW

    simulations = [
        {
            "machine_id": twin.machine_id,
            "simulation_type": "composite",
            "input_parameters": {"load_pct": 110, "sensor_drift_pct": 5, "production_pct": 105},
            "simulated_oee": round(twin.baseline_oee * 0.97, 3),
            "simulated_failure_probability": min(0.5, twin.baseline_failure_probability + 0.06),
            "simulated_health_score": max(0, twin.baseline_health_score - 6),
            "simulated_energy_efficiency": max(0, twin.baseline_energy_efficiency - 0.03),
            "risk_delta": 0.06,
            "impact_level": "MEDIUM",
            "ai_analysis": {"notes": "Load increase stresses spindle and hydraulics."},
            "created_at": _clamp_dt(now - timedelta(hours=10)),
        }
        for twin in twins.values()
    ]

    for data in simulations:
        twin = twins.get(data["machine_id"])
        if not twin:
            continue
        sim = TwinSimulationHistory.query.filter_by(
            digital_twin_id=twin.id,
            simulation_type=data["simulation_type"],
        ).first()
        payload = {
            "digital_twin_id": twin.id,
            "simulation_type": data["simulation_type"],
            "input_parameters": data["input_parameters"],
            "simulated_oee": data["simulated_oee"],
            "simulated_failure_probability": data["simulated_failure_probability"],
            "simulated_health_score": data["simulated_health_score"],
            "simulated_energy_efficiency": data["simulated_energy_efficiency"],
            "risk_delta": data["risk_delta"],
            "impact_level": data["impact_level"],
            "ai_analysis": data["ai_analysis"],
            "created_at": data["created_at"],
        }
        if not sim:
            sim = TwinSimulationHistory(**payload)
            db.session.add(sim)
        else:
            for field, value in payload.items():
                setattr(sim, field, value)
