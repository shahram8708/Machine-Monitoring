from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import AlertGroup, Machine

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
    "name": "alert_groups",
    "order": 330,
    "description": "Grouped alerts for correlated events",
}


def run():
    machines = {m.machine_code: m for m in Machine.query.all()}
    now = ANCHOR_NOW

    groups = [
        {
            "machine_code": "NW-AHD-PRESS-01",
            "group_reason": "Pressure ripple above threshold",
            "created_at": now - timedelta(hours=6),
        },
        {
            "machine_code": "EV-NOI-PACK-01",
            "group_reason": "Seal temperature instability",
            "created_at": now - timedelta(hours=5),
        },
    ]

    for data in groups:
        machine = machines.get(data["machine_code"])
        if not machine:
            continue
        data["created_at"] = _clamp_dt(data["created_at"])
        group = AlertGroup.query.filter_by(machine_id=machine.id, group_reason=data["group_reason"]).first()
        if not group:
            group = AlertGroup(
                machine_id=machine.id,
                group_reason=data["group_reason"],
                created_at=data["created_at"],
            )
            db.session.add(group)
        else:
            group.created_at = group.created_at or data["created_at"]
