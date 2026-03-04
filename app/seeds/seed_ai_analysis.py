from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import AiAnalysis, Machine

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
    "name": "ai_analysis",
    "order": 310,
    "description": "Recent AI analyses per machine",
}


def run():
    machines = {m.machine_code: m for m in Machine.query.all()}
    now = ANCHOR_NOW

    analyses = [
        {
            "machine_code": "AP-PUN-LATHE-01",
            "timestamp": now - timedelta(hours=1),
            "health_score": 91.0,
            "risk_level": "LOW",
            "anomaly": False,
            "maintenance_suggestion": "Inspect spindle lubrication during next micro-stop; vibration remains within control limits.",
            "explanation": "Model shows stable temperature trend with minor vibration uptick after 45 minutes.",
            "status": "completed",
        },
        {
            "machine_code": "AP-MAA-MILL-01",
            "timestamp": now - timedelta(hours=2),
            "health_score": 88.5,
            "risk_level": "LOW",
            "anomaly": False,
            "maintenance_suggestion": "Schedule tool recalibration after current batch; spindle load trending upward.",
            "explanation": "Load increase correlates with harder alloy lot; no thermal runaway detected.",
            "status": "completed",
        },
        {
            "machine_code": "NW-AHD-PRESS-01",
            "timestamp": now - timedelta(hours=3),
            "health_score": 74.0,
            "risk_level": "MEDIUM",
            "anomaly": True,
            "maintenance_suggestion": "Check hydraulic seals and accumulator pre-charge; pressure ripple above baseline.",
            "explanation": "Intermittent pressure dips coincide with rising vibration; probable seal wear.",
            "status": "completed",
        },
        {
            "machine_code": "EV-NOI-PACK-01",
            "timestamp": now - timedelta(hours=4),
            "health_score": 69.5,
            "risk_level": "MEDIUM",
            "anomaly": True,
            "maintenance_suggestion": "Clean forming jaws and check film tensioner; humidity drift causing seal variance.",
            "explanation": "Seal quality variance correlates with elevated humidity in the packaging hall.",
            "status": "completed",
        },
    ]

    for data in analyses:
        machine = machines.get(data["machine_code"])
        if not machine:
            continue
        data["timestamp"] = _clamp_dt(data["timestamp"])
        row = AiAnalysis.query.filter_by(machine_id=machine.id, timestamp=data["timestamp"]).first()
        if not row:
            row = AiAnalysis(
                machine_id=machine.id,
                timestamp=data["timestamp"],
                health_score=data["health_score"],
                risk_level=data["risk_level"],
                anomaly=data["anomaly"],
                maintenance_suggestion=data["maintenance_suggestion"],
                explanation=data["explanation"],
                status=data["status"],
                created_at=_clamp_dt(now),
            )
            db.session.add(row)
        else:
            row.health_score = data["health_score"]
            row.risk_level = data["risk_level"]
            row.anomaly = data["anomaly"]
            row.maintenance_suggestion = data["maintenance_suggestion"]
            row.explanation = data["explanation"]
            row.status = data["status"]
