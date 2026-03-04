import secrets
from datetime import datetime
from app.extensions import db


def generate_secure_token() -> str:
    """Generate a URL-safe API token for machine authentication."""
    return secrets.token_urlsafe(32)


class Machine(db.Model):
    __tablename__ = "machines"
    __table_args__ = (
        db.UniqueConstraint("machine_name", "company_id", name="uq_machine_company_name"),
        db.UniqueConstraint("plant_id", "machine_code", name="uq_machine_code_per_plant"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_name = db.Column(db.String(120), nullable=False)
    machine_type = db.Column(db.String(120), nullable=False)
    machine_code = db.Column(db.String(60), nullable=True)
    model_number = db.Column(db.String(80))
    location = db.Column(db.String(120))
    installation_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, default="idle")
    operational_state = db.Column(db.String(30), nullable=False, default="ready")
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey("plants.id"), nullable=True, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True, index=True)
    api_token = db.Column(db.String(128), unique=True, nullable=False, default=generate_secure_token)
    cost_per_hour = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    revenue_per_hour = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    expected_lifetime_hours = db.Column(db.Integer)
    last_seen = db.Column(db.DateTime, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    company = db.relationship("Company", back_populates="machines")
    plant = db.relationship("Plant", back_populates="machines")
    department = db.relationship("Department", back_populates="machines")
    sensors = db.relationship(
        "Sensor", back_populates="machine", cascade="all, delete-orphan", lazy="dynamic"
    )
    data_points = db.relationship(
        "MachineData", back_populates="machine", cascade="all, delete-orphan", lazy="dynamic"
    )
    ai_analyses = db.relationship(
        "AiAnalysis", back_populates="machine", cascade="all, delete-orphan", lazy="dynamic"
    )
    alerts = db.relationship(
        "Alert", back_populates="machine", cascade="all, delete-orphan", lazy="dynamic"
    )
    kpis = db.relationship(
        "MachineKPI", back_populates="machine", cascade="all, delete-orphan", lazy="dynamic"
    )
    health_scores = db.relationship(
        "MachineHealthScore", back_populates="machine", cascade="all, delete-orphan", lazy="dynamic"
    )
    ai_predictions = db.relationship(
        "AIPrediction", backref="machine", cascade="all, delete-orphan", lazy="dynamic"
    )
    digital_twin = db.relationship(
        "DigitalTwin", uselist=False, cascade="all, delete-orphan", lazy="joined", back_populates="machine"
    )

    def __repr__(self) -> str:
        return f"<Machine {self.machine_name}>"
