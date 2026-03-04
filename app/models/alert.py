from __future__ import annotations

from datetime import datetime
from app.extensions import db

ALERT_SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
ALERT_STATUSES = ("OPEN", "ACKNOWLEDGED", "RESOLVED", "ESCALATED")


class Alert(db.Model):
    __tablename__ = "alerts"
    __table_args__ = (
        db.Index("ix_alert_machine_created", "machine_id", "created_at"),
        db.Index("ix_alert_company_resolved", "company_id", "status"),
        db.Index("ix_alert_machine", "machine_id"),
        db.Index("ix_alert_plant", "plant_id"),
        db.Index("ix_alert_status", "status"),
        db.Index("ix_alert_severity", "severity"),
        db.Index("ix_alert_created", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey("plants.id"), nullable=True, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    alert_type = db.Column(db.String(80), nullable=False)
    severity = db.Column(db.String(20), nullable=False, default="LOW")
    priority_score = db.Column(db.Float, nullable=True)
    grouped_alert_id = db.Column(db.Integer, db.ForeignKey("alert_groups.id"), nullable=True)
    sla_deadline = db.Column(db.DateTime, nullable=True)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    escalation_level = db.Column(db.Integer, default=0, nullable=False)
    response_time_minutes = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="OPEN")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # legacy compatibility
    sensor_type = db.Column(db.String(50), nullable=True)
    value = db.Column(db.Float)
    threshold = db.Column(db.Float)
    message = db.Column(db.Text, nullable=False)
    is_resolved = db.Column(db.Boolean, default=False, nullable=False)
    last_escalated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    metadata_payload = db.Column(db.JSON, nullable=True)

    machine = db.relationship("Machine", back_populates="alerts")
    company = db.relationship("Company")
    plant = db.relationship("Plant")
    timelines = db.relationship(
        "AlertTimeline", back_populates="alert", cascade="all, delete-orphan", order_by="AlertTimeline.created_at"
    )
    group = db.relationship("AlertGroup", back_populates="alerts")

    def mark_status(self, status: str) -> None:
        status = (status or "OPEN").upper()
        if status not in ALERT_STATUSES:
            status = "OPEN"
        self.status = status
        self.is_resolved = status == "RESOLVED"

    def __repr__(self) -> str:
        return f"<Alert machine={self.machine_id} severity={self.severity} status={self.status}>"


class AlertTimeline(db.Model):
    __tablename__ = "alert_timelines"

    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer, db.ForeignKey("alerts.id"), nullable=False, index=True)
    event = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20))
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    alert = db.relationship("Alert", back_populates="timelines")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<AlertTimeline alert={self.alert_id} event={self.event}>"
