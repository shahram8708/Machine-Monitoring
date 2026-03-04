from __future__ import annotations

from app.extensions import db


class EscalationRule(db.Model):
    __tablename__ = "escalation_rules"
    __table_args__ = (
        db.UniqueConstraint("company_id", "severity", name="uq_escalation_company_severity"),
        db.Index("ix_escalation_company", "company_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    severity = db.Column(db.String(20), nullable=False)
    escalation_time_minutes = db.Column(db.Integer, nullable=False)
    next_role_to_notify = db.Column(db.String(80), nullable=False)

    company = db.relationship("Company")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<EscalationRule company={self.company_id} severity={self.severity} minutes={self.escalation_time_minutes}>"
