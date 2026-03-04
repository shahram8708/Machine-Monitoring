from datetime import datetime
from app.extensions import db


class AIPrediction(db.Model):
    __tablename__ = "ai_predictions"
    __table_args__ = (
        db.Index("ix_ai_pred_machine_ts", "machine_id", "created_at"),
        db.Index("ix_ai_pred_plant_ts", "plant_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey("plants.id"), nullable=True, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    failure_probability = db.Column(db.Float, nullable=False, default=0)
    remaining_useful_life_hours = db.Column(db.Float, nullable=True)
    degradation_score = db.Column(db.Float, nullable=True)
    anomaly_score = db.Column(db.Float, nullable=True)
    risk_level = db.Column(db.String(20), nullable=False, default="LOW")
    early_warning_flag = db.Column(db.Boolean, nullable=False, default=False)
    ai_explanation = db.Column(db.JSON)
    confidence_score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Machine.ai_predictions provides backref=machine
    plant = db.relationship("Plant")

    def __repr__(self) -> str:  # pragma: no cover - simple repr
        return f"<AIPrediction machine={self.machine_id} risk={self.risk_level}>"
