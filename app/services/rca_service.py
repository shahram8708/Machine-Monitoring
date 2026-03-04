from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from sqlalchemy import func

from app.extensions import db
from app.ai import prompt_templates
from app.models import Alert, AlertGroup, RootCauseAnalysis, MachineHealthScore, AIPrediction
from app.models.machine_data import MachineData
from app.services.gemini_service import generate_gemini_response

logger = logging.getLogger(__name__)


def _sanitize_text(value: str) -> str:
    return (value or "").replace("`", "").replace("\n", " ").strip()


def _alert_history(group_id: int) -> list[dict[str, Any]]:
    alerts = (
        Alert.query.filter_by(grouped_alert_id=group_id)
        .order_by(Alert.created_at.asc())
        .all()
    )
    return [
        {
            "id": a.id,
            "type": a.alert_type,
            "severity": a.severity,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
            "message": _sanitize_text(a.message),
        }
        for a in alerts
    ]


def _sensor_trends(machine_id: int, hours: int = 72) -> dict[str, Any]:
    window_start = datetime.utcnow() - timedelta(hours=hours)
    qs = (
        db.session.query(
            func.avg(MachineData.temperature),
            func.avg(MachineData.vibration),
            func.avg(MachineData.current),
            func.avg(MachineData.voltage),
            func.avg(MachineData.pressure),
            func.avg(MachineData.humidity),
            func.avg(MachineData.speed),
        )
        .filter(MachineData.machine_id == machine_id, MachineData.timestamp >= window_start)
        .first()
    )
    return {
        "temperature_avg": qs[0] if qs else None,
        "vibration_avg": qs[1] if qs else None,
        "current_avg": qs[2] if qs else None,
        "voltage_avg": qs[3] if qs else None,
        "pressure_avg": qs[4] if qs else None,
        "humidity_avg": qs[5] if qs else None,
        "speed_avg": qs[6] if qs else None,
    }


def _failure_probability(machine_id: int) -> float:
    pred = (
        AIPrediction.query.filter_by(machine_id=machine_id)
        .order_by(AIPrediction.created_at.desc())
        .first()
    )
    return float(pred.failure_probability) if pred else 0.0


def _health_score(machine_id: int, company_id: int) -> float:
    score = (
        MachineHealthScore.query.filter_by(machine_id=machine_id, company_id=company_id)
        .order_by(MachineHealthScore.calculated_at.desc())
        .first()
    )
    return float(score.health_score) if score else 0.0


def _validate_rca_response(resp: Dict[str, Any]) -> Dict[str, Any]:
    required_keys = {
        "primary_root_cause": str,
        "contributing_factors": list,
        "sensor_interactions": str,
        "timeline_explanation": str,
        "root_cause_probability_breakdown": list,
        "confidence": (int, float),
    }
    for key, expected in required_keys.items():
        if key not in resp:
            raise ValueError(f"Missing key {key} in RCA response")
        if not isinstance(resp[key], expected):
            raise ValueError(f"Invalid type for {key}")
    return resp


def perform_root_cause_analysis(alert_group_id: int) -> RootCauseAnalysis:
    group = AlertGroup.query.get_or_404(alert_group_id)
    machine_id = group.machine_id
    alerts = _alert_history(alert_group_id)
    if not alerts:
        raise ValueError("No alerts in group for RCA")

    sample_alert = alerts[-1]
    company_id = Alert.query.get(alerts[-1]["id"]).company_id  # type: ignore[index]

    structured_data = {
        "machine_id": machine_id,
        "alert_group_id": alert_group_id,
        "alerts": alerts,
        "sensor_trends": _sensor_trends(machine_id),
        "failure_probability": _failure_probability(machine_id),
        "health_score": _health_score(machine_id, company_id),
    }

    try:
        response = generate_gemini_response(prompt_templates.root_cause_analysis_prompt, structured_data)
        parsed = _validate_rca_response(response)
    except Exception as exc:  # noqa: BLE001
        logger.error("RCA Gemini call failed: %s", exc)
        raise

    rca = RootCauseAnalysis(
        machine_id=machine_id,
        alert_group_id=alert_group_id,
        primary_root_cause=_sanitize_text(parsed.get("primary_root_cause", "")),
        contributing_factors=parsed.get("contributing_factors"),
        probability_breakdown=parsed.get("root_cause_probability_breakdown"),
        timeline_explanation=_sanitize_text(parsed.get("timeline_explanation", "")),
        sensor_interactions=_sanitize_text(parsed.get("sensor_interactions", "")),
        confidence_score=float(parsed.get("confidence", 0)),
    )
    db.session.add(rca)
    db.session.commit()
    return rca


def latest_rca_for_machine(machine_id: int) -> RootCauseAnalysis | None:
    return (
        RootCauseAnalysis.query.filter_by(machine_id=machine_id)
        .order_by(RootCauseAnalysis.created_at.desc())
        .first()
    )


def rca_for_group(alert_group_id: int) -> RootCauseAnalysis | None:
    return (
        RootCauseAnalysis.query.filter_by(alert_group_id=alert_group_id)
        .order_by(RootCauseAnalysis.created_at.desc())
        .first()
    )
