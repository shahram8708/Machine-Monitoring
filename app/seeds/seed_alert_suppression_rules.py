from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import AlertSuppressionRule, Machine

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
    "name": "alert_suppression_rules",
    "order": 370,
    "description": "Alert suppression windows per machine",
}


def run():
    machines = {m.machine_code: m for m in Machine.query.all()}
    now = ANCHOR_NOW

    rules = [
        {
            "machine_code": "AP-PUN-LATHE-01",
            "alert_type": "SpindleTemperatureHigh",
            "suppression_window_minutes": 20,
            "max_trigger_count": 2,
            "adaptive_threshold": 2.5,
        },
        {
            "machine_code": "NW-AHD-PRESS-01",
            "alert_type": "HydraulicPressureRipple",
            "suppression_window_minutes": 15,
            "max_trigger_count": 3,
            "adaptive_threshold": 4.0,
        },
        {
            "machine_code": "EV-NOI-PACK-01",
            "alert_type": "SealTemperatureDrift",
            "suppression_window_minutes": 25,
            "max_trigger_count": 2,
            "adaptive_threshold": 3.0,
        },
    ]

    for data in rules:
        machine = machines.get(data["machine_code"])
        if not machine:
            continue
        rule = AlertSuppressionRule.query.filter_by(machine_id=machine.id, alert_type=data["alert_type"]).first()
        payload = {
            "machine_id": machine.id,
            "alert_type": data["alert_type"],
            "suppression_window_minutes": data["suppression_window_minutes"],
            "max_trigger_count": data["max_trigger_count"],
            "adaptive_threshold": data["adaptive_threshold"],
            "updated_at": _clamp_dt(now),
        }
        if not rule:
            rule = AlertSuppressionRule(**payload)
            db.session.add(rule)
        else:
            for field, value in payload.items():
                setattr(rule, field, value)
