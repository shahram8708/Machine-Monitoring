from __future__ import annotations

from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Company, ExecutiveReport, User

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
    "name": "executive_reports",
    "order": 480,
    "description": "Quarterly executive summaries with financial and operational highlights",
}


def _find_author(company: Company, admins: dict[int, User]) -> User | None:
    return admins.get(company.id) or User.query.filter_by(company_id=company.id).order_by(User.created_at).first()


def run():
    companies = Company.query.all()
    if not companies:
        return

    admins = {
        user.company_id: user
        for user in User.query.filter(User.role.in_(["SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN", "MANAGER"]))
    }

    now = ANCHOR_NOW
    periods = ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4"]

    for company in companies:
        author = _find_author(company, admins)
        if not author:
            continue
        for idx, period in enumerate(periods):
            created_at = _clamp_dt(now - timedelta(days=(idx * 65) + company.id))
            revenue_mn = round(42 + (company.id * 3) + idx * 1.8, 2)
            downtime_hours = round(120 - (idx * 9) - company.id * 1.2, 1)
            efficiency = round(0.84 + 0.01 * idx, 3)
            path_slug = company.company_name.lower().replace(" ", "-")
            report_path = f"reports/executive/{path_slug}/{period}.pdf"
            summary_json = {
                "period": period,
                "revenue_mn": revenue_mn,
                "downtime_hours": max(18.0, downtime_hours),
                "efficiency_trend": {"oee": efficiency, "throughput_index": round(1.02 + 0.02 * idx, 3)},
                "ai_insights": f"Predictive models flagged {4 + idx} early interventions reducing unplanned downtime by {round(6.5 + idx, 1)} hours.",
                "actions": [
                    "Scale predictive maintenance to remaining lines",
                    "Tighten SLA for critical suppliers",
                    "Expand energy monitoring to utilities",
                ],
            }

            existing = ExecutiveReport.query.filter_by(company_id=company.id, report_path=report_path).first()
            if not existing:
                db.session.add(
                    ExecutiveReport(
                        company_id=company.id,
                        user_id=author.id,
                        report_path=report_path,
                        summary_json=summary_json,
                        created_at=created_at,
                    )
                )
            else:
                existing.summary_json = summary_json
                existing.user_id = author.id
                existing.created_at = _clamp_dt(existing.created_at or created_at)

