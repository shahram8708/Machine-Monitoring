from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Machine, MachineData

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
    "name": "machine_data",
    "order": 260,
    "description": "Recent telemetry points for machines",
}


def _add_point(machine, ts, temperature, vibration, current, voltage, pressure, humidity, speed, running):
    ts = _clamp_dt(ts)
    row = MachineData.query.filter_by(machine_id=machine.id, timestamp=ts).first()
    if not row:
        row = MachineData(
            machine_id=machine.id,
            timestamp=ts,
            temperature=temperature,
            vibration=vibration,
            current=current,
            voltage=voltage,
            pressure=pressure,
            humidity=humidity,
            speed=speed,
            running_status=running,
            created_at=_clamp_dt(ANCHOR_NOW),
        )
        db.session.add(row)
    else:
        row.temperature = temperature
        row.vibration = vibration
        row.current = current
        row.voltage = voltage
        row.pressure = pressure
        row.humidity = humidity
        row.speed = speed
        row.running_status = running


def run():
    now = ANCHOR_NOW
    machines = {m.machine_code: m for m in Machine.query.all()}

    timeline = [
        -60, -45, -30, -15, -5,
    ]

    specs = {
        "AP-PUN-LATHE-01": {
            "temperature": [58.2, 59.0, 60.5, 62.1, 61.4],
            "vibration": [4.5, 4.8, 5.1, 5.4, 5.0],
            "current": [34, 36, 38, 39, 37],
            "voltage": [398, 400, 401, 402, 400],
            "pressure": [None, None, None, None, None],
            "humidity": [55, 54, 53, 52, 52],
            "speed": [1200, 1215, 1220, 1230, 1225],
            "running": [True, True, True, True, True],
        },
        "AP-MAA-MILL-01": {
            "temperature": [52.0, 52.4, 53.1, 53.8, 54.2],
            "vibration": [3.8, 3.9, 4.0, 4.1, 4.2],
            "current": [41, 42, 43, 44, 43],
            "voltage": [410, 409, 411, 410, 409],
            "pressure": [None, None, None, None, None],
            "humidity": [48, 48, 47, 47, 47],
            "speed": [1350, 1360, 1365, 1370, 1368],
            "running": [True, True, True, True, True],
        },
        "NW-AHD-PRESS-01": {
            "temperature": [48.5, 49.0, 49.6, 50.1, 50.3],
            "vibration": [6.5, 6.9, 7.2, 7.5, 7.1],
            "current": [58, 59, 60, 62, 61],
            "voltage": [402, 403, 405, 404, 403],
            "pressure": [185, 188, 190, 193, 191],
            "humidity": [50, 49, 48, 48, 47],
            "speed": [32, 33, 34, 35, 34],
            "running": [True, True, True, True, True],
        },
        "EV-NOI-PACK-01": {
            "temperature": [28.0, 28.5, 29.0, 29.2, 29.1],
            "vibration": [1.4, 1.5, 1.6, 1.6, 1.5],
            "current": [18, 18, 19, 19, 19],
            "voltage": [392, 393, 394, 394, 393],
            "pressure": [None, None, None, None, None],
            "humidity": [61, 60, 59, 59, 60],
            "speed": [240, 245, 250, 248, 246],
            "running": [True, True, True, True, False],
        },
    }

    for machine_code, profile in specs.items():
        machine = machines.get(machine_code)
        if not machine:
            continue
        for idx, minutes_ago in enumerate(timeline):
            ts = now + timedelta(minutes=minutes_ago)
            _add_point(
                machine,
                ts,
                profile["temperature"][idx],
                profile["vibration"][idx],
                profile["current"][idx],
                profile["voltage"][idx],
                profile["pressure"][idx],
                profile["humidity"][idx],
                profile["speed"][idx],
                profile["running"][idx],
            )
