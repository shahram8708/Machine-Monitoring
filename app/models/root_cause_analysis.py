from __future__ import annotations

from datetime import datetime
from app.extensions import db


class RootCauseAnalysis(db.Model):
    __tablename__ = "root_cause_analyses"
    __table_args__ = (
        db.Index("ix_rca_machine", "machine_id"),
        db.Index("ix_rca_alert_group", "alert_group_id"),
        db.Index("ix_rca_created", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False, index=True)
    alert_group_id = db.Column(db.Integer, db.ForeignKey("alert_groups.id"), nullable=False, index=True)
    primary_root_cause = db.Column(db.String(255), nullable=False)
    contributing_factors = db.Column(db.JSON, nullable=True)
    probability_breakdown = db.Column(db.JSON, nullable=True)
    timeline_explanation = db.Column(db.Text, nullable=True)
    sensor_interactions = db.Column(db.Text, nullable=True)
    confidence_score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    machine = db.relationship("Machine")
    alert_group = db.relationship("AlertGroup", back_populates="root_causes")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<RootCauseAnalysis machine={self.machine_id} alert_group={self.alert_group_id}>"
