from __future__ import annotations

from datetime import datetime
from app.extensions import db

ALERT_SEVERITIES = ("low", "medium", "high", "critical")


class Alert(db.Model):
    __tablename__ = "alerts"
    __table_args__ = (
        db.Index("ix_alert_machine_created", "machine_id", "created_at"),
        db.Index("ix_alert_company_resolved", "company_id", "is_resolved"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    sensor_type = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Float)
    threshold = db.Column(db.Float)
    severity = db.Column(db.String(20), nullable=False, default="low")
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_resolved = db.Column(db.Boolean, default=False, nullable=False)
    resolved_at = db.Column(db.DateTime)
    escalation_level = db.Column(db.Integer, default=1, nullable=False)
    last_escalated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    machine = db.relationship("Machine", back_populates="alerts")
    company = db.relationship("Company")
    timelines = db.relationship(
        "AlertTimeline", back_populates="alert", cascade="all, delete-orphan", order_by="AlertTimeline.created_at"
    )

    def __repr__(self) -> str:
        return f"<Alert machine={self.machine_id} severity={self.severity} resolved={self.is_resolved}>"


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
