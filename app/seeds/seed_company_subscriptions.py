from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Company, CompanySubscription, SubscriptionPlan

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
    "name": "company_subscriptions",
    "order": 190,
    "description": "Company subscription state",
}


def run():
    now = ANCHOR_NOW
    companies = {c.company_name: c for c in Company.query.all()}
    plans = {p.name: p for p in SubscriptionPlan.query.all()}

    rows = [
        {
            "company": "Aurora Precision Systems",
            "plan": "ENTERPRISE",
            "start_date": _clamp_dt(now - timedelta(days=90)),
            "end_date": _clamp_dt(now + timedelta(days=270)),
            "expiry_date": _clamp_dt(now + timedelta(days=270)),
            "status": "ACTIVE",
            "billing_cycle": "yearly",
            "purchased_seats": 80,
            "active_seats": 65,
            "razorpay_subscription_id": "sub_aurora_enterprise_001",
        },
        {
            "company": "Northwind Automotive Components",
            "plan": "PROFESSIONAL",
            "start_date": _clamp_dt(now - timedelta(days=120)),
            "end_date": _clamp_dt(now + timedelta(days=60)),
            "expiry_date": _clamp_dt(now + timedelta(days=60)),
            "status": "ACTIVE",
            "billing_cycle": "monthly",
            "purchased_seats": 25,
            "active_seats": 18,
            "razorpay_subscription_id": "sub_northwind_pro_002",
        },
        {
            "company": "Evergreen Food Machinery",
            "plan": "STANDARD",
            "start_date": _clamp_dt(now - timedelta(days=400)),
            "end_date": _clamp_dt(now - timedelta(days=30)),
            "expiry_date": _clamp_dt(now - timedelta(days=30)),
            "status": "EXPIRED",
            "billing_cycle": "monthly",
            "purchased_seats": 8,
            "active_seats": 5,
            "razorpay_subscription_id": "sub_evergreen_std_003",
        },
    ]

    for data in rows:
        company = companies.get(data["company"])
        plan = plans.get(data["plan"])
        if not company or not plan:
            continue
        sub = CompanySubscription.query.filter_by(company_id=company.id, plan_id=plan.id).order_by(CompanySubscription.start_date.desc()).first()
        payload = {
            "company_id": company.id,
            "plan_id": plan.id,
            "start_date": data["start_date"],
            "end_date": data["end_date"],
            "expiry_date": data["expiry_date"],
            "status": data["status"],
            "billing_cycle": data["billing_cycle"],
            "purchased_seats": data["purchased_seats"],
            "active_seats": data["active_seats"],
            "razorpay_subscription_id": data["razorpay_subscription_id"],
        }
        if not sub:
            sub = CompanySubscription(**payload)
            db.session.add(sub)
        else:
            for field, value in payload.items():
                setattr(sub, field, value)
