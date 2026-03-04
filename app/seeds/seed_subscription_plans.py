from decimal import Decimal

from app.extensions import db
from app.models import SubscriptionPlan

SEED_METADATA = {
    "name": "subscription_plans",
    "order": 180,
    "description": "Subscription plan catalog",
}


def run():
    plans = [
        {
            "name": "STANDARD",
            "base_seats": 5,
            "max_plants": 1,
            "max_machines": 10,
            "ai_prediction_limit": 1000,
            "advanced_reports_enabled": False,
            "digital_twin_enabled": False,
            "workforce_analytics_enabled": False,
            "price_monthly": Decimal("1499.00"),
            "price_yearly": Decimal("14999.00"),
            "seat_price_monthly": Decimal("299.00"),
            "seat_price_yearly": Decimal("2999.00"),
        },
        {
            "name": "PROFESSIONAL",
            "base_seats": 15,
            "max_plants": 3,
            "max_machines": 50,
            "ai_prediction_limit": 5000,
            "advanced_reports_enabled": True,
            "digital_twin_enabled": True,
            "workforce_analytics_enabled": True,
            "price_monthly": Decimal("4999.00"),
            "price_yearly": Decimal("49999.00"),
            "seat_price_monthly": Decimal("499.00"),
            "seat_price_yearly": Decimal("4999.00"),
        },
        {
            "name": "ENTERPRISE",
            "base_seats": 50,
            "max_plants": 10,
            "max_machines": 200,
            "ai_prediction_limit": 20000,
            "advanced_reports_enabled": True,
            "digital_twin_enabled": True,
            "workforce_analytics_enabled": True,
            "price_monthly": Decimal("12999.00"),
            "price_yearly": Decimal("129999.00"),
            "seat_price_monthly": Decimal("699.00"),
            "seat_price_yearly": Decimal("6999.00"),
        },
    ]

    for data in plans:
        plan = SubscriptionPlan.query.filter_by(name=data["name"]).first()
        if not plan:
            plan = SubscriptionPlan(**data)
            db.session.add(plan)
        else:
            for field, value in data.items():
                setattr(plan, field, value)
