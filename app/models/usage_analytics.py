from datetime import date
from app.extensions import db


class UsageMetric(db.Model):
    __tablename__ = "usage_metrics"
    __table_args__ = (
        db.Index("ix_usage_company_metric", "company_id", "metric_type", "date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    metric_type = db.Column(db.String(80), nullable=False)
    count = db.Column(db.Integer, nullable=False, default=0)
    date = db.Column(db.Date, nullable=False, default=date.today)

    def __repr__(self) -> str:  # pragma: no cover - repr only
        return f"<UsageMetric {self.metric_type} company={self.company_id} date={self.date}>"
