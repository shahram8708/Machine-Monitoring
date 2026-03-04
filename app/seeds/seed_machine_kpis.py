from datetime import date, datetime, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import Machine, MachineKPI

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
    "name": "machine_kpis",
    "order": 290,
    "description": "Daily OEE and performance KPIs",
}


def run():
    machines = {m.machine_code: m for m in Machine.query.all()}
    base_date = _clamp_date(MAX_DATE - timedelta(days=1))

    kpis = {
        "AP-PUN-LATHE-01": {
            "oee": 0.86,
            "availability": 0.91,
            "performance": 0.92,
            "quality": 0.98,
            "utilization_rate": 0.88,
            "energy_efficiency": 0.82,
            "downtime_minutes": 180,
            "cost_of_downtime": Decimal("26500.00"),
        },
        "AP-MAA-MILL-01": {
            "oee": 0.83,
            "availability": 0.89,
            "performance": 0.90,
            "quality": 0.96,
            "utilization_rate": 0.86,
            "energy_efficiency": 0.79,
            "downtime_minutes": 210,
            "cost_of_downtime": Decimal("31800.00"),
        },
        "NW-AHD-PRESS-01": {
            "oee": 0.78,
            "availability": 0.85,
            "performance": 0.88,
            "quality": 0.95,
            "utilization_rate": 0.82,
            "energy_efficiency": 0.75,
            "downtime_minutes": 260,
            "cost_of_downtime": Decimal("41200.00"),
        },
        "EV-NOI-PACK-01": {
            "oee": 0.72,
            "availability": 0.80,
            "performance": 0.86,
            "quality": 0.97,
            "utilization_rate": 0.74,
            "energy_efficiency": 0.70,
            "downtime_minutes": 320,
            "cost_of_downtime": Decimal("15800.00"),
        },
    }

    for machine_code, values in kpis.items():
        machine = machines.get(machine_code)
        if not machine:
            continue
        row = MachineKPI.query.filter_by(machine_id=machine.id, date=base_date).first()
        if not row:
            row = MachineKPI(
                machine_id=machine.id,
                plant_id=machine.plant_id,
                date=base_date,
                oee=values["oee"],
                availability=values["availability"],
                performance=values["performance"],
                quality=values["quality"],
                utilization_rate=values["utilization_rate"],
                energy_efficiency=values["energy_efficiency"],
                downtime_minutes=values["downtime_minutes"],
                cost_of_downtime=values["cost_of_downtime"],
                created_at=_clamp_dt(ANCHOR_NOW),
            )
            db.session.add(row)
        else:
            for field, value in values.items():
                setattr(row, field, value)
            row.plant_id = machine.plant_id
            row.created_at = _clamp_dt(row.created_at or ANCHOR_NOW)
