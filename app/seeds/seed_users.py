from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Company, Role, User

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
    "name": "users",
    "order": 160,
    "description": "Core user accounts with roles",
}


def _set_password(user: User, password: str):
    if not password:
        return
    # Always reset to ensure seed passwords stay in sync for local testing
    user.set_password(password)


def run():
    now = ANCHOR_NOW
    companies = {c.company_name: c for c in Company.query.all()}
    roles = {r.name: r for r in Role.query.all()}

    users = [
        {
            "name": "Ananya Mehra",
            "email": "ananya.mehra@aurora-precision.com",
            "company": "Aurora Precision Systems",
            "role": "SUPER_ADMIN",
            "password": "Aurora!Admin#24",
            "created_at": _clamp_dt(now - timedelta(days=310)),
        },
        {
            "name": "Rohit Kulkarni",
            "email": "rohit.kulkarni@aurora-precision.com",
            "company": "Aurora Precision Systems",
            "role": "ENTERPRISE_ADMIN",
            "password": "Aurora!Ops#24",
            "created_at": _clamp_dt(now - timedelta(days=300)),
        },
        {
            "name": "Maya Srinivasan",
            "email": "maya.srinivasan@aurora-precision.com",
            "company": "Aurora Precision Systems",
            "role": "ADMIN",
            "password": "Aurora!Admin#25",
            "created_at": _clamp_dt(now - timedelta(days=295)),
        },
        {
            "name": "Rahul Deshpande",
            "email": "rahul.deshpande@aurora-precision.com",
            "company": "Aurora Precision Systems",
            "role": "PLANT_MANAGER",
            "password": "Aurora!Plant#25",
            "created_at": _clamp_dt(now - timedelta(days=280)),
        },
        {
            "name": "Sanjay Pillai",
            "email": "sanjay.pillai@aurora-precision.com",
            "company": "Aurora Precision Systems",
            "role": "MAINTENANCE_HEAD",
            "password": "Aurora!Maint#25",
            "created_at": _clamp_dt(now - timedelta(days=270)),
        },
        {
            "name": "Priya Nair",
            "email": "priya.nair@aurora-precision.com",
            "company": "Aurora Precision Systems",
            "role": "TECHNICIAN",
            "password": "Aurora!Tech#25",
            "created_at": _clamp_dt(now - timedelta(days=265)),
        },
        {
            "name": "Vikram Patel",
            "email": "vikram.patel@northwind-auto.com",
            "company": "Northwind Automotive Components",
            "role": "ADMIN",
            "password": "Northwind!Admin#24",
            "created_at": _clamp_dt(now - timedelta(days=240)),
        },
        {
            "name": "Rina Shah",
            "email": "rina.shah@northwind-auto.com",
            "company": "Northwind Automotive Components",
            "role": "PLANT_MANAGER",
            "password": "Northwind!Plant#25",
            "created_at": _clamp_dt(now - timedelta(days=230)),
        },
        {
            "name": "Amit Verma",
            "email": "amit.verma@northwind-auto.com",
            "company": "Northwind Automotive Components",
            "role": "TECHNICIAN",
            "password": "Northwind!Tech#25",
            "created_at": _clamp_dt(now - timedelta(days=228)),
        },
        {
            "name": "Neha Kapoor",
            "email": "neha.kapoor@evergreen-foods.com",
            "company": "Evergreen Food Machinery",
            "role": "ADMIN",
            "password": "Evergreen!Admin#24",
            "created_at": _clamp_dt(now - timedelta(days=180)),
        },
        {
            "name": "Mohit Arora",
            "email": "mohit.arora@evergreen-foods.com",
            "company": "Evergreen Food Machinery",
            "role": "MANAGER",
            "password": "Evergreen!Mgr#24",
            "created_at": _clamp_dt(now - timedelta(days=175)),
        },
        {
            "name": "Sara Fernandes",
            "email": "sara.fernandes@evergreen-foods.com",
            "company": "Evergreen Food Machinery",
            "role": "VIEWER",
            "password": "Evergreen!View#24",
            "created_at": _clamp_dt(now - timedelta(days=172)),
        },
    ]

    for data in users:
        company = companies.get(data["company"])
        role = roles.get(data["role"])
        if not company or not role:
            continue
        user = User.query.filter_by(email=data["email"].lower()).first()
        if not user:
            user = User(
                name=data["name"],
                email=data["email"].lower(),
                role=data["role"],
                company_id=company.id,
                primary_role_id=role.id,
                is_active=True,
                created_at=data["created_at"],
            )
            _set_password(user, data["password"])
            db.session.add(user)
        else:
            user.name = data["name"]
            user.role = data["role"]
            user.company_id = company.id
            user.primary_role_id = role.id
            user.is_active = True
            user.created_at = user.created_at or data["created_at"]
            _set_password(user, data["password"])
