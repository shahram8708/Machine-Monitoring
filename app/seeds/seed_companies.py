from datetime import date, datetime, timedelta

MIN_DATE = date(2026, 3, 1)
MAX_DATE = date(2026, 3, 3)
ANCHOR_NOW = datetime(2026, 3, 3, 12, 0, 0)


def _clamp_dt(value: datetime) -> datetime:
    if value.date() < MIN_DATE:
        return value.replace(year=2026, month=3, day=1)
    if value.date() > MAX_DATE:
        return value.replace(year=2026, month=3, day=3)
    return value

from app.extensions import db
from app.models import Company

SEED_METADATA = {
    "name": "companies",
    "order": 130,
    "description": "Tenant companies with subscription tiers",
}


def run():
    now = ANCHOR_NOW
    companies = [
        {
            "company_name": "Aurora Precision Systems",
            "industry_type": "Industrial Automation",
            "subscription_tier": "enterprise",
            "created_at": _clamp_dt(now - timedelta(days=320)),
        },
        {
            "company_name": "Northwind Automotive Components",
            "industry_type": "Automotive",
            "subscription_tier": "professional",
            "created_at": _clamp_dt(now - timedelta(days=260)),
        },
        {
            "company_name": "Evergreen Food Machinery",
            "industry_type": "Food Processing",
            "subscription_tier": "standard",
            "created_at": _clamp_dt(now - timedelta(days=190)),
        },
    ]

    for data in companies:
        company = Company.query.filter_by(company_name=data["company_name"]).first()
        if not company:
            company = Company(**data)
            db.session.add(company)
        else:
            company.industry_type = data["industry_type"]
            company.subscription_tier = data["subscription_tier"]
            company.created_at = company.created_at or data["created_at"]
