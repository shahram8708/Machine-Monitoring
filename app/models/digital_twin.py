from datetime import datetime
from app.extensions import db


class DigitalTwin(db.Model):
    __tablename__ = "digital_twins"
    __table_args__ = (
        db.Index("ix_twin_machine", "machine_id"),
        db.Index("ix_twin_plant", "plant_id"),
        db.Index("ix_twin_company", "company_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False)
    plant_id = db.Column(db.Integer, db.ForeignKey("plants.id"), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    baseline_oee = db.Column(db.Float, nullable=False, default=0)
    baseline_health_score = db.Column(db.Float, nullable=False, default=0)
    baseline_failure_probability = db.Column(db.Float, nullable=False, default=0)
    baseline_energy_efficiency = db.Column(db.Float, nullable=False, default=0)
    degradation_rate = db.Column(db.Float, nullable=False, default=0)
    configuration_json = db.Column(db.JSON)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    machine = db.relationship("Machine", back_populates="digital_twin")
    plant = db.relationship("Plant")
    company = db.relationship("Company")
    simulations = db.relationship(
        "TwinSimulationHistory",
        back_populates="digital_twin",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class TwinSimulationHistory(db.Model):
    __tablename__ = "twin_simulation_history"
    __table_args__ = (
        db.Index("ix_twin_history_twin_ts", "digital_twin_id", "created_at"),
        db.Index("ix_twin_history_type", "simulation_type"),
    )

    id = db.Column(db.Integer, primary_key=True)
    digital_twin_id = db.Column(db.Integer, db.ForeignKey("digital_twins.id"), nullable=False, index=True)
    simulation_type = db.Column(db.String(64), nullable=False)
    input_parameters = db.Column(db.JSON)
    simulated_oee = db.Column(db.Float, nullable=False, default=0)
    simulated_failure_probability = db.Column(db.Float, nullable=False, default=0)
    simulated_health_score = db.Column(db.Float, nullable=False, default=0)
    simulated_energy_efficiency = db.Column(db.Float, nullable=False, default=0)
    risk_delta = db.Column(db.Float, nullable=False, default=0)
    impact_level = db.Column(db.String(16), nullable=False, default="LOW")
    ai_analysis = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    digital_twin = db.relationship("DigitalTwin", back_populates="simulations")
