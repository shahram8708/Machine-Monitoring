from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Machine, MachineHourlyStat

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
    "name": "machine_hourly_stats",
    "order": 270,
    "description": "Hourly aggregated telemetry",
}


def run():
    now = ANCHOR_NOW.replace(minute=0, second=0, microsecond=0)
    machines = {m.machine_code: m for m in Machine.query.all()}

    stats = {
        "AP-PUN-LATHE-01": [
            {"temp": 60.1, "vib": 5.0, "volt": 400, "curr": 37.5, "energy": 21.4, "run": 3200, "idle": 400, "points": 48},
            {"temp": 59.4, "vib": 4.8, "volt": 399, "curr": 36.8, "energy": 20.1, "run": 3000, "idle": 600, "points": 46},
            {"temp": 58.8, "vib": 4.6, "volt": 398, "curr": 36.0, "energy": 19.6, "run": 2900, "idle": 700, "points": 45},
        ],
        "AP-MAA-MILL-01": [
            {"temp": 53.8, "vib": 4.1, "volt": 410, "curr": 43.2, "energy": 24.8, "run": 3300, "idle": 300, "points": 50},
            {"temp": 53.1, "vib": 4.0, "volt": 409, "curr": 42.4, "energy": 23.9, "run": 3200, "idle": 400, "points": 49},
            {"temp": 52.6, "vib": 3.9, "volt": 409, "curr": 41.9, "energy": 23.1, "run": 3150, "idle": 450, "points": 47},
        ],
        "NW-AHD-PRESS-01": [
            {"temp": 50.2, "vib": 7.2, "volt": 404, "curr": 61.1, "energy": 35.5, "run": 3100, "idle": 500, "points": 44},
            {"temp": 49.7, "vib": 7.0, "volt": 403, "curr": 60.5, "energy": 34.8, "run": 3000, "idle": 600, "points": 43},
            {"temp": 49.0, "vib": 6.8, "volt": 402, "curr": 59.7, "energy": 33.9, "run": 2950, "idle": 650, "points": 42},
        ],
        "EV-NOI-PACK-01": [
            {"temp": 29.1, "vib": 1.5, "volt": 393, "curr": 19.0, "energy": 11.2, "run": 2500, "idle": 1100, "points": 41},
            {"temp": 28.7, "vib": 1.5, "volt": 393, "curr": 18.6, "energy": 10.7, "run": 2400, "idle": 1200, "points": 39},
            {"temp": 28.2, "vib": 1.4, "volt": 392, "curr": 18.2, "energy": 10.3, "run": 2300, "idle": 1300, "points": 38},
        ],
    }

    for machine_code, rows in stats.items():
        machine = machines.get(machine_code)
        if not machine:
            continue
        for idx, row in enumerate(rows):
            period_start = _clamp_dt(now - timedelta(hours=idx + 1))
            period_end = _clamp_dt(period_start + timedelta(hours=1))
            stat = MachineHourlyStat.query.filter_by(machine_id=machine.id, period_start=period_start).first()
            if not stat:
                stat = MachineHourlyStat(
                    machine_id=machine.id,
                    period_start=period_start,
                    period_end=period_end,
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
