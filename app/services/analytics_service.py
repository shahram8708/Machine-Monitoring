from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, date
from typing import Dict, Iterable, List, Optional, Tuple

from app.extensions import db
from app.models.machine_data import MachineData
from app.models.machine_stats import MachineDailyStat, MachineHourlyStat

RETENTION_DAYS = 90


def _cutoff_dt() -> datetime:
    return datetime.utcnow() - timedelta(days=RETENTION_DAYS)


def _default_duration_seconds(current_ts: datetime, next_ts: Optional[datetime]) -> float:
    if next_ts is None:
        return 60.0
    duration = (next_ts - current_ts).total_seconds()
    if duration <= 0:
        return 60.0
    return duration


def _aggregate_energy_from_raw(records: List[MachineData]) -> float:
    if not records:
        return 0.0

    energy_ws = 0.0
    for idx, record in enumerate(records):
        if record.voltage is None or record.current is None:
            continue
        next_ts = records[idx + 1].timestamp if idx + 1 < len(records) else None
        duration_seconds = _default_duration_seconds(record.timestamp, next_ts)
        energy_ws += record.voltage * record.current * duration_seconds

    # Convert watt-seconds to kWh
    return energy_ws / 3_600_000


def _energy_series_from_raw(records: List[MachineData]) -> List[Dict[str, float]]:
    if not records:
        return []

    buckets: Dict[date, float] = defaultdict(float)
    for idx, record in enumerate(records):
        if record.voltage is None or record.current is None:
            continue
        next_ts = records[idx + 1].timestamp if idx + 1 < len(records) else None
        duration_seconds = _default_duration_seconds(record.timestamp, next_ts)
        energy_kwh = (record.voltage * record.current * duration_seconds) / 3_600_000
        buckets[record.timestamp.date()] += energy_kwh

    output: List[Dict[str, float]] = []
    for bucket_date, value in sorted(buckets.items()):
        output.append({
            "timestamp": datetime.combine(bucket_date, datetime.min.time()).isoformat(),
            "value": round(value, 4),
        })
    return output


def _aggregate_runtime_from_raw(records: List[MachineData]) -> Dict[str, float]:
    running_seconds = 0.0
    idle_seconds = 0.0
    for idx, record in enumerate(records):
        next_ts = records[idx + 1].timestamp if idx + 1 < len(records) else None
        duration_seconds = _default_duration_seconds(record.timestamp, next_ts)
        if record.running_status:
            running_seconds += duration_seconds
        else:
            idle_seconds += duration_seconds
    return {
        "running_hours": running_seconds / 3600.0,
        "idle_hours": idle_seconds / 3600.0,
    }


def _temperature_series_from_raw(records: List[MachineData]) -> List[Dict[str, Optional[float]]]:
    return [
        {"timestamp": record.timestamp.isoformat(), "value": record.temperature}
        for record in records
        if record.temperature is not None
    ]


def _vibration_series_from_raw(records: List[MachineData]) -> List[Dict[str, Optional[float]]]:
    return [
        {"timestamp": record.timestamp.isoformat(), "value": record.vibration}
        for record in records
        if record.vibration is not None
    ]


def _energy_series_from_hourly(stats: Iterable[MachineHourlyStat]) -> List[Dict[str, float]]:
    return [
        {"timestamp": stat.period_start.isoformat(), "value": stat.energy_kwh or 0.0}
        for stat in stats
    ]


def _series_from_hourly(stats: Iterable[MachineHourlyStat], field: str) -> List[Dict[str, Optional[float]]]:
    output: List[Dict[str, Optional[float]]] = []
    for stat in stats:
        value = getattr(stat, field)
        if value is None:
            continue
        output.append({"timestamp": stat.period_start.isoformat(), "value": value})
    return output


def get_temperature_trend(machine_id: int, start_date: datetime, end_date: datetime) -> List[Dict[str, float]]:
    cutoff = _cutoff_dt()
    if start_date >= cutoff:
        records = (
            MachineData.query.filter_by(machine_id=machine_id)
            .filter(MachineData.timestamp >= start_date, MachineData.timestamp <= end_date)
            .order_by(MachineData.timestamp.asc())
            .all()
        )
        return _temperature_series_from_raw(records)

    stats = (
        MachineHourlyStat.query.filter_by(machine_id=machine_id)
        .filter(MachineHourlyStat.period_start >= start_date, MachineHourlyStat.period_start <= end_date)
        .order_by(MachineHourlyStat.period_start.asc())
        .all()
    )
    if stats:
        return _series_from_hourly(stats, "temperature_avg")

    # Fallback to daily stats if hourly is unavailable
    daily_stats = (
        MachineDailyStat.query.filter_by(machine_id=machine_id)
        .filter(MachineDailyStat.period_date >= start_date.date(), MachineDailyStat.period_date <= end_date.date())
        .order_by(MachineDailyStat.period_date.asc())
        .all()
    )
    return [
        {"timestamp": datetime.combine(stat.period_date, datetime.min.time()).isoformat(), "value": stat.temperature_avg}
        for stat in daily_stats
        if stat.temperature_avg is not None
    ]


def get_vibration_trend(machine_id: int, start_date: datetime, end_date: datetime) -> List[Dict[str, float]]:
    cutoff = _cutoff_dt()
    if start_date >= cutoff:
        records = (
            MachineData.query.filter_by(machine_id=machine_id)
            .filter(MachineData.timestamp >= start_date, MachineData.timestamp <= end_date)
            .order_by(MachineData.timestamp.asc())
            .all()
        )
        return _vibration_series_from_raw(records)

    stats = (
        MachineHourlyStat.query.filter_by(machine_id=machine_id)
        .filter(MachineHourlyStat.period_start >= start_date, MachineHourlyStat.period_start <= end_date)
        .order_by(MachineHourlyStat.period_start.asc())
        .all()
    )
    if stats:
        return _series_from_hourly(stats, "vibration_avg")

    daily_stats = (
        MachineDailyStat.query.filter_by(machine_id=machine_id)
        .filter(MachineDailyStat.period_date >= start_date.date(), MachineDailyStat.period_date <= end_date.date())
        .order_by(MachineDailyStat.period_date.asc())
        .all()
    )
    return [
        {"timestamp": datetime.combine(stat.period_date, datetime.min.time()).isoformat(), "value": stat.vibration_avg}
        for stat in daily_stats
        if stat.vibration_avg is not None
    ]


def get_energy_consumption(machine_id: int, start_date: datetime, end_date: datetime) -> List[Dict[str, float]]:
    cutoff = _cutoff_dt()
    if start_date >= cutoff:
        records = (
            MachineData.query.filter_by(machine_id=machine_id)
            .filter(MachineData.timestamp >= start_date, MachineData.timestamp <= end_date)
            .order_by(MachineData.timestamp.asc())
            .all()
        )
        return _energy_series_from_raw(records)

    stats = (
        MachineDailyStat.query.filter_by(machine_id=machine_id)
        .filter(MachineDailyStat.period_date >= start_date.date(), MachineDailyStat.period_date <= end_date.date())
        .order_by(MachineDailyStat.period_date.asc())
        .all()
    )
    return [
        {"timestamp": datetime.combine(stat.period_date, datetime.min.time()).isoformat(), "value": stat.energy_kwh or 0.0}
        for stat in stats
    ]


def get_runtime_stats(machine_id: int, start_date: datetime, end_date: datetime) -> Dict[str, float]:
    cutoff = _cutoff_dt()
    if start_date >= cutoff:
        records = (
            MachineData.query.filter_by(machine_id=machine_id)
            .filter(MachineData.timestamp >= start_date, MachineData.timestamp <= end_date)
            .order_by(MachineData.timestamp.asc())
            .all()
        )
        return _aggregate_runtime_from_raw(records)

    stats = (
        MachineDailyStat.query.filter_by(machine_id=machine_id)
        .filter(MachineDailyStat.period_date >= start_date.date(), MachineDailyStat.period_date <= end_date.date())
        .all()
    )
    running_hours = sum(stat.running_seconds or 0 for stat in stats) / 3600.0
    idle_hours = sum(stat.idle_seconds or 0 for stat in stats) / 3600.0
    return {"running_hours": running_hours, "idle_hours": idle_hours}


# ---- Aggregation pipeline ----

def _bucket_key(ts: datetime) -> datetime:
    return ts.replace(minute=0, second=0, microsecond=0)


def aggregate_hourly_stats(start_dt: datetime, end_dt: datetime) -> None:
    """Aggregate raw machine_data into hourly summaries."""
    records = (
        MachineData.query.filter(MachineData.timestamp >= start_dt, MachineData.timestamp < end_dt)
        .order_by(MachineData.machine_id.asc(), MachineData.timestamp.asc())
        .all()
    )

    buckets: Dict[Tuple[int, datetime], Dict[str, float]] = defaultdict(lambda: {
        "temp_sum": 0.0,
        "temp_count": 0,
        "vib_sum": 0.0,
        "vib_count": 0,
        "volt_sum": 0.0,
        "volt_count": 0,
        "curr_sum": 0.0,
        "curr_count": 0,
        "energy_ws": 0.0,
        "running_seconds": 0.0,
        "idle_seconds": 0.0,
        "data_points": 0,
    })

    for idx, record in enumerate(records):
        key = (record.machine_id, _bucket_key(record.timestamp))
        bucket = buckets[key]
        bucket["data_points"] += 1

        if record.temperature is not None:
            bucket["temp_sum"] += record.temperature
            bucket["temp_count"] += 1
        if record.vibration is not None:
            bucket["vib_sum"] += record.vibration
            bucket["vib_count"] += 1
        if record.voltage is not None:
            bucket["volt_sum"] += record.voltage
            bucket["volt_count"] += 1
        if record.current is not None:
            bucket["curr_sum"] += record.current
            bucket["curr_count"] += 1

        next_ts = None
        if idx + 1 < len(records) and records[idx + 1].machine_id == record.machine_id:
            next_ts = records[idx + 1].timestamp
        duration_seconds = _default_duration_seconds(record.timestamp, next_ts)

        if record.voltage is not None and record.current is not None:
            bucket["energy_ws"] += record.voltage * record.current * duration_seconds

        if record.running_status:
            bucket["running_seconds"] += duration_seconds
        else:
            bucket["idle_seconds"] += duration_seconds

    for (machine_id, period_start), vals in buckets.items():
        stat = (
            MachineHourlyStat.query.filter_by(machine_id=machine_id, period_start=period_start).first()
        )
        if not stat:
            stat = MachineHourlyStat(machine_id=machine_id, period_start=period_start)

        stat.temperature_avg = (vals["temp_sum"] / vals["temp_count"]) if vals["temp_count"] else None
        stat.vibration_avg = (vals["vib_sum"] / vals["vib_count"]) if vals["vib_count"] else None
        stat.voltage_avg = (vals["volt_sum"] / vals["volt_count"]) if vals["volt_count"] else None
        stat.current_avg = (vals["curr_sum"] / vals["curr_count"]) if vals["curr_count"] else None
        stat.energy_kwh = vals["energy_ws"] / 3_600_000
        stat.running_seconds = vals["running_seconds"]
        stat.idle_seconds = vals["idle_seconds"]
        stat.data_points = vals["data_points"]
        stat.period_end = period_start + timedelta(hours=1)

        db.session.add(stat)

    db.session.commit()


def aggregate_daily_stats(start_date: date, end_date: date) -> None:
    """Aggregate hourly stats into daily summaries."""
    hourly_stats = (
        MachineHourlyStat.query.filter(MachineHourlyStat.period_start >= datetime.combine(start_date, datetime.min.time()))
        .filter(MachineHourlyStat.period_start < datetime.combine(end_date + timedelta(days=1), datetime.min.time()))
        .all()
    )

    daily: Dict[Tuple[int, date], Dict[str, float]] = defaultdict(lambda: {
        "temp_sum": 0.0,
        "temp_count": 0,
        "vib_sum": 0.0,
        "vib_count": 0,
        "volt_sum": 0.0,
        "volt_count": 0,
        "curr_sum": 0.0,
        "curr_count": 0,
        "energy_kwh": 0.0,
        "running_seconds": 0.0,
        "idle_seconds": 0.0,
        "data_points": 0,
    })

    for stat in hourly_stats:
        key = (stat.machine_id, stat.period_start.date())
        bucket = daily[key]
        if stat.temperature_avg is not None:
            bucket["temp_sum"] += stat.temperature_avg
            bucket["temp_count"] += 1
        if stat.vibration_avg is not None:
            bucket["vib_sum"] += stat.vibration_avg
            bucket["vib_count"] += 1
        if stat.voltage_avg is not None:
            bucket["volt_sum"] += stat.voltage_avg
            bucket["volt_count"] += 1
        if stat.current_avg is not None:
            bucket["curr_sum"] += stat.current_avg
            bucket["curr_count"] += 1
        bucket["energy_kwh"] += stat.energy_kwh or 0.0
        bucket["running_seconds"] += stat.running_seconds or 0.0
        bucket["idle_seconds"] += stat.idle_seconds or 0.0
        bucket["data_points"] += stat.data_points or 0

    for (machine_id, period_date), vals in daily.items():
        record = (
            MachineDailyStat.query.filter_by(machine_id=machine_id, period_date=period_date).first()
        )
        if not record:
            record = MachineDailyStat(machine_id=machine_id, period_date=period_date)

        record.temperature_avg = (vals["temp_sum"] / vals["temp_count"]) if vals["temp_count"] else None
        record.vibration_avg = (vals["vib_sum"] / vals["vib_count"]) if vals["vib_count"] else None
        record.voltage_avg = (vals["volt_sum"] / vals["volt_count"]) if vals["volt_count"] else None
        record.current_avg = (vals["curr_sum"] / vals["curr_count"]) if vals["curr_count"] else None
        record.energy_kwh = vals["energy_kwh"]
        record.running_seconds = vals["running_seconds"]
        record.idle_seconds = vals["idle_seconds"]
        record.data_points = vals["data_points"]

        db.session.add(record)

    db.session.commit()


def purge_raw_data_older_than(days: int = RETENTION_DAYS) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    deleted = MachineData.query.filter(MachineData.timestamp < cutoff).delete(synchronize_session=False)
    db.session.commit()
    return deleted


def run_nightly_aggregation(app) -> None:
    with app.app_context():
        now = datetime.utcnow()
        # Aggregate the last 48 hours to handle late-arriving data
        start_dt = (now - timedelta(days=2)).replace(minute=0, second=0, microsecond=0)
        end_dt = now.replace(minute=0, second=0, microsecond=0)
        aggregate_hourly_stats(start_dt, end_dt)
        aggregate_daily_stats(start_dt.date(), end_dt.date())
        purge_raw_data_older_than(RETENTION_DAYS)
