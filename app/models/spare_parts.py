from __future__ import annotations

from datetime import datetime

from app.extensions import db


class SparePart(db.Model):
    __tablename__ = "spare_parts"
    __table_args__ = (
        db.UniqueConstraint("part_code", "company_id", name="uq_spare_part_code_company"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    part_name = db.Column(db.String(200), nullable=False)
    part_code = db.Column(db.String(120), nullable=False)
    machine_type = db.Column(db.String(120), nullable=True)
    average_lifetime_hours = db.Column(db.Float, nullable=True)
    cost_per_unit = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    supplier_name = db.Column(db.String(200), nullable=True)
    lead_time_days = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    inventories = db.relationship("SpareInventory", back_populates="spare_part", cascade="all, delete-orphan")
    machine_mappings = db.relationship("MachineSpareMapping", back_populates="spare_part", cascade="all, delete-orphan")


class MachineSpareMapping(db.Model):
    __tablename__ = "machine_spare_mappings"
    __table_args__ = (
        db.UniqueConstraint("machine_id", "spare_part_id", name="uq_machine_spare"),
    )

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey("machines.id"), nullable=False, index=True)
    spare_part_id = db.Column(db.Integer, db.ForeignKey("spare_parts.id"), nullable=False, index=True)
    replacement_frequency_hours = db.Column(db.Float, nullable=True)
    criticality_level = db.Column(db.String(50), nullable=True)

    machine = db.relationship("Machine", backref=db.backref("spare_mappings", cascade="all, delete-orphan"))
    spare_part = db.relationship("SparePart", back_populates="machine_mappings")


class SpareInventory(db.Model):
    __tablename__ = "spare_inventory"
    __table_args__ = (
        db.UniqueConstraint("spare_part_id", "plant_id", name="uq_spare_inventory_plant"),
    )

    id = db.Column(db.Integer, primary_key=True)
    spare_part_id = db.Column(db.Integer, db.ForeignKey("spare_parts.id"), nullable=False, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey("plants.id"), nullable=False, index=True)
    current_stock = db.Column(db.Integer, nullable=False, default=0)
    minimum_required_stock = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow)

    spare_part = db.relationship("SparePart", back_populates="inventories")
    plant = db.relationship("Plant", backref=db.backref("spare_inventories", cascade="all, delete-orphan"))
