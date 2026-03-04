from datetime import datetime
from app.extensions import db


class Sensor(db.Model):
    __tablename__ = "sensors"

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False, index=True)
    sensor_type = db.Column(db.String(50), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    threshold_min = db.Column(db.Float, nullable=False, default=0)
    threshold_max = db.Column(db.Float, nullable=False, default=0)
    calibration_date = db.Column(db.Date, nullable=True)
    accuracy_percentage = db.Column(db.Float, nullable=True)
    # Legacy fields retained for compatibility with existing forms and routes
    min_threshold = db.Column(db.Float, nullable=False, default=0)
    max_threshold = db.Column(db.Float, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    machine = db.relationship("Machine", back_populates="sensors")

    def __repr__(self) -> str:
        return f"<Sensor {self.sensor_type} ({self.unit})>"
