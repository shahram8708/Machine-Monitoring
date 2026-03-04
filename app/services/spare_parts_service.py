from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import func

from app.extensions import db
from app.models import Machine, SparePart, SpareInventory, MachineSpareMapping
from app.services.predictive_service import latest_prediction, run_prediction


def _ensure_prediction(machine: Machine):
    prediction = latest_prediction(machine.id, machine.company_id)
    if not prediction:
        try:
            prediction = run_prediction(machine)
        except Exception:  # noqa: BLE001
            prediction = None
    return prediction


def _demand_estimate(
    machine: Machine,
    mapping: MachineSpareMapping,
    spare: SparePart,
    window_days: int = 30,
) -> dict:
    pred = _ensure_prediction(machine)
    window_hours = 24 * window_days

    failure_prob = (pred.failure_probability if pred else 50) or 50
    confidence = pred.confidence_score if pred else 0
    remaining_hours = pred.remaining_useful_life_hours if pred else None

    base_freq = mapping.replacement_frequency_hours or spare.average_lifetime_hours or 720.0
    expected_replacements = max(0.2, window_hours / base_freq)

    failure_multiplier = max(0.5, min(1.5, failure_prob / 50))
    if remaining_hours and remaining_hours < window_hours:
        urgency_factor = 1.2
    else:
        urgency_factor = 1.0
    expected_demand = round(expected_replacements * failure_multiplier * urgency_factor, 2)

    inventory = (
        SpareInventory.query.filter_by(spare_part_id=spare.id, plant_id=machine.plant_id).first()
        if machine.plant_id
        else None
    )
    current_stock = inventory.current_stock if inventory else 0
    minimum_required = inventory.minimum_required_stock if inventory else 0
    lead_time_days = spare.lead_time_days or 0

    # Risk: if lead time exceeds coverage from stock
    daily_use = expected_demand / window_days if window_days else 0
    coverage_days = (current_stock / daily_use) if daily_use else float("inf")
    stock_out_risk = 0
    if lead_time_days and coverage_days != float("inf"):
        shortage_gap = max(0.0, lead_time_days - coverage_days)
        stock_out_risk = min(100, round((shortage_gap / max(lead_time_days, 1)) * 100, 2))
    elif current_stock < minimum_required:
        stock_out_risk = 65.0

    reorder_qty = 0
    if current_stock < minimum_required:
        reorder_qty = (minimum_required - current_stock) + max(1, int(round(expected_demand)))
    elif stock_out_risk >= 50:
        reorder_qty = max(1, int(round(expected_demand)))

    estimated_cost = float(spare.cost_per_unit or 0) * reorder_qty

    return {
        "part_name": spare.part_name,
        "part_code": spare.part_code,
        "machine_type": spare.machine_type,
        "recommended_quantity": reorder_qty,
        "stock_out_risk": round(stock_out_risk, 2),
        "estimated_cost": round(estimated_cost, 2),
        "current_stock": current_stock,
        "minimum_required_stock": minimum_required,
        "lead_time_days": lead_time_days,
        "expected_demand": expected_demand,
        "confidence": confidence or 0,
    }


def predict_for_machine(machine_id: int, company_id: int, window_days: int = 30) -> Dict[str, object]:
    machine = Machine.query.filter_by(id=machine_id, company_id=company_id).first_or_404()
    mappings = MachineSpareMapping.query.join(SparePart).filter(
        MachineSpareMapping.machine_id == machine.id,
        SparePart.company_id == company_id,
    ).all()

    recommendations: List[dict] = []
    for mapping in mappings:
        spare = mapping.spare_part
        recommendations.append(_demand_estimate(machine, mapping, spare, window_days=window_days))

    avg_conf = 0
    if recommendations:
        avg_conf = sum(r.get("confidence", 0) for r in recommendations) / max(len(recommendations), 1)

    return {
        "machine_id": machine.id,
        "plant_id": machine.plant_id,
        "company_id": machine.company_id,
        "recommended_parts": recommendations,
        "confidence": round(avg_conf or 0, 4),
    }


def inventory_view(company_id: int, plant_ids: list[int] | None = None) -> List[dict]:
    query = SpareInventory.query.join(SparePart).filter(SparePart.company_id == company_id)
    if plant_ids:
        query = query.filter(SpareInventory.plant_id.in_(plant_ids))

    rows = query.all()
    output: List[dict] = []
    for inv in rows:
        output.append(
            {
                "id": inv.id,
                "spare_part_id": inv.spare_part_id,
                "plant_id": inv.plant_id,
                "part_name": inv.spare_part.part_name,
                "part_code": inv.spare_part.part_code,
                "current_stock": inv.current_stock,
                "minimum_required_stock": inv.minimum_required_stock,
                "lead_time_days": inv.spare_part.lead_time_days,
                "last_updated": inv.last_updated.isoformat() if inv.last_updated else None,
            }
        )
    return output


def recommendation_summary(company_id: int, plant_ids: list[int] | None = None) -> Dict[str, object]:
    query = SpareInventory.query.join(SparePart).filter(SparePart.company_id == company_id)
    if plant_ids:
        query = query.filter(SpareInventory.plant_id.in_(plant_ids))

    total_items = query.count()
    at_risk = query.filter(SpareInventory.current_stock < SpareInventory.minimum_required_stock).count()
    lead_time_avg = query.with_entities(func.avg(SparePart.lead_time_days)).scalar() or 0

    return {
        "total_items": total_items,
        "at_risk": at_risk,
        "avg_lead_time_days": float(lead_time_avg),
    }
