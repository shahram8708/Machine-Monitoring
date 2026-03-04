from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from sqlalchemy import func

from app.extensions import db
from app.models import MaintenanceTask, TechnicianPerformance, User, Machine


WEIGHTS = {
    "tasks": 0.30,
    "resolution": 0.25,
    "sla": 0.25,
    "rework": 0.20,
}


def _normalize(value, max_value):
    if not max_value:
        return 0.0
    return max(0.0, min(100.0, (value / max_value) * 100.0))


def _score(perf: TechnicianPerformance) -> float:
    tasks_component = _normalize(perf.total_tasks_completed or 0, 50)
    resolution_component = 100.0 - _normalize(perf.avg_resolution_time or 0, 240)
    sla_component = _normalize(perf.sla_compliance_rate or 0, 100)
    rework_component = 100.0 - _normalize(perf.rework_rate or 0, 30)

    score = (
        WEIGHTS["tasks"] * tasks_component
        + WEIGHTS["resolution"] * resolution_component
        + WEIGHTS["sla"] * sla_component
        + WEIGHTS["rework"] * rework_component
    )
    return round(max(0.0, min(100.0, score)), 2)


def refresh_performance(user_id: int, plant_id: int) -> TechnicianPerformance:
    perf = TechnicianPerformance.query.filter_by(user_id=user_id, plant_id=plant_id).first()
    if not perf:
        perf = TechnicianPerformance(user_id=user_id, plant_id=plant_id)

    tasks = MaintenanceTask.query.filter_by(assigned_to=user_id).all()
    completed = [t for t in tasks if t.status == "completed"]
    perf.total_tasks_completed = len(completed)

    if completed:
        durations = []
        sla_hits = 0
        reworks = 0
        for t in completed:
            if t.assigned_at and t.completed_at:
                durations.append((t.completed_at - t.assigned_at).total_seconds() / 60)
            if t.sla_minutes and t.completed_at and t.assigned_at:
                if (t.completed_at - t.assigned_at).total_seconds() / 60 <= t.sla_minutes:
                    sla_hits += 1
            if (t.status or "").lower() == "rework":
                reworks += 1
        perf.avg_resolution_time = sum(durations) / len(durations) if durations else None
        perf.sla_compliance_rate = round((sla_hits / len(completed)) * 100, 2) if completed else 0
        perf.rework_rate = round((reworks / len(completed)) * 100, 2) if completed else 0
    else:
        perf.avg_resolution_time = None
        perf.sla_compliance_rate = None
        perf.rework_rate = 0

    perf.efficiency_score = _score(perf)
    db.session.add(perf)
    db.session.commit()
    return perf


def analytics_overview(company_id: int, plant_ids: List[int] | None = None) -> Dict[str, object]:
    query = TechnicianPerformance.query.join(User).filter(User.company_id == company_id)
    if plant_ids:
        query = query.filter(TechnicianPerformance.plant_id.in_(plant_ids))

    rows = query.order_by(TechnicianPerformance.efficiency_score.desc().nullslast()).all()
    ranking = [
        {
            "user_id": row.user_id,
            "technician_name": row.user.name if row.user else "Unknown",
            "plant_id": row.plant_id,
            "efficiency_score": row.efficiency_score,
            "tasks_completed": row.total_tasks_completed,
            "sla_compliance": row.sla_compliance_rate,
        }
        for row in rows
    ]

    open_tasks = MaintenanceTask.query.join(User).filter(User.company_id == company_id, MaintenanceTask.status != "completed")
    if plant_ids:
        open_tasks = open_tasks.join(Machine).filter(Machine.plant_id.in_(plant_ids))
    open_count = open_tasks.count()

    delayed = open_tasks.filter(MaintenanceTask.sla_minutes.isnot(None))
    delayed = delayed.filter((func.extract("epoch", func.now()) - func.extract("epoch", MaintenanceTask.assigned_at)) / 60 > MaintenanceTask.sla_minutes)

    return {
        "ranking": ranking,
        "open_tasks": open_count,
        "delayed_tasks": delayed.count(),
    }


def technician_detail(tech_id: int) -> Dict[str, object]:
    perf = TechnicianPerformance.query.filter_by(user_id=tech_id).order_by(TechnicianPerformance.last_updated.desc()).first()
    if not perf:
        user = User.query.get_or_404(tech_id)
        return {"user_id": user.id, "technician_name": user.name, "efficiency_score": None}

    return {
        "user_id": perf.user_id,
        "technician_name": perf.user.name if perf.user else "Unknown",
        "plant_id": perf.plant_id,
        "efficiency_score": perf.efficiency_score,
        "tasks_completed": perf.total_tasks_completed,
        "avg_resolution_time": perf.avg_resolution_time,
        "sla_compliance_rate": perf.sla_compliance_rate,
        "rework_rate": perf.rework_rate,
        "last_updated": perf.last_updated.isoformat() if perf.last_updated else None,
    }


def workload_balance(company_id: int, plant_ids: List[int] | None = None) -> Dict[str, object]:
    open_tasks = MaintenanceTask.query.join(User).filter(User.company_id == company_id, MaintenanceTask.status != "completed")
    if plant_ids:
        open_tasks = open_tasks.join(Machine).filter(Machine.plant_id.in_(plant_ids))

    workload: Dict[int, List[MaintenanceTask]] = defaultdict(list)
    for task in open_tasks.all():
        if task.assigned_to:
            workload[task.assigned_to].append(task)

    avg_load = sum(len(v) for v in workload.values()) / max(len(workload), 1) if workload else 0

    overloaded = [uid for uid, tasks in workload.items() if len(tasks) > avg_load + 1]
    underloaded = [uid for uid, tasks in workload.items() if len(tasks) < avg_load - 1]

    suggestions = []
    for uid in overloaded:
        if not workload.get(uid):
            continue
        candidate = workload[uid][0]
        target_uid = underloaded[0] if underloaded else None
        suggestions.append(
            {
                "task_id": candidate.id,
                "from_user_id": uid,
                "to_user_id": target_uid,
                "reason": "Workload balancing due to overload",
                "skill_match": _skill_match(candidate, target_uid) if target_uid else False,
            }
        )

    delayed_tasks = [t for t in open_tasks.all() if _is_delayed(t)]

    return {
        "average_load": avg_load,
        "overloaded": overloaded,
        "underloaded": underloaded,
        "suggested_reassignments": suggestions,
        "delayed_tasks": [t.id for t in delayed_tasks],
    }


def _skill_match(task: MaintenanceTask, technician_id: int | None) -> bool:
    if not technician_id:
        return False
    tech = User.query.get(technician_id)
    if not tech or not task.skill_tags:
        return False
    tech_tags = set((tech.skill_tags or "").lower().split(",")) if hasattr(tech, "skill_tags") else set()
    required = set(t.strip().lower() for t in task.skill_tags.split(",") if t)
    return bool(required.intersection(tech_tags)) if required else True


def _is_delayed(task: MaintenanceTask) -> bool:
    if not task.sla_minutes or not task.assigned_at:
        return False
    elapsed_minutes = (datetime.utcnow() - task.assigned_at).total_seconds() / 60
    return elapsed_minutes > task.sla_minutes
