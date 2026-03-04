from datetime import datetime
from app.extensions import db


class AdvancedReport(db.Model):
    __tablename__ = "advanced_reports"
    __table_args__ = (
        db.Index("ix_adv_reports_company", "company_id"),
        db.Index("ix_adv_reports_type", "report_type"),
        db.Index("ix_adv_reports_generated_at", "generated_at"),
        db.Index("ix_adv_reports_company_type", "company_id", "report_type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    report_type = db.Column(db.String(80), nullable=False)
    report_data = db.Column(db.JSON, nullable=False)
    generated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    file_path = db.Column(db.String(255))
    format = db.Column(db.String(20), nullable=False, default="PDF")

    # Relationship from Company.advanced_reports backref already provides .company
    user = db.relationship("User")

    def __repr__(self) -> str:  # pragma: no cover - repr only
        return f"<AdvancedReport {self.report_type} company={self.company_id}>"
