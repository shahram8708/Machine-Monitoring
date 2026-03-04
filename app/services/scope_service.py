from flask_login import current_user
from flask_jwt_extended import get_jwt_identity
from app.models import User
from app.security import dev_show_all_data_enabled


def get_request_user() -> User | None:
    if current_user and getattr(current_user, "is_authenticated", False):
        return current_user
    identity = get_jwt_identity()
    if identity:
        try:
            identity_int = int(identity)
        except (TypeError, ValueError):
            return None
        return User.query.get(identity_int)
    return None


def enforce_company_scope(query, company_id: int | None = None):
    user = get_request_user()
    if dev_show_all_data_enabled():
        return query
    if not user:
        return query.filter(False)  # empty
    target_company = company_id or user.company_id
    if (user.active_role or user.role).upper() == "SUPER_ADMIN":
        return query
    return query.filter_by(company_id=target_company)


def enforce_plant_scope(query, plant_id: int | None = None):
    user = get_request_user()
    if dev_show_all_data_enabled():
        return query
    if not user:
        return query.filter(False)
    role = (user.active_role or user.role or "").upper()
    if role in {"SUPER_ADMIN", "ENTERPRISE_ADMIN"}:
        return query
    mapping_ids = {m.plant_id for m in user.plant_mappings}
    if plant_id and plant_id not in mapping_ids:
        return query.filter(False)
    return query.filter(query._primary_entity.entity.class_.plant_id.in_(mapping_ids))
