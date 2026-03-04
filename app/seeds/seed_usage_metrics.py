from datetime import date, timedelta

MIN_DATE = date(2026, 3, 1)
MAX_DATE = date(2026, 3, 3)


def _clamp_date(value: date) -> date:
    if value < MIN_DATE:
        return MIN_DATE
    if value > MAX_DATE:
        return MAX_DATE
    return value

from app.extensions import db
from app.models import Company, UsageMetric

SEED_METADATA = {
    "name": "usage_metrics",
    "order": 230,
    "description": "Daily product usage counters",
}


def run():
    companies = {c.company_name: c for c in Company.query.all()}
    today = MAX_DATE
    metrics = [
        ("Aurora Precision Systems", "api_calls", [1800, 1920, 2050, 1985, 2105]),
        ("Aurora Precision Systems", "prediction_runs", [420, 415, 438, 455, 462]),
        ("Northwind Automotive Components", "api_calls", [980, 1040, 1125, 1090, 1175]),
        ("Northwind Automotive Components", "downtime_reports", [8, 6, 7, 5, 4]),
        ("Evergreen Food Machinery", "api_calls", [520, 540, 565, 580, 0]),
        ("Evergreen Food Machinery", "report_downloads", [6, 5, 4, 3, 0]),
    ]

    for company_name, metric_type, values in metrics:
        company = companies.get(company_name)
        if not company:
            continue
        for offset, count in enumerate(reversed(values)):
            metric_date = _clamp_date(today - timedelta(days=offset))
            row = UsageMetric.query.filter_by(company_id=company.id, metric_type=metric_type, date=metric_date).first()
            if not row:
                row = UsageMetric(company_id=company.id, metric_type=metric_type, date=metric_date, count=count)
                db.session.add(row)
            else:
                row.count = count
