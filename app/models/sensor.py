from datetime import datetime
from app.extensions import db


class Sensor(db.Model):
    __tablename__ = "sensors"

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False, index=True)
    sensor_type = db.Column(db.String(50), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    min_threshold = db.Column(db.Float, nullable=False)
    max_threshold = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    machine = db.relationship("Machine", back_populates="sensors")

    def __repr__(self) -> str:
        return f"<Sensor {self.sensor_type} ({self.unit})>"
