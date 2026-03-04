from functools import wraps
from flask import jsonify
from flask_login import current_user
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.user import User
from app.services.subscription_service import feature_enabled, enforce_entity_limits


def _current_user():
    if current_user and getattr(current_user, "is_authenticated", False):
        return current_user
    verify_jwt_in_request(optional=True)
    identity = get_jwt_identity()
    if not identity:
        return None
    try:
        identity_int = int(identity)
    except (TypeError, ValueError):
        return None
    return User.query.get(identity_int)


def feature_required(feature_name: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = _current_user()
            if not user:
                return jsonify({"status": "error", "message": "Authentication required."}), 401
            if not enforce_entity_limits(user.company_id):
                return jsonify({"status": "error", "message": "Subscription limits exceeded."}), 403
            if not feature_enabled(user.company_id, feature_name):
                return jsonify({"status": "error", "message": "Feature unavailable for your plan."}), 403
            return func(*args, **kwargs)

        return wrapper

    return decorator
