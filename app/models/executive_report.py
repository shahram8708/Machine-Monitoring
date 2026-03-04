from __future__ import annotations

from datetime import datetime

from app.extensions import db


class ExecutiveReport(db.Model):
    __tablename__ = "executive_reports"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    report_path = db.Column(db.String(512), nullable=False)
    summary_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    company = db.relationship("Company", backref=db.backref("executive_reports", cascade="all, delete-orphan"))
    user = db.relationship("User", backref=db.backref("executive_reports", cascade="all, delete-orphan"))
