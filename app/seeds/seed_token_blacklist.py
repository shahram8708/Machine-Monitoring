from __future__ import annotations

from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import TokenBlacklist, User

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
    "name": "token_blacklist",
    "order": 440,
    "description": "Revoked and expired JWT tokens",
}


def run():
    users = User.query.all()
    if not users:
        return

    now = ANCHOR_NOW
    tokens: list[dict[str, object]] = []

    for user in users:
        tokens.extend(
            [
                {
                    "user": user,
                    "jti": f"{user.id:04d}-session-expired",
                    "revoked_at": _clamp_dt(now - timedelta(days=35, hours=user.id % 5)),
                },
                {
                    "user": user,
                    "jti": f"{user.id:04d}-password-rotation",
                    "revoked_at": _clamp_dt(now - timedelta(days=15, minutes=user.id % 30)),
                },
                {
                    "user": user,
                    "jti": f"{user.id:04d}-device-revoked",
                    "revoked_at": _clamp_dt(now - timedelta(days=3, hours=user.id % 7)),
                },
            ]
        )

    idx = 0
    while len(tokens) < 30:
        user = users[idx % len(users)]
        tokens.append(
            {
                "user": user,
                "jti": f"{user.id:04d}-anomaly-{idx:03d}",
                "revoked_at": _clamp_dt(now - timedelta(hours=12 + idx)),
            }
        )
        idx += 1

    for entry in tokens:
        jti = str(entry["jti"])[:64]
        revoked_at = entry["revoked_at"]
        user = entry["user"]
        existing = TokenBlacklist.query.filter_by(token_jti=jti).first()
        if existing:
            existing.revoked_at = revoked_at
            existing.user_id = user.id
        else:
            db.session.add(TokenBlacklist(token_jti=jti, user_id=user.id, revoked_at=revoked_at))

