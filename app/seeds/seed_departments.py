from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Department, Plant

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
    "name": "departments",
    "order": 150,
    "description": "Core departments for each plant",
}


def run():
    now = ANCHOR_NOW
    department_rows = [
        ("AP-PUN", "Production", "production", _clamp_dt(now - timedelta(days=275))),
        ("AP-PUN", "Maintenance", "maintenance", _clamp_dt(now - timedelta(days=270))),
        ("AP-PUN", "Quality Assurance", "quality", _clamp_dt(now - timedelta(days=268))),
        ("AP-MAA", "Production", "production", _clamp_dt(now - timedelta(days=235))),
        ("AP-MAA", "Maintenance", "maintenance", _clamp_dt(now - timedelta(days=230))),
        ("NW-AHD", "Body Shop", "production", _clamp_dt(now - timedelta(days=210))),
        ("NW-AHD", "Maintenance", "maintenance", _clamp_dt(now - timedelta(days=208))),
        ("NW-AHD", "Quality Assurance", "quality", _clamp_dt(now - timedelta(days=206))),
        ("EV-NOI", "Processing", "production", _clamp_dt(now - timedelta(days=155))),
        ("EV-NOI", "Packaging", "production", _clamp_dt(now - timedelta(days=152))),
        ("EV-NOI", "Maintenance", "maintenance", _clamp_dt(now - timedelta(days=150))),
    ]

    plants = {p.plant_code: p for p in Plant.query.filter(Plant.plant_code.in_({row[0] for row in department_rows}))}

    for plant_code, name, dept_type, created_at in department_rows:
        plant = plants.get(plant_code)
        if not plant:
            continue
        dept = Department.query.filter_by(plant_id=plant.id, name=name).first()
        if not dept:
            dept = Department(
                plant_id=plant.id,
                name=name,
                department_type=dept_type,
                created_at=created_at,
            )
            db.session.add(dept)
        else:
            dept.department_type = dept_type
            dept.created_at = dept.created_at or created_at
