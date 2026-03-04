from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import CompanySubscription, SeatAllocation, User

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
    "name": "seat_allocations",
    "order": 200,
    "description": "Seat assignments tied to subscriptions",
}


def run():
    users = {u.email: u for u in User.query.all()}
    # Choose the latest subscription per company
    subs = {}
    for sub in CompanySubscription.query.order_by(CompanySubscription.start_date.desc()).all():
        subs.setdefault(sub.company_id, sub)

    allocations = [
        ("ananya.mehra@aurora-precision.com", "ACTIVE"),
        ("rohit.kulkarni@aurora-precision.com", "ACTIVE"),
        ("maya.srinivasan@aurora-precision.com", "ACTIVE"),
        ("rahul.deshpande@aurora-precision.com", "ACTIVE"),
        ("sanjay.pillai@aurora-precision.com", "ACTIVE"),
        ("priya.nair@aurora-precision.com", "ACTIVE"),
        ("vikram.patel@northwind-auto.com", "ACTIVE"),
        ("rina.shah@northwind-auto.com", "ACTIVE"),
        ("amit.verma@northwind-auto.com", "ACTIVE"),
        ("neha.kapoor@evergreen-foods.com", "ACTIVE"),
        ("mohit.arora@evergreen-foods.com", "ACTIVE"),
        ("sara.fernandes@evergreen-foods.com", "RELEASED"),
    ]

    now = ANCHOR_NOW

    for email, status in allocations:
        user = users.get(email)
        if not user:
            continue
        sub = subs.get(user.company_id)
        if not sub:
            continue
        alloc = SeatAllocation.query.filter_by(company_id=user.company_id, user_id=user.id).first()
        if not alloc:
            alloc = SeatAllocation(
                company_id=user.company_id,
                user_id=user.id,
                subscription_id=sub.id,
                status=status,
                allocated_at=_clamp_dt(sub.start_date),
                released_at=_clamp_dt(sub.expiry_date) if status != "ACTIVE" else None,
            )
            db.session.add(alloc)
        else:
            alloc.subscription_id = sub.id
            alloc.status = status
            if status != "ACTIVE":
                alloc.released_at = _clamp_dt(alloc.released_at or sub.expiry_date or now - timedelta(days=30))
