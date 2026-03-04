from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Alert, AlertTimeline, Machine

MIN_DATE = date(2026, 3, 1)
MAX_DATE = date(2026, 3, 3)


def _clamp_dt(value: datetime) -> datetime:
    if value.date() < MIN_DATE:
        return value.replace(year=2026, month=3, day=1)
    if value.date() > MAX_DATE:
        return value.replace(year=2026, month=3, day=3)
    return value


SEED_METADATA = {
    "name": "alert_timelines",
    "order": 350,
    "description": "Alert lifecycle events",
}


def run():
    machines = {m.machine_code: m for m in Machine.query.all()}
    now = datetime(2026, 3, 3, 12, 0, 0)

    def _alert(machine_code, alert_type):
        machine = machines.get(machine_code)
        if not machine:
            return None
        return Alert.query.filter_by(machine_id=machine.id, alert_type=alert_type).order_by(Alert.created_at.desc()).first()

    timelines = [
        {
            "alert": _alert("NW-AHD-PRESS-01", "HydraulicPressureRipple"),
            "events": [
                ("triggered", "HIGH", "Pressure ripple detected"),
                ("acknowledged", "HIGH", "Plant manager notified"),
            ],
        },
        {
            "alert": _alert("EV-NOI-PACK-01", "SealTemperatureDrift"),
            "events": [
                ("triggered", "MEDIUM", "Seal temp variance"),
            ],
        },
        {
            "alert": _alert("AP-PUN-LATHE-01", "SpindleTemperatureHigh"),
            "events": [
                ("triggered", "MEDIUM", "Spindle temperature exceeded threshold"),
                ("resolved", "MEDIUM", "Cooling flow adjusted and tool replaced"),
            ],
        },
    ]

    for item in timelines:
        alert = item["alert"]
        if not alert:
            continue
        for idx, (event, severity, note) in enumerate(item["events"]):
            created_at = _clamp_dt(alert.created_at + timedelta(minutes=idx * 10))
            timeline = AlertTimeline.query.filter_by(alert_id=alert.id, event=event).first()
            if not timeline:
                timeline = AlertTimeline(
                    alert_id=alert.id,
                    event=event,
                    severity=severity,
                    note=note,
                    created_at=created_at,
                )
                db.session.add(timeline)
            else:
                timeline.severity = severity
                timeline.note = note
                timeline.created_at = _clamp_dt(timeline.created_at or created_at)
