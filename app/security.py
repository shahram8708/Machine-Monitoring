from __future__ import annotations

from flask import session
from flask_login import current_user
from app.models.company import Company


def get_active_company_id() -> int | None:
    if not current_user.is_authenticated:
        return None

    if current_user.is_admin:
        active_id = session.get("active_company_id")
        if active_id:
            company = Company.query.get(active_id)
            if company:
                return company.id
    return current_user.company_id


def set_active_company(company_id: int) -> None:
    if not current_user.is_authenticated or not current_user.is_admin:
        return
    company = Company.query.get(company_id)
    if not company:
        return
    session["active_company_id"] = company.id


def clear_active_company() -> None:
    session.pop("active_company_id", None)
