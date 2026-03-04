from datetime import datetime, date
from app.extensions import db


class MachineKPI(db.Model):
    __tablename__ = "machine_kpis"
    __table_args__ = (
        db.UniqueConstraint("machine_id", "date", name="uq_machine_kpi_date"),
        db.Index("ix_kpi_machine_date", "machine_id", "date"),
        db.Index("ix_kpi_plant_date", "plant_id", "date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey("plants.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    oee = db.Column(db.Float, nullable=False, default=0)
    availability = db.Column(db.Float, nullable=False, default=0)
    performance = db.Column(db.Float, nullable=False, default=0)
    quality = db.Column(db.Float, nullable=False, default=0)
    utilization_rate = db.Column(db.Float, nullable=False, default=0)
    energy_efficiency = db.Column(db.Float, nullable=False, default=0)
    downtime_minutes = db.Column(db.Float, nullable=False, default=0)
    cost_of_downtime = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    machine = db.relationship("Machine", back_populates="kpis")
    plant = db.relationship("Plant")

    def __repr__(self) -> str:
        return f"<MachineKPI machine={self.machine_id} date={self.date} oee={self.oee}>"
