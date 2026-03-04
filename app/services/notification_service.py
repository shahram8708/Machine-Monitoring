from __future__ import annotations

import os
import logging
from typing import Iterable
import requests
from flask import url_for

from app.services.email_service import send_email

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def _email_subject(prefix: str, alert) -> str:
        machine_label = getattr(alert.machine, "machine_name", None) or f"Machine {alert.machine_id}"
        return f"{prefix}: {machine_label}"

    @staticmethod
    def _send_slack(text: str) -> None:
        webhook = os.getenv("SLACK_WEBHOOK_URL")
        if not webhook:
            return
        try:
            requests.post(webhook, json={"text": text}, timeout=5)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Slack notification failed: %s", exc)

    @staticmethod
    def _send_sms(text: str, recipients: Iterable[str]) -> None:
        # Placeholder for SMS integration (Twilio, etc.)
        _ = (text, recipients)
        logger.info("SMS placeholder invoked")

    @staticmethod
    def notify_new_alert(alert) -> None:
        subject = NotificationService._email_subject("Critical Alert", alert)
        body = f"Alert {alert.id} on machine {alert.machine.machine_name if alert.machine else alert.machine_id}: {alert.message}"
        send_email(
            subject=subject,
            recipients=_recipients_for_company(alert.company_id, critical_only=True),
            template="alert_notification",
            context={
                "subject": subject,
                "headline": "Critical alert triggered",
                "intro": "We detected a critical condition that needs immediate attention.",
                "machine_name": getattr(alert.machine, "machine_name", None),
                "machine_id": alert.machine_id,
                "plant_name": getattr(alert.plant, "plant_name", None),
                "severity": getattr(alert, "severity", "CRITICAL"),
                "message": alert.message,
                "metrics": {
                    "Alert ID": alert.id,
                    "Alert Type": alert.alert_type,
                    "Sensor": alert.sensor_type or "N/A",
                },
                "triggered_at": getattr(alert, "created_at", None),
                "action_url": _alert_link(alert),
                "current_year": _year(),
            },
        )
        NotificationService._send_slack(body)

    @staticmethod
    def notify_escalation(alert) -> None:
        subject = NotificationService._email_subject(f"Alert Escalated · L{alert.escalation_level}", alert)
        body = f"Alert {alert.id} escalated to level {alert.escalation_level}. Status: {alert.status}. Message: {alert.message}"
        send_email(
            subject=subject,
            recipients=_recipients_for_company(alert.company_id),
            template="alert_escalation",
            context={
                "subject": subject,
                "headline": "Alert escalation in progress",
                "intro": "An open alert has been escalated. Please review and act.",
                "machine_name": getattr(alert.machine, "machine_name", None),
                "machine_id": alert.machine_id,
                "plant_name": getattr(alert.plant, "plant_name", None),
                "message": alert.message,
                "status": alert.status,
                "escalation_level": alert.escalation_level,
                "triggered_at": getattr(alert, "last_escalated_at", None),
                "action_url": _alert_link(alert),
                "current_year": _year(),
            },
        )
        NotificationService._send_slack(body)

    @staticmethod
    def notify_sla_breach(alert) -> None:
        subject = NotificationService._email_subject("SLA Breach", alert)
        body = f"Alert {alert.id} breached SLA. Priority {alert.priority_score}."
        send_email(
            subject=subject,
            recipients=_recipients_for_company(alert.company_id),
            template="alert_sla_breach",
            context={
                "subject": subject,
                "headline": "SLA breached for open alert",
                "intro": "This alert exceeded its response window. Immediate remediation is required.",
                "machine_name": getattr(alert.machine, "machine_name", None),
                "machine_id": alert.machine_id,
                "plant_name": getattr(alert.plant, "plant_name", None),
                "priority_score": alert.priority_score,
                "message": alert.message,
                "sla_deadline": getattr(alert, "sla_deadline", None),
                "triggered_at": getattr(alert, "created_at", None),
                "action_url": _alert_link(alert),
                "current_year": _year(),
            },
        )
        NotificationService._send_slack(body)


def _recipients_for_company(company_id: int, critical_only: bool = False) -> list[str]:
    try:
        from app.models.user import User  # lazy import to avoid cycles
    except Exception:  # noqa: BLE001
        return []
    query = User.query.filter_by(company_id=company_id, is_active=True)
    if critical_only:
        query = query.filter(User.role.in_(["admin", "manager", "SUPER_ADMIN", "ENTERPRISE_ADMIN"]))
    return [u.email for u in query.all() if u.email]


def _company_portal_url() -> str | None:
    try:
        return url_for("alerts.list", _external=True)
    except Exception:  # noqa: BLE001
        return None


def _alert_link(alert) -> str | None:
    base = _company_portal_url()
    if not base:
        return None
    return f"{base}?alertId={getattr(alert, 'id', '')}"


def _year() -> int:
    try:
        from datetime import datetime

        return datetime.utcnow().year
    except Exception:  # noqa: BLE001
        return 2026
