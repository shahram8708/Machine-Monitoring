from datetime import date
from typing import Dict, List

from app.models.machine import Machine
from app.services.kpi_service import plant_rankings, top_kpi_machines


def compare_plants(company_id: int, day: date | None = None) -> List[Dict]:
    return plant_rankings(company_id, day)


def compare_machines(company_id: int, day: date | None = None) -> Dict[str, List[Dict]]:
    return {
        "best": top_kpi_machines(company_id, limit=10, day=day, best=True),
        "worst": top_kpi_machines(company_id, limit=10, day=day, best=False),
    }


def underperforming(company_id: int, day: date | None = None) -> Dict[str, List[int]]:
    thresholds = {"oee": 0.6, "health": 50.0, "downtime_cost": 1000.0}
    machine_ids: List[int] = []
    best_worst = compare_machines(company_id, day)
    for rec in best_worst["worst"]:
        if rec.get("oee", 1) < thresholds["oee"]:
            machine_ids.append(rec["machine_id"])
    return {"machines": machine_ids, "thresholds": thresholds}
