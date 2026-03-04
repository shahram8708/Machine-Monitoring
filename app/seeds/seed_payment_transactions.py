from datetime import date, datetime, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import Company, CompanySubscription, PaymentTransaction

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
    "name": "payment_transactions",
    "order": 210,
    "description": "Billing transactions per subscription",
}


def run():
    now = ANCHOR_NOW
    companies = {c.company_name: c for c in Company.query.all()}
    subs = {}
    for sub in CompanySubscription.query.order_by(CompanySubscription.start_date.desc()).all():
        subs.setdefault(sub.company_id, sub)

    rows = [
        {
            "company": "Aurora Precision Systems",
            "amount": Decimal("12999.00"),
            "currency": "INR",
            "billing_cycle": "monthly",
            "seats": 80,
            "status": "SUCCESS",
            "razorpay_payment_id": "pay_AUR_001",
            "razorpay_subscription_id": "sub_aurora_enterprise_001",
            "signature_verified": True,
            "created_at": _clamp_dt(now - timedelta(days=30)),
        },
        {
            "company": "Northwind Automotive Components",
            "amount": Decimal("4999.00"),
            "currency": "INR",
            "billing_cycle": "monthly",
            "seats": 25,
            "status": "SUCCESS",
            "razorpay_payment_id": "pay_NW_001",
            "razorpay_subscription_id": "sub_northwind_pro_002",
            "signature_verified": True,
            "created_at": _clamp_dt(now - timedelta(days=28)),
        },
        {
            "company": "Evergreen Food Machinery",
            "amount": Decimal("1499.00"),
            "currency": "INR",
            "billing_cycle": "monthly",
            "seats": 8,
            "status": "FAILED",
            "razorpay_payment_id": "pay_EV_001",
            "razorpay_subscription_id": "sub_evergreen_std_003",
            "signature_verified": False,
            "created_at": _clamp_dt(now - timedelta(days=45)),
            "meta": {"reason": "card_declined"},
        },
        {
            "company": "Aurora Precision Systems",
            "amount": Decimal("25998.00"),
            "currency": "INR",
            "billing_cycle": "yearly",
            "seats": 80,
            "status": "INITIATED",
            "razorpay_payment_id": None,
            "razorpay_subscription_id": "sub_aurora_enterprise_001",
            "signature_verified": False,
            "created_at": _clamp_dt(now - timedelta(days=1)),
            "meta": {"note": "renewal in progress"},
        },
    ]

    for data in rows:
        company = companies.get(data["company"])
        sub = subs.get(company.id) if company else None
        if not company:
            continue
        txn = PaymentTransaction.query.filter_by(
            company_id=company.id,
            razorpay_payment_id=data.get("razorpay_payment_id"),
            razorpay_subscription_id=data.get("razorpay_subscription_id"),
        ).first()
        payload = {
            "company_id": company.id,
            "subscription_id": sub.id if sub else None,
            "amount": data["amount"],
            "currency": data["currency"],
            "billing_cycle": data["billing_cycle"],
            "seats": data["seats"],
            "status": data["status"],
            "razorpay_payment_id": data.get("razorpay_payment_id"),
            "razorpay_subscription_id": data.get("razorpay_subscription_id"),
            "signature_verified": data.get("signature_verified", False),
            "meta": data.get("meta"),
            "created_at": data.get("created_at", now),
        }
        if not txn:
            txn = PaymentTransaction(**payload)
            db.session.add(txn)
        else:
            for field, value in payload.items():
                setattr(txn, field, value)
