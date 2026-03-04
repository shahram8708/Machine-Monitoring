from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import AIPrediction, Machine

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
    "name": "ai_predictions",
    "order": 320,
    "description": "Latest AI predictions with risk levels",
}


def run():
    machines = {m.machine_code: m for m in Machine.query.all()}
    now = ANCHOR_NOW

    predictions = [
        {
            "machine_code": "AP-PUN-LATHE-01",
            "failure_probability": 0.08,
            "remaining_useful_life_hours": 940,
            "degradation_score": 0.12,
            "anomaly_score": 0.05,
            "risk_level": "LOW",
            "early_warning_flag": False,
            "ai_explanation": {"drivers": ["stable temperature", "low vibration variance"]},
            "confidence_score": 0.86,
            "created_at": now - timedelta(minutes=30),
        },
        {
            "machine_code": "AP-MAA-MILL-01",
            "failure_probability": 0.11,
            "remaining_useful_life_hours": 810,
            "degradation_score": 0.18,
            "anomaly_score": 0.10,
            "risk_level": "LOW",
            "early_warning_flag": False,
            "ai_explanation": {"drivers": ["tool wear trending", "load rise"]},
            "confidence_score": 0.82,
            "created_at": now - timedelta(minutes=45),
        },
        {
            "machine_code": "NW-AHD-PRESS-01",
            "failure_probability": 0.26,
            "remaining_useful_life_hours": 540,
            "degradation_score": 0.34,
            "anomaly_score": 0.28,
            "risk_level": "MEDIUM",
            "early_warning_flag": True,
            "ai_explanation": {"drivers": ["pressure ripple", "vibration drift"]},
            "confidence_score": 0.79,
            "created_at": now - timedelta(minutes=55),
        },
        {
            "machine_code": "EV-NOI-PACK-01",
            "failure_probability": 0.33,
            "remaining_useful_life_hours": 410,
            "degradation_score": 0.42,
            "anomaly_score": 0.36,
            "risk_level": "MEDIUM",
            "early_warning_flag": True,
            "ai_explanation": {"drivers": ["humidity impact", "film tension variance"]},
            "confidence_score": 0.77,
            "created_at": now - timedelta(minutes=70),
        },
    ]

    for data in predictions:
        machine = machines.get(data["machine_code"])
        if not machine:
            continue
        data["created_at"] = _clamp_dt(data["created_at"])
        row = AIPrediction.query.filter_by(machine_id=machine.id, created_at=data["created_at"]).first()
        payload = {
            "machine_id": machine.id,
            "plant_id": machine.plant_id,
            "company_id": machine.company_id,
            "failure_probability": data["failure_probability"],
            "remaining_useful_life_hours": data["remaining_useful_life_hours"],
            "degradation_score": data["degradation_score"],
            "anomaly_score": data["anomaly_score"],
            "risk_level": data["risk_level"],
            "early_warning_flag": data["early_warning_flag"],
            "ai_explanation": data["ai_explanation"],
            "confidence_score": data["confidence_score"],
            "created_at": data["created_at"],
        }
        if not row:
            row = AIPrediction(**payload)
            db.session.add(row)
        else:
            for field, value in payload.items():
                setattr(row, field, value)
