from datetime import datetime
from app.extensions import db


class Department(db.Model):
    __tablename__ = "departments"
    __table_args__ = (
        db.UniqueConstraint("plant_id", "name", name="uq_department_name"),
        db.Index("ix_department_plant", "plant_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey("plants.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    department_type = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    plant = db.relationship("Plant", back_populates="departments")
    machines = db.relationship("Machine", back_populates="department", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Department {self.name} ({self.department_type})>"
