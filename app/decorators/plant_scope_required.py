from functools import wraps
from flask import request, abort
from flask_login import current_user
from app.security import dev_show_all_data_enabled

PLANT_SCOPED_ROLES = {"PLANT_MANAGER", "MAINTENANCE_HEAD", "TECHNICIAN", "VIEWER", "MANAGER"}


def _extract_plant_id(args, kwargs):
    if "plant_id" in kwargs:
        return kwargs.get("plant_id")
    plant_arg = request.view_args.get("plant_id") if request.view_args else None
    if plant_arg:
        return plant_arg
    plant_query = request.args.get("plant_id")
    if plant_query:
        try:
            return int(plant_query)
        except ValueError:
            return None
    json_payload = request.get_json(silent=True) or {}
    pid = json_payload.get("plant_id")
    return pid


def plant_scope_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if dev_show_all_data_enabled():
            return func(*args, **kwargs)
        if not current_user.is_authenticated:
            abort(401)

        role_name = (current_user.active_role or "").upper()
        if role_name in {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN"}:
            return func(*args, **kwargs)

        plant_id = _extract_plant_id(args, kwargs)
        if not plant_id:
            abort(400)

        mapping_ids = {m.plant_id for m in current_user.plant_mappings}
        if plant_id not in mapping_ids:
            abort(403)
        return func(*args, **kwargs)

    return wrapper
