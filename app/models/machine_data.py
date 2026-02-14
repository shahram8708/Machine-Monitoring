from datetime import datetime, timedelta
from typing import List, Optional
from app.extensions import db


class MachineData(db.Model):
    __tablename__ = "machine_data"
    __table_args__ = (
        db.Index("ix_machine_data_machine_ts", "machine_id", "timestamp"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    temperature = db.Column(db.Float)
    vibration = db.Column(db.Float)
    current = db.Column(db.Float)
    voltage = db.Column(db.Float)
    pressure = db.Column(db.Float)
    humidity = db.Column(db.Float)
    speed = db.Column(db.Float)
    running_status = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    machine = db.relationship("Machine", back_populates="data_points")

    def __repr__(self) -> str:
        return f"<MachineData machine={self.machine_id} ts={self.timestamp.isoformat()}>"


def get_latest_machine_data(machine_id: int) -> Optional["MachineData"]:
    return (
        MachineData.query.filter_by(machine_id=machine_id)
        .order_by(MachineData.timestamp.desc())
        .first()
    )


def get_last_1_hour_data(machine_id: int) -> List["MachineData"]:
    cutoff = datetime.utcnow() - timedelta(hours=1)
    return (
        MachineData.query.filter_by(machine_id=machine_id)
        .filter(MachineData.timestamp >= cutoff)
        .order_by(MachineData.timestamp.asc())
        .all()
    )
