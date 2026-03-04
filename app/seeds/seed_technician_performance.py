from __future__ import annotations

import random
from collections import defaultdict
from datetime import date, datetime
from statistics import mean

from app.extensions import db
from app.models import Machine, MaintenanceTask, TechnicianPerformance, User

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
    "name": "technician_performance",
    "order": 460,
    "description": "Performance metrics derived from maintenance tasks",
}


def run():
    random.seed(43)
    now = ANCHOR_NOW
    tasks = (
        MaintenanceTask.query.join(Machine, Machine.id == MaintenanceTask.machine_id)
        .filter(MaintenanceTask.assigned_to.isnot(None))
        .all()
    )
    if not tasks:
        return

    aggregates: dict[tuple[int, int], dict[str, object]] = defaultdict(
        lambda: {"durations": [], "completed": 0, "total": 0, "on_time": 0, "overdue": 0}
    )

    for task in tasks:
        if not task.assigned_to or not task.machine:
            continue
        key = (task.assigned_to, task.machine.plant_id)
        bucket = aggregates[key]
        bucket["total"] += 1

        if task.completed_at and task.assigned_at:
            duration_minutes = max(1, (task.completed_at - task.assigned_at).total_seconds() / 60)
            bucket["durations"].append(duration_minutes)
            if str(task.status).lower() == "completed":
                bucket["completed"] += 1
                if task.delay_minutes is not None and task.delay_minutes <= 0:
                    bucket["on_time"] += 1
                else:
                    bucket["overdue"] += 1
        elif task.assigned_at:
            duration_minutes = max(1, (now - task.assigned_at).total_seconds() / 60)
            bucket["durations"].append(duration_minutes)

    for (user_id, plant_id), data in aggregates.items():
        durations = data["durations"] or [240]
        completed = data["completed"]
        avg_resolution_hours = round(mean(durations) / 60, 2)
        sla_rate = round(data["on_time"] / max(1, completed), 2)
        overdue_penalty = min(15, data["overdue"] * 0.6)
        efficiency_score = round(min(99.0, max(65.0, 88 + (sla_rate * 10) - overdue_penalty)), 2)
        rework_rate = round(0.02 + random.random() * 0.07, 3)

        perf = TechnicianPerformance.query.filter_by(user_id=user_id, plant_id=plant_id).first()
        if not perf:
            perf = TechnicianPerformance(user_id=user_id, plant_id=plant_id)
            db.session.add(perf)

        perf.total_tasks_completed = completed
        perf.avg_resolution_time = avg_resolution_hours
        perf.sla_compliance_rate = sla_rate
        perf.efficiency_score = efficiency_score
        perf.rework_rate = rework_rate
        perf.last_updated = _clamp_dt(now)

    db.session.flush()

    if len(aggregates) < 20:
        remaining = 20 - len(aggregates)
        technicians = User.query.filter(User.role == "TECHNICIAN").order_by(User.id).all()
        plants = {m.plant_id for m in Machine.query.all() if m.plant_id}
        cursor = 0
        for _ in range(remaining):
            if not technicians or not plants:
                break
            tech = technicians[cursor % len(technicians)]
            plant_id = list(plants)[cursor % len(plants)]
            cursor += 1
            perf = TechnicianPerformance.query.filter_by(user_id=tech.id, plant_id=plant_id).first()
            if perf:
                continue
            perf = TechnicianPerformance(
                user_id=tech.id,
                plant_id=plant_id,
                total_tasks_completed=5,
                avg_resolution_time=round(3.5 + random.random(), 2),
                sla_compliance_rate=round(0.82 + random.random() * 0.12, 2),
                efficiency_score=round(82 + random.random() * 12, 2),
                rework_rate=round(0.02 + random.random() * 0.05, 3),
                last_updated=_clamp_dt(now),
            )
            db.session.add(perf)

