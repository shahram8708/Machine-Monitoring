from datetime import datetime
from app.extensions import db


class AiAnalysis(db.Model):
    __tablename__ = "ai_analysis"
    __table_args__ = (
        db.Index("ix_ai_machine_created", "machine_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    health_score = db.Column(db.Float)
    risk_level = db.Column(db.String(16))
    anomaly = db.Column(db.Boolean)
    maintenance_suggestion = db.Column(db.Text)
    explanation = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    machine = db.relationship("Machine", back_populates="ai_analyses")

    def __repr__(self) -> str:
        return f"<AiAnalysis machine={self.machine_id} status={self.status}>"
