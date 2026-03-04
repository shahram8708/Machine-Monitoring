from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import DigitalTwin, Machine

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
    "name": "digital_twins",
    "order": 390,
    "description": "Baseline digital twin configurations",
}


def run():
    machines = {m.machine_code: m for m in Machine.query.all()}
    now = ANCHOR_NOW

    twins = [
        {
            "machine_code": "AP-PUN-LATHE-01",
            "baseline_oee": 0.88,
            "baseline_health_score": 90.0,
            "baseline_failure_probability": 0.08,
            "baseline_energy_efficiency": 0.83,
            "degradation_rate": 0.012,
            "configuration_json": {"axes": 2, "spindle_power_kw": 18, "coolant": "emulsion"},
            "last_updated": _clamp_dt(now - timedelta(days=3)),
            "created_at": _clamp_dt(now - timedelta(days=30)),
        },
        {
            "machine_code": "AP-MAA-MILL-01",
            "baseline_oee": 0.85,
            "baseline_health_score": 88.0,
            "baseline_failure_probability": 0.10,
            "baseline_energy_efficiency": 0.81,
            "degradation_rate": 0.014,
            "configuration_json": {"axes": 5, "table_size_mm": [800, 500], "coolant": "through-tool"},
            "last_updated": _clamp_dt(now - timedelta(days=2)),
            "created_at": _clamp_dt(now - timedelta(days=28)),
        },
        {
            "machine_code": "NW-AHD-PRESS-01",
            "baseline_oee": 0.80,
            "baseline_health_score": 76.0,
            "baseline_failure_probability": 0.22,
            "baseline_energy_efficiency": 0.74,
            "degradation_rate": 0.018,
            "configuration_json": {"tonnage": 300, "stroke_mm": 250, "loop": "hydraulic"},
            "last_updated": _clamp_dt(now - timedelta(days=1)),
            "created_at": _clamp_dt(now - timedelta(days=26)),
        },
        {
            "machine_code": "EV-NOI-PACK-01",
            "baseline_oee": 0.75,
            "baseline_health_score": 70.0,
            "baseline_failure_probability": 0.28,
            "baseline_energy_efficiency": 0.72,
            "degradation_rate": 0.020,
            "configuration_json": {"form_width_mm": 320, "film_type": "PE", "heater_zones": 3},
            "last_updated": _clamp_dt(now - timedelta(days=1)),
            "created_at": _clamp_dt(now - timedelta(days=20)),
        },
    ]

    for data in twins:
        machine = machines.get(data["machine_code"])
        if not machine:
            continue
        twin = DigitalTwin.query.filter_by(machine_id=machine.id).first()
        payload = {
            "machine_id": machine.id,
            "plant_id": machine.plant_id,
            "company_id": machine.company_id,
            "baseline_oee": data["baseline_oee"],
            "baseline_health_score": data["baseline_health_score"],
            "baseline_failure_probability": data["baseline_failure_probability"],
            "baseline_energy_efficiency": data["baseline_energy_efficiency"],
            "degradation_rate": data["degradation_rate"],
            "configuration_json": data["configuration_json"],
            "last_updated": data["last_updated"],
            "created_at": data["created_at"],
        }
        if not twin:
            twin = DigitalTwin(**payload)
            db.session.add(twin)
        else:
            for field, value in payload.items():
                setattr(twin, field, value)
