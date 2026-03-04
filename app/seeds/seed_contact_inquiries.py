from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Company, ContactInquiry

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
    "name": "contact_inquiries",
    "order": 220,
    "description": "Recent sales and support inquiries",
}


def run():
    now = ANCHOR_NOW
    companies = {c.company_name: c for c in Company.query.all()}

    rows = [
        {
            "full_name": "Leena Narang",
            "organization": "Vertex Robotics",
            "email": "leena.narang@vertex-robotics.com",
            "phone": "+91-98111-23456",
            "industry": "Robotics",
            "users_needed": 120,
            "category": "Enterprise Plan",
            "message": "Need predictive maintenance rollout across three factories in FY26.",
            "company": "Aurora Precision Systems",
            "created_at": _clamp_dt(now - timedelta(days=5)),
        },
        {
            "full_name": "Arun Raman",
            "organization": "Delta Metals",
            "email": "arun.raman@deltametals.in",
            "phone": "+91-98220-44551",
            "industry": "Metals",
            "users_needed": 45,
            "category": "Custom Integration",
            "message": "Need OPC-UA gateway integration and SAP export hooks.",
            "company": "Northwind Automotive Components",
            "created_at": _clamp_dt(now - timedelta(days=12)),
        },
        {
            "full_name": "Sonal Chawla",
            "organization": "Fresh Harvest Foods",
            "email": "sonal.chawla@freshharvest.com",
            "phone": "+91-98765-11223",
            "industry": "Food & Beverage",
            "users_needed": 30,
            "category": "On-Premise Deployment",
            "message": "Assess on-prem deployment for chilled storage equipment.",
            "company": "Evergreen Food Machinery",
            "created_at": _clamp_dt(now - timedelta(days=20)),
        },
    ]

    for data in rows:
        company = companies.get(data.get("company"))
        inquiry = ContactInquiry.query.filter_by(email=data["email"], message=data["message"]).first()
        payload = {
            "full_name": data["full_name"],
            "organization": data["organization"],
            "email": data["email"],
            "phone": data.get("phone"),
            "industry": data.get("industry"),
            "users_needed": data.get("users_needed"),
            "category": data["category"],
            "message": data["message"],
            "company_id": company.id if company else None,
            "created_at": data.get("created_at", now),
        }
        if not inquiry:
            inquiry = ContactInquiry(**payload)
            db.session.add(inquiry)
        else:
            for field, value in payload.items():
                setattr(inquiry, field, value)
