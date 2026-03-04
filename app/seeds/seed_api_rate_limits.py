from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import APIRateLimit, User

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
    "name": "api_rate_limits",
    "order": 445,
    "description": "Recent API usage windows with throttling scenarios",
}


def run():
    random.seed(41)
    users = User.query.all()
    if not users:
        return

    now = ANCHOR_NOW.replace(second=0, microsecond=0)
    endpoints = [
        "/api/machines",
        "/api/machines/health",
        "/api/alerts",
        "/api/alerts/acknowledge",
        "/api/kpis",
        "/api/analytics/oee",
        "/api/reports/executive",
        "/api/workforce/tasks",
        "/api/auth/token",
        "/api/rca",
    ]

    windows: list[dict[str, object]] = []
    for user in users:
        sampled_endpoints = random.sample(endpoints, k=6)
        for idx, endpoint in enumerate(sampled_endpoints):
            window_start = _clamp_dt(now - timedelta(minutes=(idx + user.id) * 15))
            base_count = random.randint(18, 95)
            burst = random.choice([0, 0, random.randint(40, 220)])
            windows.append(
                {
                    "user": user,
                    "endpoint": endpoint,
                    "request_count": base_count + burst,
                    "window_start": window_start,
                }
            )
            if idx % 2 == 0:
                throttle_window = _clamp_dt(window_start - timedelta(minutes=15))
                windows.append(
                    {
                        "user": user,
                        "endpoint": endpoint,
                        "request_count": base_count + 250,
                        "window_start": throttle_window,
                    }
                )

    if len(windows) < 50:
        while len(windows) < 50:
            user = random.choice(users)
            endpoint = random.choice(endpoints)
            window_start = _clamp_dt(now - timedelta(minutes=len(windows)))
            windows.append(
                {
                    "user": user,
                    "endpoint": endpoint,
                    "request_count": random.randint(5, 60),
                    "window_start": window_start,
                }
            )

    for entry in windows:
        user = entry["user"]
        endpoint = entry["endpoint"]
        window_start = entry["window_start"]
        request_count = entry["request_count"]

        existing = APIRateLimit.query.filter_by(user_id=user.id, endpoint=endpoint, window_start=window_start).first()
        if existing:
            existing.request_count = request_count
        else:
            db.session.add(
                APIRateLimit(
                    user_id=user.id,
                    endpoint=endpoint,
                    request_count=request_count,
                    window_start=window_start,
                )
            )

