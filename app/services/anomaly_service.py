from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Tuple

from sqlalchemy import desc

from app.models.machine_data import MachineData
from app.services.gemini_service import generate_gemini_response
from app.ai.prompt_templates import anomaly_detection_prompt


def _mean_std(values: Iterable[float]) -> Tuple[float, float]:
    vals = list(values)
    if not vals:
        return 0.0, 0.0
    mean_val = sum(vals) / len(vals)
    variance = sum((v - mean_val) ** 2 for v in vals) / len(vals)
    return mean_val, math.sqrt(variance)


def _z_scores(values: List[float], mean_val: float, std_val: float) -> List[float]:
    if std_val == 0:
        return [0.0 for _ in values]
    return [(v - mean_val) / std_val for v in values]


def _summarize_metric(values: List[float]) -> Dict[str, float]:
    mean_val, std_val = _mean_std(values)
    z_vals = _z_scores(values, mean_val, std_val)
    max_z = max((abs(z) for z in z_vals), default=0.0)
    outliers = sum(1 for z in z_vals if abs(z) > 3)
    return {
        "mean": round(mean_val, 4),
        "std": round(std_val, 4),
        "max_z": round(max_z, 4),
        "outlier_count": outliers,
    }


def _recent_points(machine_id: int, hours: int | None) -> List[MachineData]:
    query = MachineData.query.filter_by(machine_id=machine_id)
    if hours is not None:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(MachineData.timestamp >= cutoff)
    return query.order_by(desc(MachineData.timestamp)).all()


def _metric_values(records: List[MachineData], field: str) -> List[float]:
    values: List[float] = []
    for rec in records:
        val = getattr(rec, field)
        if val is None:
            continue
        try:
            values.append(float(val))
        except (TypeError, ValueError):
            continue
    return values


def detect_anomalies(machine_id: int, window_hours: int | None = None) -> Dict[str, object]:
    records = _recent_points(machine_id, window_hours)
    metrics = {"temperature": [], "vibration": [], "current": [], "voltage": [], "pressure": [], "speed": []}
    for metric in metrics:
        metrics[metric] = _metric_values(records, metric)

    summaries = {name: _summarize_metric(vals) for name, vals in metrics.items() if vals}

    condensed_samples = []
    for rec in records[:60]:
        condensed_samples.append(
            {
                "timestamp": rec.timestamp.isoformat(),
                "temperature": rec.temperature,
                "vibration": rec.vibration,
                "current": rec.current,
                "voltage": rec.voltage,
                "pressure": rec.pressure,
                "speed": rec.speed,
                "running_status": rec.running_status,
            }
        )

    payload = {
        "window_hours": window_hours,
        "metric_stats": summaries,
        "sample_size": len(records),
        "recent_samples": condensed_samples,
    }

    try:
        ai_result = generate_gemini_response(anomaly_detection_prompt, payload)
    except Exception:  # noqa: BLE001
        ai_result = {
            "anomaly_detected": False,
            "anomaly_score": 0,
            "root_pattern": "AI unavailable; fallback to statistics",
            "confidence": 0,
        }

    anomaly_score = float(ai_result.get("anomaly_score", 0) or 0)
    anomaly_score = max(0.0, min(100.0, anomaly_score))

    return {
        "anomaly_detected": bool(ai_result.get("anomaly_detected", False)),
        "anomaly_score": anomaly_score,
        "root_pattern": ai_result.get("root_pattern", ""),
        "confidence": float(ai_result.get("confidence", 0) or 0),
        "metric_stats": summaries,
        "sample_size": len(records),
    }
