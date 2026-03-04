from datetime import datetime
from app.extensions import db


class MachineHealthScore(db.Model):
    __tablename__ = "machine_health_scores"
    __table_args__ = (
        db.UniqueConstraint("machine_id", "calculated_at", name="uq_machine_health_ts"),
        db.Index("ix_health_machine_ts", "machine_id", "calculated_at"),
        db.Index("ix_health_plant_ts", "plant_id", "calculated_at"),
        db.Index("ix_health_company_ts", "company_id", "calculated_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey("plants.id"), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    health_score = db.Column(db.Float, nullable=False, default=0)
    risk_level = db.Column(db.String(20), nullable=False, default="LOW")
    calculated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    machine = db.relationship("Machine", back_populates="health_scores")
    plant = db.relationship("Plant")
    company = db.relationship("Company")

    def __repr__(self) -> str:
        return f"<MachineHealthScore machine={self.machine_id} score={self.health_score}>"
