from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from functools import lru_cache
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import and_, func

from app.extensions import db
from app.models.alert import Alert
from app.models.ai_prediction import AIPrediction
from app.models.digital_twin import DigitalTwin, TwinSimulationHistory
from app.models.machine import Machine
from app.models.machine_data import MachineData
from app.models.machine_health import MachineHealthScore
from app.models.machine_kpi import MachineKPI
from app.models.workforce import MaintenanceTask, TechnicianPerformance

# ---- helpers ----

DEFAULT_DAYS = None  # no default window; use full history
MAX_DAYS = None  # no cap; caller can still pass explicit dates


def _parse_date(val: Optional[str], fallback: date) -> date:
    if not val:
        return fallback
    try:
        return datetime.fromisoformat(val).date()
    except ValueError:
        return fallback


def _clamp_dates(start: date | None, end: date | None) -> Tuple[date | None, date | None]:
    if start and end and start > end:
        start, end = end, start
    if start and end and MAX_DAYS and (end - start).days > MAX_DAYS:
        end = start + timedelta(days=MAX_DAYS)
    return start, end


def _moving_average(series: List[Dict[str, Any]], window: int = 3) -> List[Dict[str, Any]]:
    if window <= 1:
        return series
    values = [p["value"] for p in series]
    out: List[Dict[str, Any]] = []
    for idx, point in enumerate(series):
        start = max(0, idx - window + 1)
        slice_vals = values[start : idx + 1]
        out.append({"timestamp": point["timestamp"], "value": round(sum(slice_vals) / len(slice_vals), 4)})
    return out


def _growth_rate(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    first, last = values[0], values[-1]
    if first == 0:
        return 0.0
    return round(((last - first) / abs(first)) * 100, 4)


def _variance(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = mean(values)
    return round(sum((v - mu) ** 2 for v in values) / len(values), 4)


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    try:
        return round(pstdev(values), 4)
    except Exception:
        return 0.0


def _correlation_matrix(rows: List[Dict[str, float]], keys: List[str]) -> List[List[float]]:
    if not rows:
        return [[0.0 for _ in keys] for _ in keys]
    matrix: List[List[float]] = []
    for ki in keys:
        row: List[float] = []
        xi = [float(r.get(ki, 0) or 0) for r in rows]
        for kj in keys:
            xj = [float(r.get(kj, 0) or 0) for r in rows]
            row.append(_pearson(xi, xj))
        matrix.append(row)
    return matrix


def _pearson(x: List[float], y: List[float]) -> float:
    n = min(len(x), len(y))
    if n == 0:
        return 0.0
    x, y = x[:n], y[:n]
    mean_x, mean_y = mean(x), mean(y)
    num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    den_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
    den_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5
    if den_x == 0 or den_y == 0:
        return 0.0
    return round(num / (den_x * den_y), 4)


def _bins(values: List[float], bucket: int = 10) -> List[Dict[str, float]]:
    if not values:
        return []
    mn, mx = min(values), max(values)
    if mx == mn:
        return [{"label": f"{mn:.2f}", "value": len(values)}]
    step = (mx - mn) / bucket if bucket else 1
    buckets = [0 for _ in range(bucket)]
    for v in values:
        idx = int((v - mn) / step)
        idx = min(bucket - 1, max(0, idx))
        buckets[idx] += 1
    out = []
    for i, c in enumerate(buckets):
        start = mn + i * step
        end = start + step
        out.append({"label": f"{start:.2f}-{end:.2f}", "value": c})
    return out


def _sanitize_scope(user_role: str, plant_ids: Optional[List[int]]) -> Optional[List[int]]:
    if user_role in {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN"}:
        return plant_ids
    return plant_ids or None


# ---- filter handling ----


def parse_filters(args, user) -> Dict[str, Any]:
    # Ignore incoming date filters; use full history
    start_date = None
    end_date = None
    start_date, end_date = _clamp_dates(start_date, end_date)

    def _int_list(key: str) -> List[int]:
        raw = args.get(key)
        if not raw:
            return []
        out = []
        for part in str(raw).split(','):
            try:
                out.append(int(part))
            except ValueError:
                continue
        return out

    severity = args.get("severity", "").upper() or None
    risk = args.get("risk", "").upper() or None
    kpi_type = args.get("kpi_type") or None
    comparison_mode = args.get("comparison", "off") == "on"
    granularity = args.get("granularity", "daily")
    page = max(1, int(args.get("page", 1)))
    per_page = min(200, max(10, int(args.get("per_page", 50))))

    role = (getattr(user, "active_role", None) or getattr(user, "role", "") or "").upper()
    allowed_plants = _sanitize_scope(role, _int_list("plant_id"))

    return {
        "company_id": user.company_id,
        "role": role,
        "start_date": start_date,
        "end_date": end_date,
        "plant_ids": allowed_plants,
        "department_ids": _int_list("department_id"),
        "machine_ids": _int_list("machine_id"),
        "severity": severity,
        "risk": risk,
        "kpi_type": kpi_type,
        "comparison": comparison_mode,
        "granularity": granularity,
        "page": page,
        "per_page": per_page,
    }


# ---- base queries ----


def _machine_scope(filters: Dict[str, Any]):
    q = Machine.query.filter(Machine.company_id == filters["company_id"])
    if filters["plant_ids"]:
        q = q.filter(Machine.plant_id.in_(filters["plant_ids"]))
    if filters["department_ids"]:
        q = q.filter(Machine.department_id.in_(filters["department_ids"]))
    if filters["machine_ids"]:
        q = q.filter(Machine.id.in_(filters["machine_ids"]))
    return q


def _kpi_scope(filters: Dict[str, Any]):
    q = MachineKPI.query.filter(MachineKPI.machine.has(Machine.company_id == filters["company_id"]))
    if filters["start_date"]:
        q = q.filter(MachineKPI.date >= filters["start_date"])
    if filters["end_date"]:
        q = q.filter(MachineKPI.date <= filters["end_date"])
    if filters["plant_ids"]:
        q = q.filter(MachineKPI.plant_id.in_(filters["plant_ids"]))
    if filters["machine_ids"]:
        q = q.filter(MachineKPI.machine_id.in_(filters["machine_ids"]))
    return q


def _health_scope(filters: Dict[str, Any]):
    q = MachineHealthScore.query.filter(MachineHealthScore.company_id == filters["company_id"])
    if filters["start_date"]:
        q = q.filter(MachineHealthScore.calculated_at >= datetime.combine(filters["start_date"], datetime.min.time()))
    if filters["end_date"]:
        q = q.filter(MachineHealthScore.calculated_at <= datetime.combine(filters["end_date"], datetime.max.time()))
    if filters["plant_ids"]:
        q = q.filter(MachineHealthScore.plant_id.in_(filters["plant_ids"]))
    if filters["machine_ids"]:
        q = q.filter(MachineHealthScore.machine_id.in_(filters["machine_ids"]))
    if filters["risk"]:
        q = q.filter(MachineHealthScore.risk_level == filters["risk"])
    return q


def _prediction_scope(filters: Dict[str, Any]):
    q = AIPrediction.query.filter(AIPrediction.company_id == filters["company_id"])
    if filters["start_date"]:
        q = q.filter(AIPrediction.created_at >= datetime.combine(filters["start_date"], datetime.min.time()))
    if filters["end_date"]:
        q = q.filter(AIPrediction.created_at <= datetime.combine(filters["end_date"], datetime.max.time()))
    if filters["plant_ids"]:
        q = q.filter(AIPrediction.plant_id.in_(filters["plant_ids"]))
    if filters["machine_ids"]:
        q = q.filter(AIPrediction.machine_id.in_(filters["machine_ids"]))
    if filters["risk"]:
        q = q.filter(AIPrediction.risk_level == filters["risk"])
    return q


def _alert_scope(filters: Dict[str, Any]):
    q = Alert.query.filter(Alert.company_id == filters["company_id"])
    if filters["start_date"]:
        q = q.filter(Alert.created_at >= datetime.combine(filters["start_date"], datetime.min.time()))
    if filters["end_date"]:
        q = q.filter(Alert.created_at <= datetime.combine(filters["end_date"], datetime.max.time()))
    if filters["plant_ids"]:
        q = q.filter(Alert.plant_id.in_(filters["plant_ids"]))
    if filters["machine_ids"]:
        q = q.filter(Alert.machine_id.in_(filters["machine_ids"]))
    if filters["severity"]:
        q = q.filter(Alert.severity == filters["severity"])
    return q


# ---- data builders ----


def time_series(filters: Dict[str, Any]) -> Dict[str, Any]:
    kpis = _kpi_scope(filters).order_by(MachineKPI.date.asc()).all()
    health_rows = _health_scope(filters).order_by(MachineHealthScore.calculated_at.asc()).all()
    preds = _prediction_scope(filters).order_by(AIPrediction.created_at.asc()).all()

    oee_series = [
        {"timestamp": kpi.date.isoformat(), "value": round(kpi.oee, 4)} for kpi in kpis
    ]
    health_series = [
        {"timestamp": h.calculated_at.isoformat(), "value": round(h.health_score, 4)} for h in health_rows
    ]
    failure_series = [
        {"timestamp": p.created_at.isoformat(), "value": round(p.failure_probability, 4)} for p in preds
    ]

    downtime_series = [
        {"timestamp": kpi.date.isoformat(), "value": round(kpi.downtime_minutes or 0, 4)} for kpi in kpis
    ]
    downtime_causes = defaultdict(float)
    for kpi in kpis:
        downtime_causes["planned"] += (kpi.downtime_minutes or 0) * 0.4
        downtime_causes["unplanned"] += (kpi.downtime_minutes or 0) * 0.6
    stacked_downtime = [
        {"label": cause, "value": round(val, 4)} for cause, val in downtime_causes.items()
    ]

    energy_vs_output = [
        {
            "timestamp": kpi.date.isoformat(),
            "energy": round(kpi.energy_efficiency or 0, 4),
            "output": round(kpi.utilization_rate or 0, 4),
        }
        for kpi in kpis
    ]

    forecast = _moving_average(failure_series, window=5)

    return {
        "oee_health_failure": {
            "oee": oee_series,
            "health": health_series,
            "failure_probability": failure_series,
            "forecast": forecast,
        },
        "downtime_trend": downtime_series,
        "downtime_by_cause": stacked_downtime,
        "sla_breaches": [
            {"timestamp": kpi.date.isoformat(), "value": round((kpi.downtime_minutes or 0) / 60, 4)}
            for kpi in kpis
        ],
        "energy_vs_output": energy_vs_output,
    }


def distribution(filters: Dict[str, Any]) -> Dict[str, Any]:
    preds = _prediction_scope(filters).all()
    health = _health_scope(filters).all()

    failure_probs = [float(p.failure_probability or 0) for p in preds]
    health_scores = [float(h.health_score or 0) for h in health]

    plant_box: Dict[int, List[float]] = defaultdict(list)
    for h in health:
        plant_box[h.plant_id].append(float(h.health_score or 0))

    histogram = _bins(failure_probs, bucket=12)
    boxplot = [{"plant_id": pid, "values": vals} for pid, vals in plant_box.items()]
    violin = [{"machine_id": h.machine_id, "values": [float(h.health_score or 0)]} for h in health]

    md_query = MachineData.query.join(Machine).filter(Machine.company_id == filters["company_id"])
    if filters["plant_ids"]:
        md_query = md_query.filter(Machine.plant_id.in_(filters["plant_ids"]))
    if filters["machine_ids"]:
        md_query = md_query.filter(MachineData.machine_id.in_(filters["machine_ids"]))
    offset = (filters["page"] - 1) * filters["per_page"]
    md_rows = (
        md_query.order_by(MachineData.timestamp.desc())
        .offset(offset)
        .limit(filters["per_page"])
        .all()
    )
    density = _bins([float(p.current or 0) for p in md_rows if p.current is not None], bucket=10)

    return {
        "histogram": histogram,
        "boxplot": boxplot,
        "violin": violin,
        "density": density,
    }


def comparison(filters: Dict[str, Any]) -> Dict[str, Any]:
    kpis = _kpi_scope(filters).all()
    plants = defaultdict(list)
    severities = defaultdict(int)
    risky = defaultdict(float)
    for kpi in kpis:
        plants[kpi.plant_id].append(float(kpi.oee or 0))
        severities["LOW"] += max(0, kpi.oee)
    for alert in _alert_scope(filters).all():
        severities[alert.severity] += 1
    for pred in _prediction_scope(filters).all():
        risky[pred.machine_id] = max(risky[pred.machine_id], float(pred.failure_probability or 0))

    radar = []
    for plant_id, vals in plants.items():
        radar.append({
            "plant_id": plant_id,
            "oee": round(mean(vals), 4) if vals else 0,
            "performance": round(mean(vals) * 0.9, 4) if vals else 0,
            "quality": round(mean(vals) * 0.95, 4) if vals else 0,
            "availability": round(mean(vals) * 0.92, 4) if vals else 0,
        })

    spider = [
        {"label": "oee", "value": round(mean([float(k.oee or 0) for k in kpis]) if kpis else 0, 4)},
        {"label": "availability", "value": round(mean([float(k.availability or 0) for k in kpis]) if kpis else 0, 4)},
        {"label": "performance", "value": round(mean([float(k.performance or 0) for k in kpis]) if kpis else 0, 4)},
        {"label": "quality", "value": round(mean([float(k.quality or 0) for k in kpis]) if kpis else 0, 4)},
        {"label": "utilization", "value": round(mean([float(k.utilization_rate or 0) for k in kpis]) if kpis else 0, 4)},
    ]

    return {
        "grouped_oee": [{"plant_id": pid, "value": round(mean(vals), 4)} for pid, vals in plants.items()],
        "severity_breakdown": [{"label": k, "value": v} for k, v in severities.items()],
        "risky_machines": [
            {"machine_id": mid, "value": val} for mid, val in sorted(risky.items(), key=lambda x: x[1], reverse=True)[:10]
        ],
        "radar": radar,
        "spider": spider,
    }


def correlation(filters: Dict[str, Any]) -> Dict[str, Any]:
    kpis = _kpi_scope(filters).all()
    rows = [{
        "oee": float(k.oee or 0),
        "availability": float(k.availability or 0),
        "performance": float(k.performance or 0),
        "quality": float(k.quality or 0),
        "utilization_rate": float(k.utilization_rate or 0),
        "energy_efficiency": float(k.energy_efficiency or 0),
    } for k in kpis]
    keys = ["oee", "availability", "performance", "quality", "utilization_rate", "energy_efficiency"]
    matrix = _correlation_matrix(rows, keys)
    scatter = [
        {"x": r["performance"], "y": r["quality"], "machine_id": kpis[idx].machine_id if idx < len(kpis) else None}
        for idx, r in enumerate(rows)
    ]
    bubbles = [
        {"x": r["oee"], "y": r["utilization_rate"], "r": r["energy_efficiency"] or 0}
        for r in rows
    ]
    return {
        "scatter": scatter,
        "bubbles": bubbles,
        "matrix": matrix,
        "pairwise": rows[:100],
    }


def risk(filters: Dict[str, Any]) -> Dict[str, Any]:
    preds = _prediction_scope(filters).all()
    health = _health_scope(filters).all()
    risk_grid = defaultdict(lambda: defaultdict(float))
    for p in preds:
        risk_grid[p.plant_id][p.machine_id] = max(risk_grid[p.plant_id][p.machine_id], float(p.failure_probability or 0))
    gauge = mean([float(p.failure_probability or 0) for p in preds]) if preds else 0
    timeline = sorted([
        {"timestamp": p.created_at.isoformat(), "value": float(p.failure_probability or 0)} for p in preds
    ], key=lambda x: x["timestamp"])
    heat_calendar = defaultdict(int)
    for a in _alert_scope(filters).all():
        day = a.created_at.date().isoformat()
        heat_calendar[day] += 1
    return {
        "grid": [{"plant_id": pid, "machines": [{"machine_id": mid, "risk": val} for mid, val in machines.items()]} for pid, machines in risk_grid.items()],
        "gauge": round(gauge, 4),
        "timeline": timeline,
        "calendar": [{"date": d, "count": c} for d, c in heat_calendar.items()],
    }


def financial(filters: Dict[str, Any]) -> Dict[str, Any]:
    kpis = _kpi_scope(filters).all()
    revenue_trend = [
        {"timestamp": k.date.isoformat(), "value": float(k.revenue) if hasattr(k, "revenue") else float(k.utilization_rate or 0) * float(k.performance or 0) * 1000}
        for k in kpis
    ]
    downtime_cost = [
        {"timestamp": k.date.isoformat(), "value": float(k.cost_of_downtime or 0)} for k in kpis
    ]
    spare_forecast = [
        {"timestamp": k.date.isoformat(), "value": float(k.downtime_minutes or 0) * 0.1} for k in kpis
    ]
    waterfall = [
        {"label": "budget", "value": 100000},
        {"label": "downtime_cost", "value": -sum(float(k.cost_of_downtime or 0) for k in kpis)},
        {"label": "maintenance", "value": -5000},
        {"label": "savings", "value": 12000},
    ]
    return {
        "revenue_loss": revenue_trend,
        "downtime_cost": downtime_cost,
        "cost_to_failure": [{"timestamp": k.date.isoformat(), "value": float(k.failure_prob) if hasattr(k, "failure_prob") else float(k.oee or 0)} for k in kpis],
        "spare_parts": spare_forecast,
        "waterfall": waterfall,
    }


def workforce(filters: Dict[str, Any]) -> Dict[str, Any]:
    techs = TechnicianPerformance.query
    if filters["plant_ids"]:
        techs = techs.filter(TechnicianPerformance.plant_id.in_(filters["plant_ids"]))
    ranking = techs.order_by(TechnicianPerformance.efficiency_score.desc().nullslast()).limit(10).all()
    donut = [
        {"label": "compliant", "value": float(t.sla_compliance_rate or 0)} for t in ranking
    ]
    tasks = MaintenanceTask.query.join(Machine).filter(Machine.company_id == filters["company_id"])
    if filters["plant_ids"]:
        tasks = tasks.filter(Machine.plant_id.in_(filters["plant_ids"]))
    time_trend = []
    offset = (filters["page"] - 1) * filters["per_page"]
    for t in tasks.order_by(MaintenanceTask.assigned_at.desc().nullslast()).offset(offset).limit(filters["per_page"]).all():
        if t.assigned_at and t.completed_at:
            delta = (t.completed_at - t.assigned_at).total_seconds() / 3600
            time_trend.append({"timestamp": t.completed_at.isoformat(), "value": delta})
    workload = [
        {"label": t.status, "value": 1}
        for t in tasks.order_by(MaintenanceTask.assigned_at.desc().nullslast()).offset(offset).limit(filters["per_page"]).all()
    ]
    return {
        "ranking": [
            {"user_id": t.user_id, "score": float(t.efficiency_score or 0)} for t in ranking
        ],
        "sla": donut,
        "resolution": time_trend,
        "workload": workload,
    }


def esg(filters: Dict[str, Any]) -> Dict[str, Any]:
    kpis = _kpi_scope(filters).all()
    energy_trend = [
        {"timestamp": k.date.isoformat(), "value": float(k.energy_efficiency or 0)} for k in kpis
    ]
    efficiency = _moving_average(energy_trend, window=4)
    gauge = round(mean([float(k.energy_efficiency or 0) for k in kpis]) if kpis else 0, 4)
    carbon = [
        {"timestamp": k.date.isoformat(), "value": float(k.utilization_rate or 0) * 0.2} for k in kpis
    ]
    return {
        "energy": energy_trend,
        "efficiency": efficiency,
        "sustainability_gauge": gauge,
        "carbon": carbon,
    }


def predictive(filters: Dict[str, Any]) -> Dict[str, Any]:
    preds = _prediction_scope(filters).order_by(AIPrediction.created_at.asc()).all()
    trend = [{"timestamp": p.created_at.isoformat(), "value": float(p.failure_probability or 0)} for p in preds]
    rul = [{"timestamp": p.created_at.isoformat(), "value": float(p.remaining_useful_life_hours or 0)} for p in preds]
    degradation = [{"timestamp": p.created_at.isoformat(), "value": float(p.degradation_score or 0)} for p in preds]
    anomaly = [{"timestamp": p.created_at.isoformat(), "value": float(p.anomaly_score or 0)} for p in preds]
    confidence = _bins([float(p.confidence_score or 0) for p in preds], bucket=10)
    return {
        "failure_trend": trend,
        "rul": rul,
        "degradation": degradation,
        "anomaly": anomaly,
        "confidence": confidence,
    }


def twin(filters: Dict[str, Any]) -> Dict[str, Any]:
    twins = DigitalTwin.query.filter_by(company_id=filters["company_id"]).all()
    if filters["plant_ids"]:
        twins = [t for t in twins if t.plant_id in filters["plant_ids"]]
    live_vs_sim = []
    risk_delta = []
    matrix = []
    for twin in twins:
        latest_sim = twin.simulations.order_by(TwinSimulationHistory.created_at.desc()).first()
        live_vs_sim.append({
            "machine_id": twin.machine_id,
            "live": float(twin.baseline_oee or 0),
            "simulated": float(latest_sim.simulated_oee) if latest_sim else float(twin.baseline_oee or 0),
        })
        risk_delta.append({
            "machine_id": twin.machine_id,
            "value": float(latest_sim.risk_delta) if latest_sim else float(twin.degradation_rate or 0),
        })
        if latest_sim:
            matrix.append({
                "simulation_type": latest_sim.simulation_type,
                "oee": float(latest_sim.simulated_oee),
                "failure_probability": float(latest_sim.simulated_failure_probability),
                "health": float(latest_sim.simulated_health_score),
            })
    return {
        "live_vs_sim": live_vs_sim,
        "risk_delta": risk_delta,
        "matrix": matrix,
    }


# ---- orchestrator ----

@lru_cache(maxsize=64)
def _cached_payload(key: str) -> Dict[str, Any]:
    return {}


def analytics_summary(filters: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "kpi_trends": time_series(filters),
        "risk_distribution": distribution(filters),
        "comparison": comparison(filters),
        "financial_analytics": financial(filters),
        "workforce_analytics": workforce(filters),
        "energy_analytics": esg(filters),
        "predictive_analytics": predictive(filters),
        "twin_analytics": twin(filters),
    }
    payload["correlation"] = correlation(filters)
    payload["risk"] = risk(filters)
    return payload


def paginated_response(filters: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "filters": filters,
        "data": payload,
        "meta": {
            "page": filters["page"],
            "per_page": filters["per_page"],
        },
    }
