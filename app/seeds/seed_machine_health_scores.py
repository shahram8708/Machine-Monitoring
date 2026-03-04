from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Machine, MachineHealthScore

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
    "name": "machine_health_scores",
    "order": 300,
    "description": "Latest machine health assessments",
}


def run():
    now = ANCHOR_NOW
    machines = {m.machine_code: m for m in Machine.query.all()}

    scores = {
        "AP-PUN-LATHE-01": {"health_score": 91.0, "risk_level": "LOW"},
        "AP-MAA-MILL-01": {"health_score": 88.5, "risk_level": "LOW"},
        "NW-AHD-PRESS-01": {"health_score": 74.0, "risk_level": "MEDIUM"},
        "EV-NOI-PACK-01": {"health_score": 69.5, "risk_level": "MEDIUM"},
    }

    for machine_code, values in scores.items():
        machine = machines.get(machine_code)
        if not machine:
            continue
        calculated_at = _clamp_dt(values.get("calculated_at") or now - timedelta(hours=2))
        row = (
            MachineHealthScore.query.filter_by(machine_id=machine.id, calculated_at=calculated_at)
            .order_by(MachineHealthScore.id.asc())
            .first()
        )
        if not row:
            row = MachineHealthScore(
                machine_id=machine.id,
                plant_id=machine.plant_id,
                company_id=machine.company_id,
                health_score=values["health_score"],
                risk_level=values["risk_level"],
                calculated_at=calculated_at,
            )
            db.session.add(row)
        else:
            row.health_score = values["health_score"]
            row.risk_level = values["risk_level"]
            row.plant_id = machine.plant_id
            row.company_id = machine.company_id
