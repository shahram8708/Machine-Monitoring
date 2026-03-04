from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Machine, MachineDailyStat

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
    "name": "machine_daily_stats",
    "order": 280,
    "description": "Daily aggregated telemetry",
}


def run():
    today = MAX_DATE
    machines = {m.machine_code: m for m in Machine.query.all()}

    stats = {
        "AP-PUN-LATHE-01": [
            {"temp": 59.2, "vib": 4.9, "volt": 399, "curr": 37.1, "energy": 505.0, "run": 25800, "idle": 4200, "points": 1120},
            {"temp": 58.7, "vib": 4.8, "volt": 398, "curr": 36.5, "energy": 498.3, "run": 25200, "idle": 4800, "points": 1105},
            {"temp": 58.0, "vib": 4.7, "volt": 398, "curr": 36.1, "energy": 492.1, "run": 24900, "idle": 5100, "points": 1098},
        ],
        "AP-MAA-MILL-01": [
            {"temp": 53.2, "vib": 4.0, "volt": 409, "curr": 42.6, "energy": 532.5, "run": 26200, "idle": 3800, "points": 1150},
            {"temp": 52.8, "vib": 3.9, "volt": 409, "curr": 42.0, "energy": 527.4, "run": 25800, "idle": 4200, "points": 1140},
            {"temp": 52.3, "vib": 3.9, "volt": 408, "curr": 41.5, "energy": 520.8, "run": 25500, "idle": 4500, "points": 1125},
        ],
        "NW-AHD-PRESS-01": [
            {"temp": 49.8, "vib": 7.1, "volt": 403, "curr": 60.8, "energy": 615.4, "run": 25000, "idle": 5200, "points": 1085},
            {"temp": 49.4, "vib": 7.0, "volt": 403, "curr": 60.2, "energy": 607.2, "run": 24600, "idle": 5600, "points": 1070},
            {"temp": 49.0, "vib": 6.9, "volt": 402, "curr": 59.6, "energy": 598.7, "run": 24200, "idle": 6000, "points": 1060},
        ],
        "EV-NOI-PACK-01": [
            {"temp": 28.5, "vib": 1.5, "volt": 393, "curr": 18.8, "energy": 280.4, "run": 23200, "idle": 6400, "points": 980},
            {"temp": 28.2, "vib": 1.5, "volt": 393, "curr": 18.5, "energy": 274.1, "run": 22600, "idle": 7000, "points": 960},
            {"temp": 27.9, "vib": 1.4, "volt": 392, "curr": 18.2, "energy": 268.0, "run": 22100, "idle": 7500, "points": 940},
        ],
    }

    for machine_code, rows in stats.items():
        machine = machines.get(machine_code)
        if not machine:
            continue
        for idx, row in enumerate(rows):
            period_date = _clamp_date(today - timedelta(days=idx + 1))
            stat = MachineDailyStat.query.filter_by(machine_id=machine.id, period_date=period_date).first()
            if not stat:
                stat = MachineDailyStat(
                    machine_id=machine.id,
                    period_date=period_date,
                    temperature_avg=row["temp"],
                    vibration_avg=row["vib"],
                    voltage_avg=row["volt"],
                    current_avg=row["curr"],
                    energy_kwh=row["energy"],
                    running_seconds=row["run"],
                    idle_seconds=row["idle"],
                    data_points=row["points"],
                    created_at=_clamp_dt(ANCHOR_NOW),
                )
                db.session.add(stat)
            else:
                stat.temperature_avg = row["temp"]
                stat.vibration_avg = row["vib"]
                stat.voltage_avg = row["volt"]
                stat.current_avg = row["curr"]
                stat.energy_kwh = row["energy"]
                stat.running_seconds = row["run"]
                stat.idle_seconds = row["idle"]
                stat.data_points = row["points"]
