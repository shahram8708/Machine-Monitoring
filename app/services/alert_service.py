from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Optional

from flask import current_app
from sqlalchemy import func

from app.audit import log_action
from app.extensions import db
from app.models import (
    Alert,
    AlertTimeline,
    AlertGroup,
    EscalationRule,
    AlertSuppressionRule,
    MachineHealthScore,
    AIPrediction,
)
from app.models.machine_data import MachineData
from app.models.sensor import Sensor
from app.models.user import User
from app.services import alert_filter_service
from app.services.notification_service import NotificationService

SEVERITY_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def _add_timeline(alert: Alert, event: str, note: str = "") -> None:
    db.session.add(AlertTimeline(alert=alert, event=event, severity=alert.severity, note=note))


def _severity_weight(severity: str) -> float:
    normalized = (severity or "LOW").upper()
    mapping = {"LOW": 25, "MEDIUM": 50, "HIGH": 75, "CRITICAL": 100}
    return mapping.get(normalized, 25)


def _latest_health(machine_id: int, company_id: int) -> Optional[MachineHealthScore]:
    return (
        MachineHealthScore.query.filter_by(machine_id=machine_id, company_id=company_id)
        .order_by(MachineHealthScore.calculated_at.desc())
        .first()
    )


def _latest_prediction(machine_id: int) -> Optional[AIPrediction]:
    return (
        AIPrediction.query.filter_by(machine_id=machine_id)
        .order_by(AIPrediction.created_at.desc())
        .first()
    )


def _priority_score(alert: Alert) -> float:
    severity_component = _severity_weight(alert.severity)
    health = _latest_health(alert.machine_id, alert.company_id)
    health_component = 100 - float(health.health_score) if health else 50
    prediction = _latest_prediction(alert.machine_id)
    failure_probability = float(prediction.failure_probability) if prediction else 50
    downtime_impact = float(alert.machine.cost_per_hour or 0) if alert.machine else 0
    # scale downtime impact to 0-100 with cap
    downtime_component = min(downtime_impact / 10.0, 100) if downtime_impact else 30

    score = (
        0.4 * severity_component
        + 0.2 * health_component
        + 0.2 * failure_probability
        + 0.2 * downtime_component
    )
    return max(0.0, min(100.0, round(score, 2)))


def _find_or_create_group(machine_id: int, alert_type: str, reason: str, window_minutes: int = 10) -> AlertGroup:
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
    existing_group = (
        AlertGroup.query.filter(AlertGroup.machine_id == machine_id, AlertGroup.created_at >= cutoff)
        .join(Alert, Alert.grouped_alert_id == AlertGroup.id)
        .filter(Alert.alert_type == alert_type)
        .order_by(AlertGroup.created_at.desc())
        .first()
    )
    if existing_group:
        return existing_group
    group = AlertGroup(machine_id=machine_id, group_reason=reason)
    db.session.add(group)
    db.session.flush()
    return group


def _sla_deadline(alert: Alert) -> datetime:
    rule = EscalationRule.query.filter_by(company_id=alert.company_id, severity=alert.severity).first()
    minutes = rule.escalation_time_minutes if rule else int(current_app.config.get("ALERT_SLA_MINUTES", 30))
    return alert.created_at + timedelta(minutes=minutes)


def create_alert(
    machine,
    alert_type: str,
    severity: str,
    message: str,
    *,
    value: Optional[float] = None,
    threshold: Optional[float] = None,
    metadata: Optional[Dict] = None,
) -> Optional[Alert]:
    normalized_severity = (severity or "LOW").upper()
    normalized_type = alert_type.lower()

    if alert_filter_service.should_suppress(machine.id, normalized_type):
        log_action("alert_suppressed", "alert", None, company_id=machine.company_id, plant_id=machine.plant_id, new_value={"machine_id": machine.id, "alert_type": normalized_type, "message": message})
        return None

    group = _find_or_create_group(machine.id, normalized_type, reason="time-window")

    alert = Alert(
        machine_id=machine.id,
        plant_id=machine.plant_id,
        company_id=machine.company_id,
        alert_type=normalized_type,
        severity=normalized_severity,
        message=message,
        value=value,
        threshold=threshold,
        sensor_type=normalized_type,
        grouped_alert_id=group.id,
        metadata_payload=metadata or {},
    )
    alert.priority_score = _priority_score(alert)
    alert.sla_deadline = _sla_deadline(alert)
    alert.last_escalated_at = datetime.utcnow()
    alert.mark_status("OPEN")

    db.session.add(alert)
    _add_timeline(alert, "created", message)
    db.session.flush()

    alert_filter_service.record_trigger(machine.id, normalized_type, normalized_severity)

    if normalized_severity == "CRITICAL":
        NotificationService.notify_new_alert(alert)

    db.session.commit()
    log_action("alert_created", "alert", alert.id, company_id=alert.company_id, plant_id=alert.plant_id, new_value={"severity": alert.severity, "message": alert.message, "priority": alert.priority_score})
    return alert


def acknowledge_alert(alert_id: int, user: User) -> Alert:
    alert = Alert.query.get_or_404(alert_id)
    alert.acknowledged_by = user.id
    alert.acknowledged_at = datetime.utcnow()
    alert.mark_status("ACKNOWLEDGED")
    alert.response_time_minutes = (alert.acknowledged_at - alert.created_at).total_seconds() / 60.0
    _add_timeline(alert, "acknowledged", f"Acknowledged by user {user.id}")
    db.session.commit()
    log_action("alert_acknowledged", "alert", alert.id, company_id=alert.company_id, plant_id=alert.plant_id, new_value={"user_id": user.id})
    return alert


def resolve_alert(alert_id: int, user: Optional[User] = None) -> Alert:
    alert = Alert.query.get_or_404(alert_id)
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by_user_id = user.id if user else None
    alert.mark_status("RESOLVED")
    alert.response_time_minutes = (alert.resolved_at - alert.created_at).total_seconds() / 60.0
    _add_timeline(alert, "resolved", "Alert resolved")
    db.session.commit()
    log_action("alert_resolved", "alert", alert.id, company_id=alert.company_id, plant_id=alert.plant_id, new_value={"user_id": getattr(user, "id", None)})
    return alert


def sla_status(alert_id: int) -> Dict[str, object]:
    alert = Alert.query.get_or_404(alert_id)
    if not alert.sla_deadline:
        alert.sla_deadline = _sla_deadline(alert)
    remaining_seconds = (alert.sla_deadline - datetime.utcnow()).total_seconds()
    breached = remaining_seconds < 0 and alert.status not in {"RESOLVED", "ACKNOWLEDGED"}
    return {"alert_id": alert.id, "time_remaining_seconds": max(0, int(remaining_seconds)), "breached": breached}


def evaluate_alerts_for_datapoint(data_point: MachineData) -> None:
    machine = data_point.machine
    sensors = {s.sensor_type: s for s in Sensor.query.filter_by(machine_id=machine.id).all()}

    def check_threshold(sensor_type: str, value: Optional[float]):
        sensor = sensors.get(sensor_type)
        if sensor is None or value is None:
            return
        adjusted_threshold = alert_filter_service.get_adaptive_threshold(machine.id, sensor_type, sensor.max_threshold)
        upper_threshold = adjusted_threshold if adjusted_threshold is not None else sensor.max_threshold
        if sensor_type == "voltage":
            if value < sensor.min_threshold or value > upper_threshold:
                severity = "HIGH" if abs(value - upper_threshold) < 20 else "CRITICAL"
                create_alert(machine, sensor_type, severity, f"Voltage abnormal: {value} {sensor.unit}", value=value, threshold=upper_threshold)
        else:
            if value > upper_threshold:
                severity = "HIGH"
                if upper_threshold and value > upper_threshold * 1.1:
                    severity = "CRITICAL"
                create_alert(machine, sensor_type, severity, f"{sensor_type.title()} exceeded threshold ({value} {sensor.unit})", value=value, threshold=upper_threshold)

    check_threshold("temperature", data_point.temperature)
    check_threshold("vibration", data_point.vibration)
    check_threshold("current", data_point.current)
    check_threshold("voltage", data_point.voltage)

    prev = (
        MachineData.query.filter(MachineData.machine_id == machine.id, MachineData.timestamp < data_point.timestamp)
        .order_by(MachineData.timestamp.desc())
        .first()
    )
    if prev and prev.running_status and not data_point.running_status:
        create_alert(machine, "running_status", "MEDIUM", "Machine stopped unexpectedly (running → idle)")

    db.session.commit()


def escalate_open_alerts() -> None:
    now = datetime.utcnow()
    open_alerts = Alert.query.filter(Alert.status.in_(["OPEN", "ACKNOWLEDGED"])).all()
    for alert in open_alerts:
        if alert.sla_deadline is None:
            alert.sla_deadline = _sla_deadline(alert)
        if alert.status == "ACKNOWLEDGED":
            continue
        if alert.sla_deadline and now >= alert.sla_deadline:
            NotificationService.notify_sla_breach(alert)
            alert.escalation_level = (alert.escalation_level or 0) + 1
            alert.mark_status("ESCALATED")
            alert.last_escalated_at = now
            _add_timeline(alert, "escalated", f"Escalated to level {alert.escalation_level}")
            NotificationService.notify_escalation(alert)
            log_action("alert_escalated", "alert", alert.id, company_id=alert.company_id, plant_id=alert.plant_id, new_value={"level": alert.escalation_level})
    db.session.commit()


def list_alerts(
    company_id: int,
    plant_id: Optional[int] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    grouped_alert_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
):
    query = Alert.query.filter_by(company_id=company_id)
    if plant_id:
        query = query.filter_by(plant_id=plant_id)
    if status:
        query = query.filter_by(status=status.upper())
    if severity:
        query = query.filter_by(severity=severity.upper())
    if grouped_alert_id:
        query = query.filter_by(grouped_alert_id=grouped_alert_id)
    if start_date:
        query = query.filter(Alert.created_at >= start_date)
    if end_date:
        query = query.filter(Alert.created_at <= end_date)
    query = query.order_by(Alert.created_at.desc())
    if page and per_page:
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return pagination.items
    return query.all()


def alert_detail(alert_id: int) -> Alert:
    return Alert.query.get_or_404(alert_id)
