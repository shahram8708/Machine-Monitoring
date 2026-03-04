from functools import wraps
from flask import redirect, url_for, flash, request, abort
from flask_login import current_user

ENTERPRISE_ROLES = {
    "SUPER_ADMIN",
    "ENTERPRISE_ADMIN",
    "PLANT_MANAGER",
    "MAINTENANCE_HEAD",
    "TECHNICIAN",
    "VIEWER",
    "admin",
    "manager",
    "viewer",
}


def role_required(*roles):
    allowed = {r.upper() for r in roles} if roles else ENTERPRISE_ROLES

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.url))
            current_role = (current_user.active_role or "").upper()
            if allowed and current_role not in allowed:
                flash("You are not authorized to access this resource.", "danger")
                return redirect(url_for("main.dashboard"))
            return func(*args, **kwargs)

        return wrapper

    return decorator


def manager_required(func):
    return role_required("ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN", "MANAGER", "PLANT_MANAGER")(func)


def admin_required(func):
    return role_required("ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN")(func)


def rbac_required(*roles):
    return role_required(*roles)
