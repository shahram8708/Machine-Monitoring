from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func

from app.audit import log_action
from app.extensions import db
from app.models import Machine, MachineData, MachineKPI, MachineHealthScore, Alert, AIPrediction
from app.services.anomaly_service import detect_anomalies
from app.services.gemini_service import generate_gemini_response
from app.ai.prompt_templates import (
    failure_probability_prompt,
    rul_estimation_prompt,
    degradation_analysis_prompt,
    preventive_action_prompt,
)
from config import get_config

_cfg = get_config()
FAILURE_PROB_THRESHOLD = float(getattr(_cfg, "AI_FAILURE_THRESHOLD", 65.0))
HEALTH_THRESHOLD = float(getattr(_cfg, "AI_HEALTH_THRESHOLD", 60.0))
DEGRADATION_THRESHOLD = float(getattr(_cfg, "AI_DEGRADATION_THRESHOLD", 70.0))


def _latest_health(machine_id: int) -> Optional[MachineHealthScore]:
    return (
        MachineHealthScore.query.filter_by(machine_id=machine_id)
        .order_by(MachineHealthScore.calculated_at.desc())
        .first()
    )


def _recent_kpis(machine_id: int) -> List[MachineKPI]:
    return (
        MachineKPI.query.filter_by(machine_id=machine_id)
        .order_by(MachineKPI.date.asc())
        .all()
    )


def _recent_data(machine_id: int) -> List[MachineData]:
    return (
        MachineData.query.filter_by(machine_id=machine_id)
        .order_by(MachineData.timestamp.asc())
        .all()
    )


def _recent_alerts(machine_id: int) -> List[Alert]:
    return (
        Alert.query.filter_by(machine_id=machine_id)
        .order_by(Alert.created_at.asc())
        .all()
    )


def _float(val, default: float | None = 0.0) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _summaries(machine: Machine) -> Dict[str, object]:
    data_points = _recent_data(machine.id)
    kpis = _recent_kpis(machine.id)
    alerts = _recent_alerts(machine.id)
    health = _latest_health(machine.id)

    def avg(vals: List[float]) -> float:
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    temp_vals = [v for v in (_float(dp.temperature) for dp in data_points if dp.temperature is not None) if v is not None]
    vib_vals = [v for v in (_float(dp.vibration) for dp in data_points if dp.vibration is not None) if v is not None]
    curr_vals = [v for v in (_float(dp.current) for dp in data_points if dp.current is not None) if v is not None]
    volt_vals = [v for v in (_float(dp.voltage) for dp in data_points if dp.voltage is not None) if v is not None]

    downtime_minutes = [kp.downtime_minutes for kp in kpis if kp.downtime_minutes is not None]
    downtime_freq = sum(1 for minutes in downtime_minutes if minutes > 0)

    kpi_series = [
        {
            "date": kp.date.isoformat(),
            "oee": kp.oee,
            "downtime_minutes": kp.downtime_minutes,
            "availability": kp.availability,
            "performance": kp.performance,
            "quality": kp.quality,
        }
        for kp in kpis
    ]

    alert_counts = {
        "total": len(alerts),
        "critical": sum(1 for a in alerts if a.severity == "critical"),
        "high": sum(1 for a in alerts if a.severity == "high"),
    }

    return {
        "machine": {
            "id": machine.id,
            "name": machine.machine_name,
            "type": machine.machine_type,
            "location": machine.location,
            "plant_id": machine.plant_id,
            "company_id": machine.company_id,
        },
        "telemetry_summary": {
            "avg_temperature": avg(temp_vals),
            "avg_vibration": avg(vib_vals),
            "avg_current": avg(curr_vals),
            "avg_voltage": avg(volt_vals),
            "sample_size": len(data_points),
        },
        "health": {
            "latest_score": health.health_score if health else None,
            "latest_risk": health.risk_level if health else None,
        },
        "downtime": {
            "frequency": downtime_freq,
            "avg_minutes": avg(downtime_minutes),
        },
        "kpi_trend": kpi_series,
        "alerts": alert_counts,
    }


def _normalize_risk(value: str) -> str:
    normalized = (value or "").upper()
    if normalized not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        return "MEDIUM"
    return normalized


def _coerce_probability(value) -> float:
    prob = _float(value)
    return max(0.0, min(100.0, prob))


def run_prediction(machine: Machine) -> AIPrediction:
    context = _summaries(machine)

    try:
        failure_raw = generate_gemini_response(failure_probability_prompt, context)
    except Exception:  # noqa: BLE001
        failure_raw = {"failure_probability": 50, "risk_level": "MEDIUM", "confidence": 0}

    try:
        rul_raw = generate_gemini_response(rul_estimation_prompt, context)
    except Exception:  # noqa: BLE001
        rul_raw = {"remaining_hours": None, "remaining_days": None, "degradation_stage": "MID", "confidence": 0}

    try:
        degradation_raw = generate_gemini_response(degradation_analysis_prompt, context)
    except Exception:  # noqa: BLE001
        degradation_raw = {"degradation_trend_score": 50, "severity": "MEDIUM", "confidence": 0}

    anomaly_raw = detect_anomalies(machine.id)

    failure_probability = _coerce_probability(failure_raw.get("failure_probability"))
    risk_level = _normalize_risk(failure_raw.get("risk_level"))
    degradation_score = _coerce_probability(degradation_raw.get("degradation_trend_score"))
    anomaly_score = _coerce_probability(anomaly_raw.get("anomaly_score"))

    remaining_hours = _float(rul_raw.get("remaining_hours"), None)
    remaining_days = _float(rul_raw.get("remaining_days"), None)
    degradation_stage = (rul_raw.get("degradation_stage") or "").upper() or None

    early_warning = (
        failure_probability >= FAILURE_PROB_THRESHOLD
        or (context["health"].get("latest_score") or 100) < HEALTH_THRESHOLD
        or degradation_score >= DEGRADATION_THRESHOLD
        or anomaly_score >= 60
    )

    actions_input = {
        **context,
        "ai_findings": {
            "failure_probability": failure_probability,
            "risk_level": risk_level,
            "rul_hours": remaining_hours,
            "rul_days": remaining_days,
            "degradation_stage": degradation_stage,
            "degradation_score": degradation_score,
            "anomaly_score": anomaly_score,
            "anomaly_detected": anomaly_raw.get("anomaly_detected"),
        },
    }
    try:
        actions_raw = generate_gemini_response(preventive_action_prompt, actions_input)
    except Exception:  # noqa: BLE001
        actions_raw = {
            "actions": [
                "Inspect critical bearings for wear",
                "Verify lubrication schedule adherence",
                "Check sensor calibration and wiring",
            ],
            "inspection_recommendation": "Perform vibration and thermal scan within 24 hours",
            "spare_parts": ["bearings kit", "lubricant"],
            "strategy": "Shift to condition-based maintenance until stability confirmed",
            "confidence": 0,
            "explanation": "Fallback guidance while AI is unavailable",
        }

    confidence_values = [
        _float(failure_raw.get("confidence")),
        _float(rul_raw.get("confidence")),
        _float(degradation_raw.get("confidence")),
        _float(anomaly_raw.get("confidence")),
        _float(actions_raw.get("confidence")),
    ]
    confidence_vals = [v for v in confidence_values if v is not None]
    avg_confidence = round(sum(confidence_vals) / len(confidence_vals), 4) if confidence_vals else None

    prediction = AIPrediction(
        machine_id=machine.id,
        plant_id=machine.plant_id,
        company_id=machine.company_id,
        failure_probability=failure_probability,
        remaining_useful_life_hours=remaining_hours,
        degradation_score=degradation_score,
        anomaly_score=anomaly_score,
        risk_level=risk_level,
        early_warning_flag=early_warning,
        ai_explanation={
            "failure": failure_raw,
            "rul": rul_raw,
            "degradation": degradation_raw,
            "anomaly": anomaly_raw,
            "actions": actions_raw,
            "rul_days": remaining_days,
            "degradation_stage": degradation_stage,
        },
        confidence_score=avg_confidence,
    )

    db.session.add(prediction)
    db.session.commit()
    log_action(
        "ai_prediction_created",
        "ai_prediction",
        prediction.id,
        company_id=machine.company_id,
        plant_id=machine.plant_id,
        new_value={"machine_id": machine.id, "risk": risk_level, "failure_probability": failure_probability},
        action_type="ai_prediction",
    )
    db.session.commit()
    return prediction


def latest_prediction(machine_id: int, company_id: int) -> Optional[AIPrediction]:
    return (
        AIPrediction.query.filter_by(machine_id=machine_id, company_id=company_id)
        .order_by(AIPrediction.created_at.desc())
        .first()
    )


def history(machine_id: int, company_id: int) -> List[Dict[str, object]]:
    records = (
        AIPrediction.query.filter_by(machine_id=machine_id, company_id=company_id)
        .order_by(AIPrediction.created_at.asc())
        .all()
    )
    output = []
    for rec in records:
        output.append(
            {
                "timestamp": rec.created_at.isoformat(),
                "failure_probability": rec.failure_probability,
                "risk_level": rec.risk_level,
                "degradation_score": rec.degradation_score,
                "anomaly_score": rec.anomaly_score,
                "early_warning": rec.early_warning_flag,
            }
        )
    return output


def plant_summary(company_id: int, plant_ids: List[int] | None = None) -> List[Dict[str, object]]:
    query = AIPrediction.query.filter_by(company_id=company_id)
    if plant_ids:
        query = query.filter(AIPrediction.plant_id.in_(plant_ids))
    rows = (
        query.with_entities(
            AIPrediction.plant_id,
            func.avg(AIPrediction.failure_probability).label("avg_failure"),
            func.avg(AIPrediction.degradation_score).label("avg_degradation"),
            func.count(AIPrediction.id).label("count"),
            func.max(AIPrediction.created_at).label("latest"),
        )
        .group_by(AIPrediction.plant_id)
        .all()
    )
    summary = []
    for row in rows:
        summary.append(
            {
                "plant_id": row.plant_id,
                "avg_failure_probability": float(row.avg_failure or 0),
                "avg_degradation_score": float(row.avg_degradation or 0),
                "prediction_count": int(row.count or 0),
                "latest_prediction_at": row.latest.isoformat() if row.latest else None,
            }
        )
    return summary


def run_scheduled_predictions() -> None:
    machines = Machine.query.all()
    for machine in machines:
        try:
            run_prediction(machine)
        except Exception:  # noqa: BLE001
            db.session.rollback()
            continue
