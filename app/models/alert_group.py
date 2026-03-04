from __future__ import annotations

from datetime import datetime
from app.extensions import db


class AlertGroup(db.Model):
    __tablename__ = "alert_groups"
    __table_args__ = (
        db.Index("ix_alert_group_machine", "machine_id"),
        db.Index("ix_alert_group_created", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False, index=True)
    group_reason = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    machine = db.relationship("Machine")
    alerts = db.relationship("Alert", back_populates="group", lazy="select")
    root_causes = db.relationship(
        "RootCauseAnalysis", back_populates="alert_group", cascade="all, delete-orphan", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<AlertGroup machine={self.machine_id} reason={self.group_reason}>"
