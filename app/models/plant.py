from datetime import datetime
from app.extensions import db


class Plant(db.Model):
    __tablename__ = "plants"
    __table_args__ = (
        db.UniqueConstraint("company_id", "plant_code", name="uq_company_plant_code"),
        db.Index("ix_plants_company", "company_id", "plant_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(200))
    plant_code = db.Column(db.String(50), nullable=False)
    operational_status = db.Column(db.String(40), nullable=False, default="operational")
    annual_capacity_units = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    company = db.relationship("Company", back_populates="plants")
    departments = db.relationship(
        "Department", back_populates="plant", cascade="all, delete-orphan", lazy="dynamic"
    )
    machines = db.relationship("Machine", back_populates="plant", lazy="dynamic")
    user_mappings = db.relationship(
        "UserPlantMapping",
        back_populates="plant",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Plant {self.name} ({self.plant_code})>"
