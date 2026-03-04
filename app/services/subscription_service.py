from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy import func
from app.extensions import db
from app.models.subscription import SubscriptionPlan, CompanySubscription
from app.models.plant import Plant
from app.models.machine import Machine
from app.models.user import User


DEFAULT_PLANS = (
    {
        "name": "PRO",
        "base_seats": 5,
        "max_plants": 5,
        "max_machines": 50,
        "ai_prediction_limit": 2000,
        "advanced_reports_enabled": True,
        "digital_twin_enabled": True,
        "workforce_analytics_enabled": True,
        "price_monthly": 1499,
        "price_yearly": 14999,
        "seat_price_monthly": 299,
        "seat_price_yearly": 2999,
    },
    {
        "name": "ENTERPRISE",
        "base_seats": 20,
        "max_plants": 200,
        "max_machines": 2000,
        "ai_prediction_limit": 20000,
        "advanced_reports_enabled": True,
        "digital_twin_enabled": True,
        "workforce_analytics_enabled": True,
        "price_monthly": 0,
        "price_yearly": 0,
        "seat_price_monthly": 0,
        "seat_price_yearly": 0,
    },
)

FEATURE_FLAG_MAP = {
    "advanced_reports": "advanced_reports_enabled",
    "digital_twin": "digital_twin_enabled",
    "workforce_analytics": "workforce_analytics_enabled",
}

FREE_USER_LIMIT = 5


def ensure_default_plans() -> None:
    for payload in DEFAULT_PLANS:
        plan = SubscriptionPlan.query.filter_by(name=payload["name"]).first()
        if plan:
            continue
        plan = SubscriptionPlan(**payload)
        db.session.add(plan)
    db.session.commit()


def get_plan_by_name(name: str) -> Optional[SubscriptionPlan]:
    return SubscriptionPlan.query.filter(func.lower(SubscriptionPlan.name) == name.lower()).first()


def get_active_subscription(company_id: int) -> Optional[CompanySubscription]:
    sub = (
        CompanySubscription.query.filter_by(company_id=company_id)
        .order_by(CompanySubscription.start_date.desc())
        .first()
    )
    if sub and sub.is_active:
        return sub
    return None


def get_latest_subscription(company_id: int) -> Optional[CompanySubscription]:
    return (
        CompanySubscription.query.filter_by(company_id=company_id)
        .order_by(CompanySubscription.start_date.desc())
        .first()
    )


def start_subscription(company_id: int, plan_name: str, duration_months: int = 1, razorpay_subscription_id: str | None = None, seats: int | None = None, billing_cycle: str = "monthly") -> CompanySubscription:
    plan = get_plan_by_name(plan_name)
    if not plan:
        raise ValueError("Unknown subscription plan")
    sub = CompanySubscription(
        company_id=company_id,
        plan_id=plan.id,
        razorpay_subscription_id=razorpay_subscription_id,
        billing_cycle=billing_cycle,
    )
    sub.purchased_seats = max(plan.base_seats, seats or plan.base_seats)
    sub.active_seats = 0
    sub.activate(months=duration_months, seats=sub.purchased_seats, billing_cycle=billing_cycle)
    db.session.add(sub)
    db.session.commit()
    return sub


def update_subscription_status(subscription_id: int, status: str) -> None:
    sub = CompanySubscription.query.get(subscription_id)
    if not sub:
        return
    sub.status = status.upper()
    db.session.commit()


def feature_enabled(company_id: int, feature_name: str) -> bool:
    sub = get_active_subscription(company_id)
    if not sub or not sub.plan:
        return False
    field = FEATURE_FLAG_MAP.get(feature_name)
    if not field:
        return False
    return bool(getattr(sub.plan, field, False))


def enforce_entity_limits(company_id: int) -> bool:
    sub = get_active_subscription(company_id)
    if not sub or not sub.plan:
        return False
    plant_count = Plant.query.filter_by(company_id=company_id).count()
    machine_count = Machine.query.filter_by(company_id=company_id).count()
    if plant_count > sub.plan.max_plants or machine_count > sub.plan.max_machines:
        return False
    return True


def compute_seat_limit(company_id: int) -> Tuple[int, Optional[CompanySubscription]]:
    sub = get_latest_subscription(company_id)
    if sub and sub.purchased_seats:
        return max(sub.purchased_seats, sub.plan.base_seats if sub.plan else FREE_USER_LIMIT), sub
    return FREE_USER_LIMIT, None


def check_seat_available(company_id: int, seats_needed: int = 1) -> bool:
    limit, _ = compute_seat_limit(company_id)
    active_users = User.query.filter_by(company_id=company_id, is_active=True).count()
    return active_users + seats_needed <= limit


def increment_active_seats(subscription: CompanySubscription, delta: int) -> None:
    subscription.active_seats = max(0, (subscription.active_seats or 0) + delta)
    db.session.add(subscription)
    db.session.commit()
