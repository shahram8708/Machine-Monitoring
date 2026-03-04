from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import pstdev
from typing import Dict, List

from sqlalchemy import func

from app.models import Machine, MachineData, MachineKPI
from app.services.gemini_service import generate_gemini_response
from app.ai.prompt_templates import esg_improvement_prompt


def _energy_series(machine_id: int, days: int | None = None) -> List[dict]:
    query = MachineData.query.filter_by(machine_id=machine_id).order_by(MachineData.timestamp.asc())
    if days is not None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.filter(MachineData.timestamp >= cutoff)
    records = query.all()
    daily = defaultdict(float)
    for idx, rec in enumerate(records):
        next_ts = records[idx + 1].timestamp if idx + 1 < len(records) else None
        duration = (next_ts - rec.timestamp).total_seconds() if next_ts else 60.0
        if rec.voltage and rec.current:
            kwh = (rec.voltage * rec.current * duration) / 3_600_000
            day = rec.timestamp.date().isoformat()
            daily[day] += kwh
    return [{"date": day, "energy_kwh": round(val, 3)} for day, val in sorted(daily.items())]


def _efficiency_variance(series: List[dict]) -> float:
    vals = [item["energy_kwh"] for item in series if item.get("energy_kwh") is not None]
    if len(vals) < 2:
        return 0.0
    return round(pstdev(vals), 4)


def energy_trends(machine_id: int, company_id: int, days: int | None = None) -> Dict[str, object]:
    machine = Machine.query.filter_by(id=machine_id, company_id=company_id).first_or_404()
    series = _energy_series(machine.id, days=days)
    total_kwh = round(sum(item["energy_kwh"] for item in series), 3)
    variance = _efficiency_variance(series)

    # Energy per unit proxy using speed as throughput indicator
    throughput_query = MachineData.query.with_entities(func.avg(MachineData.speed)).filter_by(machine_id=machine.id)
    if days is not None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        throughput_query = throughput_query.filter(MachineData.timestamp >= cutoff)
    throughput = throughput_query.scalar() or 1
    energy_per_unit = round(total_kwh / max(throughput, 1), 4)

    return {
        "machine_id": machine.id,
        "series": series,
        "total_energy_kwh": total_kwh,
        "efficiency_variance": variance,
        "energy_per_unit": energy_per_unit,
    }


def esg_summary(machine_id: int, company_id: int) -> Dict[str, object]:
    machine = Machine.query.filter_by(id=machine_id, company_id=company_id).first_or_404()
    trend = energy_trends(machine.id, company_id, days=None)

    # Carbon proxy (kg CO2e) using 0.4 kg/kWh placeholder
    carbon_proxy = round(trend["total_energy_kwh"] * 0.4, 3)

    avg_oee = (
        MachineKPI.query.with_entities(func.avg(MachineKPI.oee))
        .filter_by(machine_id=machine.id)
        .scalar()
    )
    efficiency_improvement = round(((avg_oee or 0) - 0.7) * 100, 2)

    ai_payload = {
        "machine": {
            "id": machine.id,
            "name": machine.machine_name,
            "type": machine.machine_type,
            "plant_id": machine.plant_id,
        },
        "energy_series": trend["series"],
        "total_energy_kwh": trend["total_energy_kwh"],
        "efficiency_variance": trend["efficiency_variance"],
        "energy_per_unit": trend["energy_per_unit"],
        "carbon_proxy_kg": carbon_proxy,
    }

    try:
        ai_output = generate_gemini_response(esg_improvement_prompt, ai_payload)
    except Exception:  # noqa: BLE001
        ai_output = {
            "energy_optimization_suggestions": ["Review idle energy consumption", "Schedule load balancing during off-peak"],
            "efficiency_gap_analysis": "AI unavailable; using fallback guidance.",
            "sustainability_score": 65,
            "confidence": 0,
        }

    sustainability_score = ai_output.get("sustainability_score") or 0

    return {
        "machine_id": machine.id,
        "energy_trend": trend,
        "carbon_proxy_kg": carbon_proxy,
        "efficiency_improvement_pct": efficiency_improvement,
        "ai": ai_output,
        "sustainability_score": sustainability_score,
        "confidence": ai_output.get("confidence", 0),
    }
