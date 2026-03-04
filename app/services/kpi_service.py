from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy import func

from app.extensions import db
from app.models.alert import Alert
from app.models.machine import Machine
from app.models.machine_data import MachineData
from app.models.machine_kpi import MachineKPI
from app.models.machine_stats import MachineDailyStat

PLANNED_SECONDS = 24 * 60 * 60
IDEAL_CYCLE_TIME_SEC = 1.0


def _duration_between(current: datetime, next_ts: Optional[datetime]) -> float:
    if not next_ts:
        return 60.0
    seconds = (next_ts - current).total_seconds()
    if seconds <= 0:
        return 60.0
    return seconds


def _bucket_records(machine_id: int, day: date) -> List[MachineData]:
    start_dt = datetime.combine(day, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)
    return (
        MachineData.query.filter_by(machine_id=machine_id)
        .filter(MachineData.timestamp >= start_dt, MachineData.timestamp < end_dt)
        .order_by(MachineData.timestamp.asc())
        .all()
    )


def _runtime_and_units(records: List[MachineData]) -> Tuple[float, float, float]:
    running_seconds = 0.0
    idle_seconds = 0.0
    total_units = 0.0
    for idx, record in enumerate(records):
        next_ts = records[idx + 1].timestamp if idx + 1 < len(records) else None
        duration = _duration_between(record.timestamp, next_ts)
        if record.running_status:
            running_seconds += duration
        else:
            idle_seconds += duration
        if record.speed is not None:
            total_units += (record.speed * duration) / 60.0
    return running_seconds, idle_seconds, total_units


def _energy_from_stats(stats: Optional[MachineDailyStat], records: List[MachineData]) -> float:
    if stats and stats.energy_kwh is not None:
        return float(stats.energy_kwh)
    energy_ws = 0.0
    for idx, record in enumerate(records):
        if record.voltage is None or record.current is None:
            continue
        next_ts = records[idx + 1].timestamp if idx + 1 < len(records) else None
        duration = _duration_between(record.timestamp, next_ts)
        energy_ws += record.voltage * record.current * duration
    return energy_ws / 3_600_000


def _latest_kpi_day_for_machine(machine_id: int, up_to: date) -> Optional[date]:
    return (
        db.session.query(func.max(MachineKPI.date))
        .filter(MachineKPI.machine_id == machine_id, MachineKPI.date <= up_to)
        .scalar()
    )


def _latest_kpi_day_for_plant(plant_id: int, up_to: date) -> Optional[date]:
    return (
        db.session.query(func.max(MachineKPI.date))
        .filter(MachineKPI.plant_id == plant_id, MachineKPI.date <= up_to)
        .scalar()
    )


def _latest_kpi_day_for_company(company_id: int, up_to: date) -> Optional[date]:
    return (
        db.session.query(func.max(MachineKPI.date))
        .join(Machine, Machine.id == MachineKPI.machine_id)
        .filter(Machine.company_id == company_id, MachineKPI.date <= up_to)
        .scalar()
    )


def _failure_counts(machine: Machine, day: date) -> int:
    start_dt = datetime.combine(day, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)
    return (
        Alert.query.filter_by(machine_id=machine.id, company_id=machine.company_id)
        .filter(Alert.created_at >= start_dt, Alert.created_at < end_dt)
        .filter(Alert.severity.in_(["high", "critical"]))
        .count()
    )


def _quality_component(failure_count: int) -> float:
    penalty = min(0.3, failure_count * 0.02)
    return max(0.7, 1.0 - penalty)


def _cost_of_downtime(downtime_minutes: float, cost_per_hour: Decimal | float | int) -> Decimal:
    hours = downtime_minutes / 60.0
    return Decimal(str(cost_per_hour or 0)) * Decimal(str(hours))


def compute_daily_kpi(machine: Machine, day: date | None = None) -> MachineKPI:
    target_day = day or date.today()
    stats = MachineDailyStat.query.filter_by(machine_id=machine.id, period_date=target_day).first()
    records = _bucket_records(machine.id, target_day)
    running_seconds, idle_seconds, total_units = _runtime_and_units(records)
    energy_kwh = _energy_from_stats(stats, records)
    planned_seconds = PLANNED_SECONDS

    availability = (running_seconds / planned_seconds) if planned_seconds else 0.0
    performance = 0.0
    if running_seconds > 0:
        performance = (IDEAL_CYCLE_TIME_SEC * total_units) / running_seconds
    quality = _quality_component(_failure_counts(machine, target_day))

    availability = max(0.0, min(1.0, availability))
    performance = max(0.0, min(1.0, performance))
    quality = max(0.0, min(1.0, quality))

    oee = availability * performance * quality
    utilization_rate = availability
    energy_efficiency = (total_units / energy_kwh) if energy_kwh else 0.0
    downtime_minutes = max(0.0, (planned_seconds - running_seconds) / 60.0)
    cost_of_downtime = _cost_of_downtime(downtime_minutes, machine.cost_per_hour)

    existing = MachineKPI.query.filter_by(machine_id=machine.id, date=target_day).first()
    if not existing:
        existing = MachineKPI(machine_id=machine.id, plant_id=machine.plant_id, date=target_day)

    existing.oee = round(oee, 4)
    existing.availability = round(availability, 4)
    existing.performance = round(performance, 4)
    existing.quality = round(quality, 4)
    existing.utilization_rate = round(utilization_rate, 4)
    existing.energy_efficiency = round(energy_efficiency, 4)
    existing.downtime_minutes = round(downtime_minutes, 2)
    existing.cost_of_downtime = cost_of_downtime

    db.session.add(existing)
    db.session.commit()
    return existing


def get_machine_kpi(machine_id: int, company_id: int, day: date | None = None) -> Optional[MachineKPI]:
    target_day = day or date.today()
    machine = Machine.query.filter_by(id=machine_id, company_id=company_id).first()
    if not machine:
        return None

    existing = MachineKPI.query.filter_by(machine_id=machine.id, date=target_day).first()
    if existing:
        return existing

    fallback_day = _latest_kpi_day_for_machine(machine.id, target_day)
    if fallback_day:
        fallback = MachineKPI.query.filter_by(machine_id=machine.id, date=fallback_day).first()
        if fallback:
            return fallback

    return compute_daily_kpi(machine, target_day)


def _aggregate_kpi(records: Iterable[MachineKPI]) -> Dict[str, float]:
    count = 0
    sums: Dict[str, float] = defaultdict(float)
    for rec in records:
        count += 1
        sums["oee"] += rec.oee
        sums["availability"] += rec.availability
        sums["performance"] += rec.performance
        sums["quality"] += rec.quality
        sums["utilization_rate"] += rec.utilization_rate
        sums["energy_efficiency"] += rec.energy_efficiency
        sums["downtime_minutes"] += rec.downtime_minutes
        sums["cost_of_downtime"] += float(rec.cost_of_downtime or 0)
    if count == 0:
        return {k: 0.0 for k in sums} | {"count": 0}
    return {k: round(v / count, 4) for k, v in sums.items()} | {"count": count}


def plant_kpi_summary(plant_id: int, day: date | None = None) -> Dict[str, float]:
    target_day = day or date.today()
    chosen_day = _latest_kpi_day_for_plant(plant_id, target_day) or target_day
    records = MachineKPI.query.filter_by(plant_id=plant_id, date=chosen_day).all()
    summary = _aggregate_kpi(records)
    summary["as_of_date"] = chosen_day
    return summary


def company_kpi_summary(company_id: int, day: date | None = None) -> Dict[str, float]:
    target_day = day or date.today()
    chosen_day = _latest_kpi_day_for_company(company_id, target_day) or target_day
    records = (
        MachineKPI.query.join(Machine, MachineKPI.machine_id == Machine.id)
        .filter(Machine.company_id == company_id, MachineKPI.date == chosen_day)
        .all()
    )
    summary = _aggregate_kpi(records)
    summary["as_of_date"] = chosen_day
    return summary


def mtbf_hours(machine: Machine, start_dt: datetime, end_dt: datetime) -> float:
    failures = (
        Alert.query.filter_by(machine_id=machine.id, company_id=machine.company_id)
        .filter(Alert.created_at >= start_dt, Alert.created_at <= end_dt)
        .filter(Alert.severity.in_(["high", "critical"]))
        .count()
    )
    runtime_seconds = 0.0
    stats = (
        MachineDailyStat.query.filter_by(machine_id=machine.id)
        .filter(MachineDailyStat.period_date >= start_dt.date(), MachineDailyStat.period_date <= end_dt.date())
        .all()
    )
    for stat in stats:
        runtime_seconds += stat.running_seconds or 0
    if failures == 0:
        return (runtime_seconds / 3600.0) if runtime_seconds else 0.0
    return (runtime_seconds / 3600.0) / failures


def mttr_hours(machine: Machine, start_dt: datetime, end_dt: datetime) -> float:
    repairs = (
        Alert.query.filter_by(machine_id=machine.id, company_id=machine.company_id, is_resolved=True)
        .filter(Alert.resolved_at.isnot(None))
        .filter(Alert.resolved_at >= start_dt, Alert.resolved_at <= end_dt)
        .all()
    )
    if not repairs:
        return 0.0
    total_repair_seconds = 0.0
    for alert in repairs:
        total_repair_seconds += max(0.0, (alert.resolved_at - alert.created_at).total_seconds())
    return (total_repair_seconds / len(repairs)) / 3600.0


def downtime_trend(machine: Machine, days: int = 7) -> List[Dict[str, float]]:
    output: List[Dict[str, float]] = []
    for i in range(days):
        day = date.today() - timedelta(days=i)
        kpi = MachineKPI.query.filter_by(machine_id=machine.id, date=day).first()
        if not kpi:
            kpi = compute_daily_kpi(machine, day)
        output.append({"date": day.isoformat(), "downtime_minutes": kpi.downtime_minutes})
    return list(reversed(output))


def plant_downtime_trend(plant_id: int, days: int = 30) -> List[Dict[str, float]]:
    """Aggregate downtime minutes for a plant over the requested window.

    We use a single grouped query over MachineKPI to avoid N×D lookups and
    fill missing dates with zeros so the chart always renders a continuous
    series for the chosen window.
    """
    if days <= 0:
        return []

    start_day = date.today() - timedelta(days=days - 1)
    machine_ids = [m.id for m in Machine.query.filter_by(plant_id=plant_id).all()]
    if not machine_ids:
        return [{"date": (start_day + timedelta(days=i)).isoformat(), "downtime_minutes": 0.0} for i in range(days)]

    rows = (
        MachineKPI.query.with_entities(MachineKPI.date, func.sum(MachineKPI.downtime_minutes).label("downtime_minutes"))
        .filter(MachineKPI.machine_id.in_(machine_ids))
        .filter(MachineKPI.date >= start_day, MachineKPI.date <= date.today())
        .group_by(MachineKPI.date)
        .all()
    )
    totals = {row.date: float(row.downtime_minutes or 0) for row in rows}

    output: List[Dict[str, float]] = []
    for i in range(days):
        day = start_day + timedelta(days=i)
        output.append({"date": day.isoformat(), "downtime_minutes": round(totals.get(day, 0.0), 2)})
    return output


def utilization_rate(machine: Machine, start_dt: datetime, end_dt: datetime) -> float:
    stats = (
        MachineDailyStat.query.filter_by(machine_id=machine.id)
        .filter(MachineDailyStat.period_date >= start_dt.date(), MachineDailyStat.period_date <= end_dt.date())
        .all()
    )
    total_running = sum(stat.running_seconds or 0 for stat in stats)
    total_planned = PLANNED_SECONDS * max(1, len(stats))
    if total_planned == 0:
        return 0.0
    return (total_running / total_planned)


def energy_efficiency(machine: Machine, start_dt: datetime, end_dt: datetime) -> float:
    stats = (
        MachineDailyStat.query.filter_by(machine_id=machine.id)
        .filter(MachineDailyStat.period_date >= start_dt.date(), MachineDailyStat.period_date <= end_dt.date())
        .all()
    )
    total_energy = sum(stat.energy_kwh or 0 for stat in stats)
    records = _bucket_records(machine.id, start_dt.date())
    total_units = _runtime_and_units(records)[2]
    if total_energy <= 0:
        return 0.0
    return total_units / total_energy


def top_kpi_machines(company_id: int, limit: int = 10, day: date | None = None, best: bool = True) -> List[Dict]:
    target_day = day or date.today()
    # Always use the most recent KPI snapshot available for the company to avoid empty results
    chosen_day = _latest_kpi_day_for_company(company_id, target_day) or target_day
    query = (
        MachineKPI.query.join(Machine, Machine.id == MachineKPI.machine_id)
        .filter(Machine.company_id == company_id, MachineKPI.date == chosen_day)
    )
    order = MachineKPI.oee.desc() if best else MachineKPI.oee.asc()
    records = query.order_by(order).limit(limit).all()
    output = []
    for rec in records:
        output.append(
            {
                "machine_id": rec.machine_id,
                "plant_id": rec.plant_id,
                "oee": rec.oee,
                "downtime_minutes": rec.downtime_minutes,
                "cost_of_downtime": float(rec.cost_of_downtime or 0),
            }
        )
    return output


def plant_rankings(company_id: int, day: date | None = None) -> List[Dict]:
    target_day = day or date.today()
    # Fall back to the last computed KPI day if no metrics exist for today
    chosen_day = _latest_kpi_day_for_company(company_id, target_day) or target_day
    records = (
        db.session.query(MachineKPI.plant_id, func.avg(MachineKPI.oee).label("avg_oee"), func.sum(MachineKPI.cost_of_downtime).label("downtime_cost"))
        .join(Machine, Machine.id == MachineKPI.machine_id)
        .filter(Machine.company_id == company_id, MachineKPI.date == chosen_day)
        .group_by(MachineKPI.plant_id)
        .order_by(func.avg(MachineKPI.oee).desc())
        .all()
    )
    return [
        {
            "plant_id": row.plant_id,
            "oee": float(row.avg_oee or 0),
            "downtime_cost": float(row.downtime_cost or 0),
        }
        for row in records
    ]
