from datetime import date, datetime, timedelta

MIN_DATE = date(2026, 3, 1)
MAX_DATE = date(2026, 3, 3)
ANCHOR_NOW = datetime(2026, 3, 3, 12, 0, 0)


def _clamp_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.date() < MIN_DATE:
        return value.replace(year=2026, month=3, day=1)
    if value.date() > MAX_DATE:
        return value.replace(year=2026, month=3, day=3)
    return value

from app.extensions import db
from app.models import Alert, AlertGroup, Machine, User

SEED_METADATA = {
    "name": "alerts",
    "order": 340,
    "description": "Active and historical alerts",
}


def run():
    machines = {m.machine_code: m for m in Machine.query.all()}
    groups = {(g.machine_id, g.group_reason): g for g in AlertGroup.query.all()}
    users = {u.email: u for u in User.query.all()}
    now = ANCHOR_NOW

    alerts = [
        {
            "machine_code": "NW-AHD-PRESS-01",
            "alert_type": "HydraulicPressureRipple",
            "severity": "HIGH",
            "priority_score": 0.84,
            "group_reason": "Pressure ripple above threshold",
            "sla_deadline": now - timedelta(minutes=15),
            "acknowledged_by_email": "rina.shah@northwind-auto.com",
            "acknowledged_at": now - timedelta(hours=1, minutes=10),
            "resolved_at": None,
            "status": "ACKNOWLEDGED",
            "sensor_type": "pressure",
            "value": 195.0,
            "threshold": 180.0,
            "message": "Hydraulic pressure ripple exceeded control limits on press line.",
            "is_resolved": False,
            "last_escalated_at": now - timedelta(hours=1),
            "resolved_by_email": None,
            "metadata_payload": {"window_minutes": 30, "stddev": 18.3},
        },
        {
            "machine_code": "EV-NOI-PACK-01",
            "alert_type": "SealTemperatureDrift",
            "severity": "MEDIUM",
            "priority_score": 0.62,
            "group_reason": "Seal temperature instability",
            "sla_deadline": now + timedelta(minutes=45),
            "acknowledged_by_email": None,
            "acknowledged_at": None,
            "resolved_at": None,
            "status": "OPEN",
            "sensor_type": "temperature",
            "value": 48.7,
            "threshold": 45.0,
            "message": "Sealing jaw temperature variance above tolerance.",
            "is_resolved": False,
            "last_escalated_at": now - timedelta(minutes=30),
            "resolved_by_email": None,
            "metadata_payload": {"batch": "BF-2403", "film": "12u PE"},
        },
        {
            "machine_code": "AP-PUN-LATHE-01",
            "alert_type": "SpindleTemperatureHigh",
            "severity": "MEDIUM",
            "priority_score": 0.55,
            "group_reason": None,
            "sla_deadline": now - timedelta(minutes=10),
            "acknowledged_by_email": "sanjay.pillai@aurora-precision.com",
            "acknowledged_at": now - timedelta(hours=2),
            "resolved_at": now - timedelta(hours=1, minutes=40),
            "status": "RESOLVED",
            "sensor_type": "temperature",
            "value": 82.4,
            "threshold": 80.0,
            "message": "Spindle temperature exceeded warning threshold during roughing pass.",
            "is_resolved": True,
            "last_escalated_at": now - timedelta(hours=2),
            "resolved_by_email": "sanjay.pillai@aurora-precision.com",
            "metadata_payload": {"program": "LATHE-PN-442", "tool": "TNMG160404"},
        },
    ]

    for data in alerts:
        machine = machines.get(data["machine_code"])
        if not machine:
            continue
        group = None
        if data.get("group_reason"):
            group = groups.get((machine.id, data["group_reason"]))
        ack_user = users.get(data.get("acknowledged_by_email")) if data.get("acknowledged_by_email") else None
        res_user = users.get(data.get("resolved_by_email")) if data.get("resolved_by_email") else None

        for field in ["sla_deadline", "acknowledged_at", "resolved_at", "created_at", "last_escalated_at"]:
            data[field] = _clamp_dt(data.get(field))

        alert = Alert.query.filter_by(
            machine_id=machine.id,
            alert_type=data["alert_type"],
            created_at=data.get("created_at", data.get("acknowledged_at") or data.get("resolved_at") or now),
        ).first()
        payload = {
            "machine_id": machine.id,
            "plant_id": machine.plant_id,
            "company_id": machine.company_id,
            "alert_type": data["alert_type"],
            "severity": data["severity"],
            "priority_score": data.get("priority_score"),
            "grouped_alert_id": group.id if group else None,
            "sla_deadline": data.get("sla_deadline"),
            "acknowledged_by": ack_user.id if ack_user else None,
            "acknowledged_at": data.get("acknowledged_at"),
            "resolved_at": data.get("resolved_at"),
            "escalation_level": 1 if data["severity"] in {"HIGH", "CRITICAL"} else 0,
            "response_time_minutes": 35 if data.get("acknowledged_at") else None,
            "status": data["status"],
            "created_at": data.get("created_at", _clamp_dt(now - timedelta(hours=2))),
            "sensor_type": data.get("sensor_type"),
            "value": data.get("value"),
            "threshold": data.get("threshold"),
            "message": data.get("message"),
            "is_resolved": data.get("is_resolved", False),
            "last_escalated_at": data.get("last_escalated_at", _clamp_dt(now)),
            "resolved_by_user_id": res_user.id if res_user else None,
            "metadata_payload": data.get("metadata_payload"),
        }
        if not alert:
            alert = Alert(**payload)
            db.session.add(alert)
        else:
            for field, value in payload.items():
                setattr(alert, field, value)
