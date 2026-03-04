from datetime import date, timedelta

MIN_DATE = date(2026, 3, 1)
MAX_DATE = date(2026, 3, 3)


def _clamp_date(value: date) -> date:
    if value < MIN_DATE:
        return MIN_DATE
    if value > MAX_DATE:
        return MAX_DATE
    return value

from app.extensions import db
from app.models import Machine, Sensor

SEED_METADATA = {
    "name": "sensors",
    "order": 250,
    "description": "Sensors configured per machine",
}


def run():
    machines = {m.machine_code: m for m in Machine.query.all()}
    base_date = MAX_DATE

    sensor_rows = {
        "AP-PUN-LATHE-01": [
            {"sensor_type": "temperature", "unit": "C", "min": 20, "max": 85, "calibration": _clamp_date(base_date - timedelta(days=45))},
            {"sensor_type": "vibration", "unit": "mm/s", "min": 0.2, "max": 12.0, "calibration": _clamp_date(base_date - timedelta(days=60))},
            {"sensor_type": "current", "unit": "A", "min": 5, "max": 65, "calibration": _clamp_date(base_date - timedelta(days=90))},
        ],
        "AP-MAA-MILL-01": [
            {"sensor_type": "temperature", "unit": "C", "min": 22, "max": 78, "calibration": _clamp_date(base_date - timedelta(days=40))},
            {"sensor_type": "vibration", "unit": "mm/s", "min": 0.3, "max": 10.5, "calibration": _clamp_date(base_date - timedelta(days=55))},
            {"sensor_type": "voltage", "unit": "V", "min": 360, "max": 430, "calibration": _clamp_date(base_date - timedelta(days=70))},
        ],
        "NW-AHD-PRESS-01": [
            {"sensor_type": "pressure", "unit": "bar", "min": 120, "max": 260, "calibration": _clamp_date(base_date - timedelta(days=35))},
            {"sensor_type": "vibration", "unit": "mm/s", "min": 0.5, "max": 15.0, "calibration": _clamp_date(base_date - timedelta(days=50))},
            {"sensor_type": "temperature", "unit": "C", "min": 18, "max": 75, "calibration": _clamp_date(base_date - timedelta(days=80))},
        ],
        "EV-NOI-PACK-01": [
            {"sensor_type": "temperature", "unit": "C", "min": 10, "max": 55, "calibration": _clamp_date(base_date - timedelta(days=25))},
            {"sensor_type": "humidity", "unit": "%RH", "min": 35, "max": 70, "calibration": _clamp_date(base_date - timedelta(days=20))},
        ],
    }

    for machine_code, sensors in sensor_rows.items():
        machine = machines.get(machine_code)
        if not machine:
            continue
        for spec in sensors:
            sensor = Sensor.query.filter_by(machine_id=machine.id, sensor_type=spec["sensor_type"], unit=spec["unit"]).first()
            payload = {
                "machine_id": machine.id,
                "sensor_type": spec["sensor_type"],
                "unit": spec["unit"],
                "threshold_min": spec["min"],
                "threshold_max": spec["max"],
                "min_threshold": spec["min"],
                "max_threshold": spec["max"],
                "calibration_date": spec["calibration"],
                "accuracy_percentage": 98.5,
            }
            if not sensor:
                sensor = Sensor(**payload)
                db.session.add(sensor)
            else:
                for field, value in payload.items():
                    setattr(sensor, field, value)
