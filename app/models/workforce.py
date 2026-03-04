from __future__ import annotations

from datetime import datetime

from app.extensions import db


class TechnicianPerformance(db.Model):
    __tablename__ = "technician_performance"
    __table_args__ = (
        db.UniqueConstraint("user_id", "plant_id", name="uq_tech_perf_user_plant"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey("plants.id"), nullable=False, index=True)
    total_tasks_completed = db.Column(db.Integer, nullable=False, default=0)
    avg_resolution_time = db.Column(db.Float, nullable=True)
    sla_compliance_rate = db.Column(db.Float, nullable=True)
    efficiency_score = db.Column(db.Float, nullable=True)
    rework_rate = db.Column(db.Float, nullable=True, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("technician_performance", cascade="all, delete-orphan"))
    plant = db.relationship("Plant", backref=db.backref("technician_performances", cascade="all, delete-orphan"))


class MaintenanceTask(db.Model):
    __tablename__ = "maintenance_tasks"

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False, index=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    assigned_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=False, default="open")
    priority = db.Column(db.String(50), nullable=True)
    delay_minutes = db.Column(db.Integer, nullable=True)
    sla_minutes = db.Column(db.Integer, nullable=True)
    skill_tags = db.Column(db.String(255), nullable=True)

    machine = db.relationship("Machine", backref=db.backref("maintenance_tasks", cascade="all, delete-orphan"))
    assignee = db.relationship("User", backref=db.backref("maintenance_tasks", cascade="all, delete-orphan"))
