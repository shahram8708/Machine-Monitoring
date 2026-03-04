from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Company, Plant

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
    "name": "plants",
    "order": 140,
    "description": "Production plants for each company",
}


def run():
    now = ANCHOR_NOW
    plants = [
        {
            "company_name": "Aurora Precision Systems",
            "name": "Aurora Pune Plant",
            "plant_code": "AP-PUN",
            "location": "Pimpri-Chinchwad, Pune, IN",
            "operational_status": "operational",
            "annual_capacity_units": 180000,
            "created_at": _clamp_dt(now - timedelta(days=280)),
        },
        {
            "company_name": "Aurora Precision Systems",
            "name": "Aurora Chennai Plant",
            "plant_code": "AP-MAA",
            "location": "Sriperumbudur, Chennai, IN",
            "operational_status": "operational",
            "annual_capacity_units": 150000,
            "created_at": _clamp_dt(now - timedelta(days=240)),
        },
        {
            "company_name": "Northwind Automotive Components",
            "name": "Northwind Ahmedabad Plant",
            "plant_code": "NW-AHD",
            "location": "Sanand, Ahmedabad, IN",
            "operational_status": "operational",
            "annual_capacity_units": 210000,
            "created_at": _clamp_dt(now - timedelta(days=220)),
        },
        {
            "company_name": "Evergreen Food Machinery",
            "name": "Evergreen Noida Plant",
            "plant_code": "EV-NOI",
            "location": "Sector 63, Noida, IN",
            "operational_status": "operational",
            "annual_capacity_units": 95000,
            "created_at": _clamp_dt(now - timedelta(days=160)),
        },
    ]

    companies = {c.company_name: c for c in Company.query.filter(Company.company_name.in_({p["company_name"] for p in plants}))}

    for data in plants:
        company = companies.get(data["company_name"])
        if not company:
            continue
        plant = Plant.query.filter_by(company_id=company.id, plant_code=data["plant_code"]).first()
        payload = {
            "company_id": company.id,
            "name": data["name"],
            "plant_code": data["plant_code"],
            "location": data["location"],
            "operational_status": data["operational_status"],
            "annual_capacity_units": data["annual_capacity_units"],
            "created_at": data["created_at"],
        }
        if not plant:
            plant = Plant(**payload)
            db.session.add(plant)
        else:
            plant.name = payload["name"]
            plant.location = payload["location"]
            plant.operational_status = payload["operational_status"]
            plant.annual_capacity_units = payload["annual_capacity_units"]
            plant.created_at = plant.created_at or payload["created_at"]
