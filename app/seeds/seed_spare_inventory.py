from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Plant, SpareInventory, SparePart

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
    "name": "spare_inventory",
    "order": 420,
    "description": "Spare parts stock levels per plant",
}


def run():
    now = ANCHOR_NOW
    parts = {p.part_code: p for p in SparePart.query.all()}
    plants = {p.plant_code: p for p in Plant.query.all()}

    inventory_rows = [
        {
            "part_code": "AP-SPD-BRG-6205",
            "plant_code": "AP-PUN",
            "current_stock": 24,
            "minimum_required_stock": 10,
            "last_updated": _clamp_dt(now - timedelta(days=20)),
        },
        {
            "part_code": "AP-SPD-BRG-6205",
            "plant_code": "AP-MAA",
            "current_stock": 16,
            "minimum_required_stock": 8,
            "last_updated": _clamp_dt(now - timedelta(days=18)),
        },
        {
            "part_code": "AP-CLT-PMP-03",
            "plant_code": "AP-PUN",
            "current_stock": 8,
            "minimum_required_stock": 4,
            "last_updated": _clamp_dt(now - timedelta(days=25)),
        },
        {
            "part_code": "NW-HYD-SEAL-300",
            "plant_code": "NW-AHD",
            "current_stock": 45,
            "minimum_required_stock": 20,
            "last_updated": _clamp_dt(now - timedelta(days=15)),
        },
        {
            "part_code": "EV-HTR-01",
            "plant_code": "EV-NOI",
            "current_stock": 30,
            "minimum_required_stock": 12,
            "last_updated": _clamp_dt(now - timedelta(days=12)),
        },
    ]

    for row in inventory_rows:
        part = parts.get(row["part_code"])
        plant = plants.get(row["plant_code"])
        if not part or not plant:
            continue
        inv = SpareInventory.query.filter_by(spare_part_id=part.id, plant_id=plant.id).first()
        payload = {
            "spare_part_id": part.id,
            "plant_id": plant.id,
            "current_stock": row["current_stock"],
            "minimum_required_stock": row["minimum_required_stock"],
            "last_updated": row["last_updated"],
        }
        if not inv:
            inv = SpareInventory(**payload)
            db.session.add(inv)
        else:
            for field, value in payload.items():
                setattr(inv, field, value)
