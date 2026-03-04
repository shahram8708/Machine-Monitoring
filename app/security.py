from __future__ import annotations

from flask import session, current_app
from flask_login import current_user
from app.models.company import Company


def dev_show_all_data_enabled() -> bool:
    try:
        return current_app.config.get("DEV_SHOW_ALL_USERS_DATA", False)
    except Exception:
        return False


def get_active_company_id() -> int | None:
    # current_user may be a LocalProxy that resolves to None outside a request (e.g., background tasks)
    user = getattr(current_user, "_get_current_object", lambda: None)()
    if not user or not getattr(user, "is_authenticated", False):
        return None

    if getattr(user, "is_admin", False):
        active_id = session.get("active_company_id")
        if active_id:
            company = Company.query.get(active_id)
            if company:
                return company.id
    return getattr(user, "company_id", None)


def set_active_company(company_id: int) -> None:
    user = getattr(current_user, "_get_current_object", lambda: None)()
    if not user or not getattr(user, "is_authenticated", False) or not getattr(user, "is_admin", False):
        return
    company = Company.query.get(company_id)
    if not company:
        return
    session["active_company_id"] = company.id


def clear_active_company() -> None:
    session.pop("active_company_id", None)
