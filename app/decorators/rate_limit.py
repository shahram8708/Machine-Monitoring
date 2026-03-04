from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from flask_login import current_user
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.extensions import db
from app.models.api_rate_limit import APIRateLimit
from config import get_config


def _get_identity() -> int | None:
    if current_user and getattr(current_user, "is_authenticated", False):
        return current_user.id
    # Only check JWT headers to avoid CSRF-related 422s when cookies are present.
    verify_jwt_in_request(optional=True, locations=["headers"])
    identity = get_jwt_identity()
    try:
        return int(identity) if identity is not None else None
    except (TypeError, ValueError):
        return None


def rate_limit(max_requests: int | None = None, window_seconds: int = 60):
    cfg = get_config()
    max_allowed = max_requests or cfg.RATE_LIMIT_REQUESTS_PER_MINUTE

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = _get_identity()
            if not user_id:
                return jsonify({"status": "error", "message": "Authentication required."}), 401

            endpoint = request.endpoint or request.path
            window_start = datetime.utcnow().replace(second=0, microsecond=0)
            existing = (
                APIRateLimit.query.filter_by(user_id=user_id, endpoint=endpoint)
                .filter(APIRateLimit.window_start >= window_start)
                .first()
            )

            if not existing:
                existing = APIRateLimit(
                    user_id=user_id,
                    endpoint=endpoint,
                    window_start=window_start,
                    request_count=0,
                )
                db.session.add(existing)

            existing.request_count += 1
            if existing.request_count > max_allowed:
                db.session.rollback()
                return jsonify({"status": "error", "message": "Rate limit exceeded"}), 429

            db.session.commit()
            return func(*args, **kwargs)

        return wrapper

    return decorator
