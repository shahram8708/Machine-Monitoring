from __future__ import annotations

from datetime import datetime
from app.extensions import db


class AlertSuppressionRule(db.Model):
    __tablename__ = "alert_suppression_rules"
    __table_args__ = (
        db.Index("ix_suppression_machine", "machine_id"),
        db.Index("ix_suppression_alert_type", "alert_type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False, index=True)
    alert_type = db.Column(db.String(80), nullable=False)
    suppression_window_minutes = db.Column(db.Integer, nullable=False, default=10)
    max_trigger_count = db.Column(db.Integer, nullable=False, default=3)
    adaptive_threshold = db.Column(db.Float, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    machine = db.relationship("Machine")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<AlertSuppressionRule machine={self.machine_id} type={self.alert_type}>"
