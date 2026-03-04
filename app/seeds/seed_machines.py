from datetime import date, datetime, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import Company, Department, Machine, Plant

MIN_DATE = date(2026, 3, 1)
MAX_DATE = date(2026, 3, 3)
ANCHOR_NOW = datetime(2026, 3, 3, 12, 0, 0)


def _clamp_date(value: date) -> date:
    if value < MIN_DATE:
        return MIN_DATE
    if value > MAX_DATE:
        return MAX_DATE
    return value


def _clamp_dt(value: datetime) -> datetime:
    if value.date() < MIN_DATE:
        return value.replace(year=2026, month=3, day=1)
    if value.date() > MAX_DATE:
        return value.replace(year=2026, month=3, day=3)
    return value


SEED_METADATA = {
    "name": "machines",
    "order": 240,
    "description": "Installed machines across plants",
}


def run():
    companies = {c.company_name: c for c in Company.query.all()}
    plants = {p.plant_code: p for p in Plant.query.all()}
    departments = {(d.plant_id, d.name): d for d in Department.query.all()}

    machines = [
        {
            "company": "Aurora Precision Systems",
            "plant_code": "AP-PUN",
            "department_name": "Production",
            "machine_name": "APX-500 CNC Lathe",
            "machine_type": "CNC Lathe",
            "machine_code": "AP-PUN-LATHE-01",
            "model_number": "APX-500",
            "location": "Line A - Bay 3",
            "installation_date": _clamp_date(MAX_DATE - timedelta(days=720)),
            "status": "running",
            "operational_state": "ready",
            "cost_per_hour": Decimal("1450.00"),
            "revenue_per_hour": Decimal("3650.00"),
            "expected_lifetime_hours": 32000,
            "last_seen": _clamp_dt(ANCHOR_NOW - timedelta(minutes=10)),
        },
        {
            "company": "Aurora Precision Systems",
            "plant_code": "AP-MAA",
            "department_name": "Production",
            "machine_name": "APX-900 Milling Center",
            "machine_type": "5-Axis Mill",
            "machine_code": "AP-MAA-MILL-01",
            "model_number": "APX-900",
            "location": "Line B - Cell 2",
            "installation_date": _clamp_date(MAX_DATE - timedelta(days=540)),
            "status": "running",
            "operational_state": "ready",
            "cost_per_hour": Decimal("1750.00"),
            "revenue_per_hour": Decimal("4250.00"),
            "expected_lifetime_hours": 28000,
            "last_seen": _clamp_dt(ANCHOR_NOW - timedelta(minutes=5)),
        },
        {
            "company": "Northwind Automotive Components",
            "plant_code": "NW-AHD",
            "department_name": "Body Shop",
            "machine_name": "NW Stamp 300T Press",
            "machine_type": "Hydraulic Press",
            "machine_code": "NW-AHD-PRESS-01",
            "model_number": "NW-Stamp-300",
            "location": "Press Line 1",
            "installation_date": _clamp_date(MAX_DATE - timedelta(days=620)),
            "status": "running",
            "operational_state": "ready",
            "cost_per_hour": Decimal("2100.00"),
            "revenue_per_hour": Decimal("5100.00"),
            "expected_lifetime_hours": 36000,
            "last_seen": _clamp_dt(ANCHOR_NOW - timedelta(minutes=15)),
        },
        {
            "company": "Evergreen Food Machinery",
            "plant_code": "EV-NOI",
            "department_name": "Packaging",
            "machine_name": "EV Packer 12",
            "machine_type": "Form-Fill-Seal",
            "machine_code": "EV-NOI-PACK-01",
            "model_number": "EV-PKR-12",
            "location": "Packaging Hall",
            "installation_date": _clamp_date(MAX_DATE - timedelta(days=480)),
            "status": "idle",
            "operational_state": "ready",
            "cost_per_hour": Decimal("950.00"),
            "revenue_per_hour": Decimal("2450.00"),
            "expected_lifetime_hours": 26000,
            "last_seen": _clamp_dt(ANCHOR_NOW - timedelta(hours=3)),
        },
    ]

    for data in machines:
        company = companies.get(data["company"])
        plant = plants.get(data["plant_code"])
        dept = departments.get((plant.id, data["department_name"])) if plant else None
        if not company or not plant:
            continue
        machine = Machine.query.filter_by(company_id=company.id, machine_code=data["machine_code"]).first()
        payload = {
            "machine_name": data["machine_name"],
            "machine_type": data["machine_type"],
            "machine_code": data["machine_code"],
            "model_number": data["model_number"],
            "location": data["location"],
            "installation_date": data["installation_date"],
            "status": data["status"],
            "operational_state": data["operational_state"],
            "company_id": company.id,
            "plant_id": plant.id,
            "department_id": dept.id if dept else None,
            "cost_per_hour": data["cost_per_hour"],
            "revenue_per_hour": data["revenue_per_hour"],
            "expected_lifetime_hours": data["expected_lifetime_hours"],
            "last_seen": data["last_seen"],
        }
        if not machine:
            machine = Machine(**payload)
            db.session.add(machine)
        else:
            for field, value in payload.items():
                setattr(machine, field, value)
