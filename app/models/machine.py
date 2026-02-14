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
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_name = db.Column(db.String(120), nullable=False)
    machine_type = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120))
    installation_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, default="idle")
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    api_token = db.Column(db.String(128), unique=True, nullable=False, default=generate_secure_token)
    last_seen = db.Column(db.DateTime, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    company = db.relationship("Company", back_populates="machines")
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

    def __repr__(self) -> str:
        return f"<Machine {self.machine_name}>"
