from __future__ import annotations

import os
from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import AdvancedReport, Company, Machine, Plant, User
from app.services.export_service import export_report

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
    "name": "advanced_reports",
    "order": 490,
    "description": "Operational drill-down reports with KPI and alert analytics",
}


def _author_for(company: Company, admins: dict[int, User]) -> User | None:
    return admins.get(company.id) or User.query.filter_by(company_id=company.id).order_by(User.created_at).first()


def _seed_pdf(company_name: str, period: str, report_type: str, report_data: dict) -> str:
    title = f"{company_name} - {period} {report_type}"
    ai_summary = {
        "executive_summary": f"Seeded {report_type} snapshot for {company_name} ({period}).",
        "key_risks": ["Seed data - replace with real insights"],
        "performance_gaps": [],
        "strategic_recommendations": [],
    }
    payload = {
        "kpi_summary": report_data.get("kpi_breakdown", {}),
        "health_overview": {"avg_health": 0, "critical_machines": 0},
        "financial_projection": {
            "projected_downtime_cost": 0,
            "projected_revenue_loss": 0,
            "total_risk_exposure": 0,
        },
        "esg": {"total_energy_kwh": 0, "sustainability_score": 0, "carbon_proxy_kg": 0},
        "prediction_outlook": report_data.get("machine_comparison", []),
        "ai_summary": ai_summary,
    }
    return export_report(payload, "PDF", title, company_name)


def run():
    companies = Company.query.all()
    if not companies:
        return

    admins = {
        user.company_id: user
        for user in User.query.filter(User.role.in_(["SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN", "MANAGER"]))
    }

    period_labels = ["2026-Q1", "2026-Q2", "2026-Q3"]
    report_types = ["kpi_trend", "machine_benchmark", "plant_performance", "alert_frequency"]
    now = ANCHOR_NOW

    for company in companies:
        author = _author_for(company, admins)
        if not author:
            continue
        company_machines = Machine.query.filter_by(company_id=company.id).all()
        company_plants = Plant.query.filter_by(company_id=company.id).all()
        if not company_plants or not company_machines:
            continue

        for period_idx, period in enumerate(period_labels):
            for report_type in report_types:
                machine_slice = company_machines[: min(3, len(company_machines))]
                plant_slice = company_plants[: min(2, len(company_plants))]
                report_data = {
                    "period": period,
                    "kpi_breakdown": {
                        "oee": round(0.84 + 0.01 * period_idx, 3),
                        "availability": round(0.95 - 0.005 * period_idx, 3),
                        "performance": round(0.9 + 0.008 * period_idx, 3),
                        "quality": round(0.98 - 0.002 * period_idx, 3),
                    },
                    "machine_comparison": [
                        {
                            "machine_id": m.id,
                            "plant_id": m.plant_id,
                            "throughput_per_hour": round(58 + m.id % 7 + period_idx * 3, 1),
                            "downtime_hours": round(22 - period_idx * 2.5, 1),
                            "maintenance_compliance": round(0.9 - 0.01 * (idx % 3), 3),
                        }
                        for idx, m in enumerate(machine_slice)
                    ],
                    "plant_comparison": [
                        {
                            "plant_id": p.id,
                            "oee": round(0.86 + (idx * 0.01), 3),
                            "throughput_index": round(1.05 + idx * 0.03, 3),
                            "energy_intensity": round(0.82 - idx * 0.02, 3),
                        }
                        for idx, p in enumerate(plant_slice)
                    ],
                    "alert_frequency": {
                        "critical_last_30d": 6 + period_idx * 2,
                        "repeat_offenders": [m.id for m in machine_slice[:2]],
                        "top_types": {"vibration": 14 + period_idx, "temperature": 11 + period_idx * 2},
                    },
                    "insights": [
                        "Balance load between lines to smooth utilization.",
                        "Increase lubrication interval on spindles showing rising vibration.",
                        "Prioritize corrective actions on repeat alerting assets.",
                    ],
                }

                created_at = _clamp_dt(now - timedelta(days=20 * period_idx + company.id))
                file_path = _seed_pdf(company.company_name, period, report_type, report_data)

                existing = AdvancedReport.query.filter_by(
                    company_id=company.id,
                    report_type=report_type,
                ).first()
                if not existing:
                    db.session.add(
                        AdvancedReport(
                            company_id=company.id,
                            report_type=report_type,
                            report_data=report_data,
                            generated_by=author.id,
                            generated_at=created_at,
                            file_path=file_path,
                            format="PDF",
                        )
                    )
                else:
                    existing.report_data = report_data
                    existing.generated_by = author.id
                    existing.generated_at = _clamp_dt(existing.generated_at or created_at)
                    if not existing.file_path or not os.path.exists(existing.file_path):
                        existing.file_path = file_path
                    existing.format = "PDF"

