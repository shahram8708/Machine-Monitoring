from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import func
from app.extensions import db
from app.models import (
    AdvancedReport,
    AIPrediction,
    Machine,
    MachineHealthScore,
    MachineKPI,
    Plant,
    RootCauseAnalysis,
    Company,
)
from app.services.financial_service import cost_to_failure
from app.services.esg_service import esg_summary
from app.services.gemini_service import generate_gemini_response
from app.services.export_service import export_report
from app.services.cache_service import get_cache, set_cache
from app.services.usage_service import track_usage
from app.ai.prompt_templates import advanced_report_summary_prompt
from config import get_config

REPORT_TYPES = {
    "predictive_maintenance": "Predictive Maintenance Roadmap",
    "cross_plant_comparison": "Cross-Plant Comparison",
    "failure_forecasting": "Failure Forecasting",
    "downtime_financial": "Downtime Financial",
    "strategic_summary": "AI Strategic Summary",
}

SUPPORTED_FORMATS = {"PDF", "EXCEL", "JSON", "XLSX", "XLS", "CSV"}


def _normalize_format(export_format: str) -> str:
    fmt = (export_format or "PDF").upper()
    if fmt in {"XLS", "XLSX"}:
        return "EXCEL"
    if fmt == "CSV":
        return "CSV"
    if fmt in SUPPORTED_FORMATS:
        return fmt
    return "PDF"


def _resolve_export_path(path: str | None) -> str | None:
    if not path:
        return None
    if os.path.isabs(path):
        return path
    return os.path.join(get_config().EXPORT_BASE_DIR, path)


def _file_exists(path: str | None) -> bool:
    resolved = _resolve_export_path(path)
    return bool(resolved and os.path.exists(resolved))


def _company_name(company_id: int) -> str:
    company = Company.query.get(company_id)
    return company.company_name if company else "Company"


def _kpi_summary(company_id: int) -> Dict[str, float]:
    avg_oee = (
        MachineKPI.query.with_entities(func.avg(MachineKPI.oee))
        .join(Machine)
        .filter(Machine.company_id == company_id)
        .scalar()
    ) or 0
    avg_availability = (
        MachineKPI.query.with_entities(func.avg(MachineKPI.availability))
        .join(Machine)
        .filter(Machine.company_id == company_id)
        .scalar()
    ) or 0
    avg_performance = (
        MachineKPI.query.with_entities(func.avg(MachineKPI.performance))
        .join(Machine)
        .filter(Machine.company_id == company_id)
        .scalar()
    ) or 0
    avg_quality = (
        MachineKPI.query.with_entities(func.avg(MachineKPI.quality))
        .join(Machine)
        .filter(Machine.company_id == company_id)
        .scalar()
    ) or 0
    return {
        "oee": round(avg_oee, 3),
        "availability": round(avg_availability, 3),
        "performance": round(avg_performance, 3),
        "quality": round(avg_quality, 3),
    }


def _health_overview(company_id: int) -> Dict[str, Any]:
    avg_health = (
        MachineHealthScore.query.with_entities(func.avg(MachineHealthScore.health_score))
        .join(Machine)
        .filter(Machine.company_id == company_id)
        .scalar()
    ) or 0
    critical = (
        MachineHealthScore.query.join(Machine)
        .filter(Machine.company_id == company_id, MachineHealthScore.risk_level == "CRITICAL")
        .count()
    )
    return {"avg_health": round(avg_health, 2), "critical_machines": critical}


def _prediction_outlook(company_id: int) -> List[Dict[str, Any]]:
    rows = (
        AIPrediction.query.filter_by(company_id=company_id)
        .order_by(AIPrediction.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "machine_id": r.machine_id,
            "plant_id": r.plant_id,
            "failure_probability": r.failure_probability,
            "remaining_useful_life_hours": r.remaining_useful_life_hours,
            "risk_level": r.risk_level,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def _rca_insights(company_id: int) -> List[Dict[str, Any]]:
    rows = (
        RootCauseAnalysis.query.join(Machine)
        .filter(Machine.company_id == company_id)
        .order_by(RootCauseAnalysis.created_at.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "machine_id": r.machine_id,
            "primary_root_cause": r.primary_root_cause,
            "confidence": r.confidence_score,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def _financial_projection(company_id: int) -> Dict[str, Any]:
    machine = Machine.query.filter_by(company_id=company_id).first()
    if not machine:
        return {"projected_downtime_cost": 0, "projected_revenue_loss": 0, "total_risk_exposure": 0}
    return cost_to_failure(machine.id, company_id)


def _cross_plant_view(company_id: int) -> List[Dict[str, Any]]:
    rows = (
        db.session.query(
            Plant.id,
            Plant.name,
            func.avg(MachineKPI.oee).label("oee"),
            func.avg(MachineHealthScore.health_score).label("health_score"),
            func.count(Machine.id).label("machines"),
        )
        .join(Machine, Machine.plant_id == Plant.id)
        .outerjoin(MachineKPI, MachineKPI.machine_id == Machine.id)
        .outerjoin(MachineHealthScore, MachineHealthScore.machine_id == Machine.id)
        .filter(Plant.company_id == company_id)
        .group_by(Plant.id, Plant.name)
        .all()
    )
    return [
        {
            "plant_id": row.id,
            "plant_name": row.name,
            "avg_oee": round(row.oee or 0, 3),
            "avg_health": round(row.health_score or 0, 3),
            "machines": row.machines,
        }
        for row in rows
    ]


def _esg_view(company_id: int) -> Dict[str, Any]:
    machine = Machine.query.filter_by(company_id=company_id).first()
    if not machine:
        return {"total_energy_kwh": 0, "sustainability_score": 0, "carbon_proxy_kg": 0}
    return esg_summary(machine.id, company_id)


def _build_payload(company_id: int) -> Dict[str, Any]:
    kpi_key = f"kpi:{company_id}"
    health_key = f"health:{company_id}"
    kpi_summary = get_cache(kpi_key) or _kpi_summary(company_id)
    health_overview = get_cache(health_key) or _health_overview(company_id)
    set_cache(kpi_key, kpi_summary)
    set_cache(health_key, health_overview)

    return {
        "kpi_summary": kpi_summary,
        "health_overview": health_overview,
        "prediction_outlook": _prediction_outlook(company_id),
        "rca_insights": _rca_insights(company_id),
        "financial_projection": _financial_projection(company_id),
        "cross_plant": _cross_plant_view(company_id),
        "esg": _esg_view(company_id),
    }


def _ai_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return generate_gemini_response(advanced_report_summary_prompt, data)
    except Exception:  # noqa: BLE001
        return {
            "executive_summary": "AI unavailable; showing synthesized snapshot.",
            "key_risks": ["Insufficient AI response"],
            "performance_gaps": ["AI summary unavailable"],
            "strategic_recommendations": ["Retry after AI service is restored"],
            "confidence": 0,
        }


def generate_advanced_report(
    company_id: int,
    user_id: int,
    report_type: str,
    export_format: str = "PDF",
    *,
    force_regen: bool = False,
    persist: bool = True,
) -> Dict[str, Any]:
    """Generate an advanced report.

    If ``persist`` is False the report is generated and returned immediately
    without inserting any database rows or caching the result.
    """

    fmt = _normalize_format(export_format)

    cache_key = f"adv-report:{company_id}:{report_type}:{fmt}"
    cached = get_cache(cache_key) if persist else None
    if cached and not force_regen and _file_exists(cached.get("file_path")):
        return cached

    payload = _build_payload(company_id)
    payload["report_type"] = report_type
    payload["ai_summary"] = _ai_summary(payload)

    company_name = _company_name(company_id)
    cfg = get_config()
    os.makedirs(cfg.EXPORT_BASE_DIR, exist_ok=True)
    file_path = export_report(payload, fmt, REPORT_TYPES.get(report_type, report_type), company_name)

    result = {
        "report_id": None,
        "file_path": file_path,
        "format": fmt,
        "ai_summary": payload.get("ai_summary"),
    }

    if persist:
        report = AdvancedReport(
            company_id=company_id,
            report_type=report_type,
            report_data=payload,
            generated_by=user_id,
            generated_at=datetime.utcnow(),
            file_path=file_path,
            format=export_format.upper(),
        )
        db.session.add(report)
        db.session.commit()

        track_usage(company_id, "report_generation")

        result["report_id"] = report.id
        set_cache(cache_key, result, ttl_seconds=get_config().REPORT_CACHE_TTL_SECONDS)

    return result


def list_reports(company_id: int, page: int = 1, per_page: int = 20):
    query = (
        AdvancedReport.query.filter_by(company_id=company_id)
        .order_by(AdvancedReport.generated_at.desc())
    )
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    items = [
        {
            "id": r.id,
            "report_type": REPORT_TYPES.get(r.report_type, r.report_type),
            "format": r.format,
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            "file_path": r.file_path,
        }
        for r in pagination.items
    ]
    return {"items": items, "total": pagination.total, "page": pagination.page, "pages": pagination.pages}


def get_report(report_id: int, company_id: int) -> AdvancedReport:
    return AdvancedReport.query.filter_by(id=report_id, company_id=company_id).first_or_404()
