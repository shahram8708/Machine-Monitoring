from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user


def role_required(*roles):
    """Ensure the user is authenticated and has one of the allowed roles."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.url))
            if roles and current_user.role not in roles:
                flash("You are not authorized to access this resource.", "danger")
                return redirect(url_for("main.dashboard"))
            return func(*args, **kwargs)

        return wrapper

    return decorator


def manager_required(func):
    """Allow managers and admins."""
    return role_required("admin", "manager")(func)


def admin_required(func):
    """Restrict to admins only."""
    return role_required("admin")(func)
