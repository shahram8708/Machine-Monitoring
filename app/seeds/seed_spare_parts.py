from decimal import Decimal
from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Company, SparePart

MIN_DATE = date(2026, 3, 1)
MAX_DATE = date(2026, 3, 3)
ANCHOR_NOW = datetime(2026, 3, 3, 12, 0, 0)


def _clamp_dt(value: datetime) -> datetime:
    if value.date() < MIN_DATE:
        return value.replace(year=2026, month=3, day=1)
    if value.date() > MAX_DATE:
        return value.replace(year=2026, month=3, day=3)
    return value


SEED_METADATA = {
    "name": "spare_parts",
    "order": 410,
    "description": "Spare parts catalog per company",
}


def run():
    now = ANCHOR_NOW
    companies = {c.company_name: c for c in Company.query.all()}

    parts = [
        {
            "company": "Aurora Precision Systems",
            "part_name": "Spindle Bearing Set",
            "part_code": "AP-SPD-BRG-6205",
            "machine_type": "CNC Lathe",
            "average_lifetime_hours": 12000,
            "cost_per_unit": Decimal("18500.00"),
            "supplier_name": "SKF India",
            "lead_time_days": 12,
            "created_at": _clamp_dt(now - timedelta(days=140)),
        },
        {
            "company": "Aurora Precision Systems",
            "part_name": "Coolant Pump",
            "part_code": "AP-CLT-PMP-03",
            "machine_type": "5-Axis Mill",
            "average_lifetime_hours": 9000,
            "cost_per_unit": Decimal("24500.00"),
            "supplier_name": "Grundfos",
            "lead_time_days": 10,
            "created_at": _clamp_dt(now - timedelta(days=135)),
        },
        {
            "company": "Northwind Automotive Components",
            "part_name": "Hydraulic Seal Kit",
            "part_code": "NW-HYD-SEAL-300",
            "machine_type": "Hydraulic Press",
            "average_lifetime_hours": 6000,
            "cost_per_unit": Decimal("7800.00"),
            "supplier_name": "Freudenberg",
            "lead_time_days": 8,
            "created_at": _clamp_dt(now - timedelta(days=150)),
        },
        {
            "company": "Evergreen Food Machinery",
            "part_name": "Heater Cartridge",
            "part_code": "EV-HTR-01",
            "machine_type": "Form-Fill-Seal",
            "average_lifetime_hours": 5000,
            "cost_per_unit": Decimal("3200.00"),
            "supplier_name": "Omega Engineering",
            "lead_time_days": 7,
            "created_at": _clamp_dt(now - timedelta(days=120)),
        },
    ]

    for data in parts:
        company = companies.get(data["company"])
        if not company:
            continue
        part = SparePart.query.filter_by(company_id=company.id, part_code=data["part_code"]).first()
        payload = {
            "company_id": company.id,
            "part_name": data["part_name"],
            "part_code": data["part_code"],
            "machine_type": data["machine_type"],
            "average_lifetime_hours": data["average_lifetime_hours"],
            "cost_per_unit": data["cost_per_unit"],
            "supplier_name": data["supplier_name"],
            "lead_time_days": data["lead_time_days"],
            "created_at": data["created_at"],
        }
        if not part:
            part = SparePart(**payload)
            db.session.add(part)
        else:
            for field, value in payload.items():
                setattr(part, field, value)
