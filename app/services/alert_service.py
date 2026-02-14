from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from flask import current_app
from flask_mail import Message

from app.extensions import db, mail
from app.models.alert import Alert, AlertTimeline
from app.models.machine_data import MachineData
from app.models.sensor import Sensor
from app.models.user import User

SEVERITY_ORDER = ["low", "medium", "high", "critical"]


def _next_severity(current: str) -> str:
    if current not in SEVERITY_ORDER:
        return "low"
    idx = SEVERITY_ORDER.index(current)
    return SEVERITY_ORDER[min(idx + 1, len(SEVERITY_ORDER) - 1)]


def _add_timeline(alert: Alert, event: str, note: str = "") -> None:
    db.session.add(
        AlertTimeline(alert=alert, event=event, severity=alert.severity, note=note)
    )


def _recent_duplicate_exists(machine_id: int, sensor_type: str, minutes: int = 5) -> bool:
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    existing = (
        Alert.query.filter_by(machine_id=machine_id, sensor_type=sensor_type, is_resolved=False)
        .filter(Alert.created_at >= cutoff)
        .first()
    )
    return existing is not None


def _notify(alert: Alert, level: int) -> None:
    if not mail:  # mail not initialized
        return
    company_id = alert.company_id
    subject = f"[Alert L{level}] {alert.severity.upper()} - Machine {alert.machine.machine_name}"
    body = (
        f"Machine: {alert.machine.machine_name}\n"
        f"Sensor: {alert.sensor_type}\n"
        f"Value: {alert.value}\n"
        f"Threshold: {alert.threshold}\n"
        f"Severity: {alert.severity}\n"
        f"Message: {alert.message}\n"
        f"Created: {alert.created_at.isoformat()}\n"
    )

    recipients: list[str] = []
    if level == 2:
        recipients = [u.email for u in User.query.filter_by(company_id=company_id, role="manager", is_active=True)]
    elif level >= 3:
        recipients = [u.email for u in User.query.filter_by(role="admin", is_active=True)]

    if not recipients:
        return

    msg = Message(subject=subject, recipients=recipients, body=body)
    try:
        mail.send(msg)
        note = f"Email notification sent to {len(recipients)} recipient(s)"
    except Exception:  # noqa: BLE001
        note = "Email notification failed"
    _add_timeline(alert, f"notify_level_{level}", note)
    db.session.commit()


def create_alert(machine, sensor_type: str, value: Optional[float], threshold: Optional[float], severity: str, message: str) -> Alert:
    if _recent_duplicate_exists(machine.id, sensor_type):
        return (
            Alert.query.filter_by(machine_id=machine.id, sensor_type=sensor_type, is_resolved=False)
            .order_by(Alert.created_at.desc())
            .first()
        )

    severity = severity if severity in SEVERITY_ORDER else "low"
    alert = Alert(
        machine_id=machine.id,
        company_id=machine.company_id,
        sensor_type=sensor_type,
        value=value,
        threshold=threshold,
        severity=severity,
        message=message,
        last_escalated_at=datetime.utcnow(),
    )
    db.session.add(alert)
    _add_timeline(alert, "created", message)
    db.session.commit()
    return alert


def resolve_alert(alert: Alert, user: Optional[User] = None) -> Alert:
    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by_user_id = user.id if user else None
    _add_timeline(alert, "resolved", "Alert marked as resolved")
    db.session.add(alert)
    db.session.commit()
    return alert


def evaluate_alerts_for_datapoint(data_point: MachineData) -> None:
    machine = data_point.machine
    sensors = {s.sensor_type: s for s in Sensor.query.filter_by(machine_id=machine.id).all()}

    def check_threshold(sensor_type: str, value: Optional[float]):
        sensor = sensors.get(sensor_type)
        if sensor is None or value is None:
            return
        if sensor_type == "voltage":
            if value < sensor.min_threshold or value > sensor.max_threshold:
                severity = "high" if abs(value - sensor.max_threshold) < 20 else "critical"
                create_alert(machine, sensor_type, value, sensor.max_threshold, severity, f"Voltage abnormal: {value} {sensor.unit}")
        else:
            if value > sensor.max_threshold:
                severity = "high"
                if value > sensor.max_threshold * 1.1:
                    severity = "critical"
                create_alert(machine, sensor_type, value, sensor.max_threshold, severity, f"{sensor_type.title()} exceeded threshold ({value} {sensor.unit})")

    check_threshold("temperature", data_point.temperature)
    check_threshold("vibration", data_point.vibration)
    check_threshold("current", data_point.current)
    check_threshold("voltage", data_point.voltage)

    # Machine stopped unexpectedly: previous data was running
    prev = (
        MachineData.query.filter(MachineData.machine_id == machine.id, MachineData.timestamp < data_point.timestamp)
        .order_by(MachineData.timestamp.desc())
        .first()
    )
    if prev and prev.running_status and not data_point.running_status:
        create_alert(
            machine,
            "running_status",
            0,
            None,
            "medium",
            "Machine stopped unexpectedly (running → idle)",
        )

    db.session.commit()


def escalate_open_alerts() -> None:
    now = datetime.utcnow()
    interval_minutes = int(current_app.config.get("ALERT_ESCALATION_MINUTES", 10))
    cutoff = now - timedelta(minutes=interval_minutes)
    open_alerts = (
        Alert.query.filter_by(is_resolved=False)
        .filter(Alert.last_escalated_at <= cutoff)
        .all()
    )

    for alert in open_alerts:
        if alert.severity == "critical":
            continue
        alert.last_escalated_at = now
        alert.escalation_level = min(alert.escalation_level + 1, 3)
        alert.severity = _next_severity(alert.severity)
        _add_timeline(alert, "escalated", f"Escalated to {alert.severity}")
        db.session.add(alert)
        db.session.commit()
        if alert.escalation_level == 2:
            _notify(alert, level=2)
        elif alert.escalation_level >= 3:
            _notify(alert, level=3)
