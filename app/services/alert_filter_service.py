from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from app.audit import log_action
from app.extensions import db
from app.models import Alert, AlertSuppressionRule


def _get_rule(machine_id: int, alert_type: str) -> AlertSuppressionRule:
    normalized_type = alert_type.lower()
    rule = AlertSuppressionRule.query.filter_by(machine_id=machine_id, alert_type=normalized_type).first()
    if not rule:
        rule = AlertSuppressionRule(machine_id=machine_id, alert_type=normalized_type)
        db.session.add(rule)
        db.session.flush()
    return rule


def get_adaptive_threshold(machine_id: int, alert_type: str, baseline: Optional[float]) -> Optional[float]:
    if baseline is None:
        return None
    rule = _get_rule(machine_id, alert_type)
    if not rule.adaptive_threshold:
        return baseline
    return baseline * rule.adaptive_threshold


def should_suppress(machine_id: int, alert_type: str) -> bool:
    rule = _get_rule(machine_id, alert_type)
    window_start = datetime.utcnow() - timedelta(minutes=rule.suppression_window_minutes or 10)
    count = (
        Alert.query.filter_by(machine_id=machine_id, alert_type=alert_type.lower())
        .filter(Alert.created_at >= window_start)
        .count()
    )
    if count >= rule.max_trigger_count:
        log_action("alert_suppressed", "alert", None, company_id=None, plant_id=None, new_value={"machine_id": machine_id, "alert_type": alert_type})
        return True
    return False


def record_trigger(machine_id: int, alert_type: str, severity: str) -> None:
    rule = _get_rule(machine_id, alert_type)
    window_start = datetime.utcnow() - timedelta(hours=24)
    recent_count = (
        Alert.query.filter_by(machine_id=machine_id, alert_type=alert_type.lower())
        .filter(Alert.created_at >= window_start)
        .count()
    )
    severity_upper = (severity or "LOW").upper()
    baseline = rule.adaptive_threshold or 1.0
    if severity_upper in {"LOW", "MEDIUM"} and recent_count >= rule.max_trigger_count:
        rule.adaptive_threshold = min(baseline * 1.05, 1.5)
    elif severity_upper in {"HIGH", "CRITICAL"} and recent_count < rule.max_trigger_count:
        rule.adaptive_threshold = max(baseline * 0.95, 0.5)
    db.session.add(rule)
