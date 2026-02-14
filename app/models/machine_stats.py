from datetime import datetime, date
from app.extensions import db


class MachineHourlyStat(db.Model):
    __tablename__ = "machine_hourly_stats"
    __table_args__ = (
        db.UniqueConstraint("machine_id", "period_start", name="uq_machine_hourly_period"),
        db.Index("ix_machine_hourly_machine_period", "machine_id", "period_start"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False)
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=True)
    temperature_avg = db.Column(db.Float)
    vibration_avg = db.Column(db.Float)
    voltage_avg = db.Column(db.Float)
    current_avg = db.Column(db.Float)
    energy_kwh = db.Column(db.Float)
    running_seconds = db.Column(db.Float)
    idle_seconds = db.Column(db.Float)
    data_points = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class MachineDailyStat(db.Model):
    __tablename__ = "machine_daily_stats"
    __table_args__ = (
        db.UniqueConstraint("machine_id", "period_date", name="uq_machine_daily_period"),
        db.Index("ix_machine_daily_machine_period", "machine_id", "period_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False)
    period_date = db.Column(db.Date, nullable=False)
    temperature_avg = db.Column(db.Float)
    vibration_avg = db.Column(db.Float)
    voltage_avg = db.Column(db.Float)
    current_avg = db.Column(db.Float)
    energy_kwh = db.Column(db.Float)
    running_seconds = db.Column(db.Float)
    idle_seconds = db.Column(db.Float)
    data_points = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
