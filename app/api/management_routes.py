from flask import request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_login import current_user
from app.extensions import db
from app.security import dev_show_all_data_enabled
from . import api_bp
from app.models import (
    Plant,
    Department,
    Role,
    Permission,
    RolePermission,
    UserPlantMapping,
    Company,
    User,
    Machine,
)
from app.decorators import rate_limit
from app.audit import log_action


ENTERPRISE_SCOPE_ROLES = {"SUPER_ADMIN", "ENTERPRISE_ADMIN"}
PLANT_SCOPE_ROLES = {"PLANT_MANAGER", "MAINTENANCE_HEAD", "TECHNICIAN", "VIEWER", "MANAGER"}


def _resolve_user():
    if current_user and getattr(current_user, "is_authenticated", False):
        return current_user
    identity = get_jwt_identity()
    if not identity:
        abort(401)
    try:
        identity_int = int(identity)
    except (TypeError, ValueError):
        abort(401)
    user = User.query.get(identity_int)
    if not user:
        abort(401)
    return user


def _user_role(user) -> str:
    if hasattr(user, "active_role"):
        return (user.active_role or "").upper()
    return (user.role or "").upper()


def _check_company_access(user, company_id: int):
    if dev_show_all_data_enabled():
        return True
    role = _user_role(user)
    if role == "SUPER_ADMIN":
        return True
    if user.company_id != company_id:
        abort(403)
    return True


def _check_plant_access(user, plant_id: int):
    if dev_show_all_data_enabled():
        return True
    role = _user_role(user)
    if role in ENTERPRISE_SCOPE_ROLES:
        return True
    mapping_ids = {m.plant_id for m in user.plant_mappings}
    if plant_id not in mapping_ids:
        abort(403)
    return True


@api_bp.route("/plants", methods=["GET", "POST"])
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def plants_collection():
    user = _resolve_user()
    role = _user_role(user)
    if request.method == "GET":
        query = Plant.query
        if role != "SUPER_ADMIN":
            query = query.filter_by(company_id=user.company_id)
        plants = query.order_by(Plant.created_at.desc()).all()
        return jsonify([{
            "id": p.id,
            "name": p.name,
            "plant_code": p.plant_code,
            "location": p.location,
            "company_id": p.company_id,
        } for p in plants])

    data = request.get_json() or {}
    name = data.get("name")
    plant_code = data.get("plant_code")
    location = data.get("location")
    company_id = data.get("company_id") or user.company_id
    _check_company_access(user, company_id)

    plant = Plant(name=name, plant_code=plant_code, location=location, company_id=company_id)
    db.session.add(plant)
    db.session.commit()
    log_action("plant_created", "plant", plant.id, new_value=data, company_id=company_id)
    return jsonify({"id": plant.id}), 201


@api_bp.route("/plants/<int:plant_id>", methods=["GET", "PUT", "DELETE"])
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def plant_item(plant_id: int):
    user = _resolve_user()
    plant = Plant.query.get_or_404(plant_id)
    _check_company_access(user, plant.company_id)
    _check_plant_access(user, plant.id)

    if request.method == "GET":
        return jsonify({
            "id": plant.id,
            "name": plant.name,
            "plant_code": plant.plant_code,
            "location": plant.location,
            "company_id": plant.company_id,
        })

    if request.method == "PUT":
        data = request.get_json() or {}
        old_value = {"name": plant.name, "plant_code": plant.plant_code, "location": plant.location}
        plant.name = data.get("name", plant.name)
        plant.plant_code = data.get("plant_code", plant.plant_code)
        plant.location = data.get("location", plant.location)
        db.session.commit()
        log_action("plant_updated", "plant", plant.id, old_value=old_value, new_value=data, company_id=plant.company_id)
        return jsonify({"status": "success"})

    db.session.delete(plant)
    db.session.commit()
    log_action("plant_deleted", "plant", plant.id, company_id=plant.company_id)
    return jsonify({"status": "deleted"})


@api_bp.route("/departments", methods=["GET", "POST"])
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def departments_collection():
    user = _resolve_user()
    if request.method == "GET":
        query = Department.query
        if _user_role(user) != "SUPER_ADMIN":
            query = query.join(Plant).filter(Plant.company_id == user.company_id)
        departments = query.order_by(Department.created_at.desc()).all()
        return jsonify([{
            "id": d.id,
            "name": d.name,
            "department_type": d.department_type,
            "plant_id": d.plant_id,
        } for d in departments])

    data = request.get_json() or {}
    plant_id = data.get("plant_id")
    if not plant_id:
        abort(400)
    plant = Plant.query.get_or_404(plant_id)
    _check_company_access(user, plant.company_id)
    _check_plant_access(user, plant.id)

    dept = Department(
        plant_id=plant_id,
        name=data.get("name"),
        department_type=data.get("department_type"),
    )
    db.session.add(dept)
    db.session.commit()
    log_action("department_created", "department", dept.id, new_value=data, company_id=plant.company_id, plant_id=plant.id)
    return jsonify({"id": dept.id}), 201


@api_bp.route("/departments/<int:department_id>", methods=["GET", "PUT", "DELETE"])
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def department_item(department_id: int):
    user = _resolve_user()
    dept = Department.query.get_or_404(department_id)
    plant = dept.plant
    _check_company_access(user, plant.company_id)
    _check_plant_access(user, plant.id)

    if request.method == "GET":
        return jsonify({
            "id": dept.id,
            "name": dept.name,
            "department_type": dept.department_type,
            "plant_id": dept.plant_id,
        })

    if request.method == "PUT":
        data = request.get_json() or {}
        old_value = {"name": dept.name, "department_type": dept.department_type}
        dept.name = data.get("name", dept.name)
        dept.department_type = data.get("department_type", dept.department_type)
        db.session.commit()
        log_action("department_updated", "department", dept.id, old_value=old_value, new_value=data, company_id=plant.company_id, plant_id=plant.id)
        return jsonify({"status": "success"})

    db.session.delete(dept)
    db.session.commit()
    log_action("department_deleted", "department", dept.id, company_id=plant.company_id, plant_id=plant.id)
    return jsonify({"status": "deleted"})


@api_bp.route("/machines", methods=["GET"])
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def machines_collection():
    user = _resolve_user()
    role = _user_role(user)
    query = Machine.query

    if not dev_show_all_data_enabled():
        if role == "SUPER_ADMIN":
            pass
        elif role in ENTERPRISE_SCOPE_ROLES:
            query = query.filter_by(company_id=user.company_id)
        else:
            plant_ids = [m.plant_id for m in user.plant_mappings if m.plant_id]
            if not plant_ids:
                return jsonify([])
            query = query.filter(Machine.plant_id.in_(plant_ids))

    machines = query.order_by(Machine.created_at.desc()).all()
    return jsonify([
        {
            "id": m.id,
            "machine_name": m.machine_name,
            "machine_code": m.machine_code,
            "plant_id": m.plant_id,
            "department_id": m.department_id,
            "company_id": m.company_id,
            "status": m.status,
        }
        for m in machines
    ])


@api_bp.route("/roles", methods=["GET", "POST"])
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def roles_collection():
    user = _resolve_user()
    if _user_role(user) not in ENTERPRISE_SCOPE_ROLES:
        abort(403)
    if request.method == "GET":
        roles = Role.query.order_by(Role.name.asc()).all()
        return jsonify([{"id": r.id, "name": r.name, "description": r.description} for r in roles])

    data = request.get_json() or {}
    role = Role(name=data.get("name"), description=data.get("description"))
    db.session.add(role)
    db.session.commit()
    log_action("role_created", "role", role.id, new_value=data, company_id=user.company_id)
    return jsonify({"id": role.id}), 201


@api_bp.route("/roles/<int:role_id>/permissions", methods=["PUT"])
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def update_role_permissions(role_id: int):
    user = _resolve_user()
    if _user_role(user) not in ENTERPRISE_SCOPE_ROLES:
        abort(403)
    role = Role.query.get_or_404(role_id)
    data = request.get_json() or {}
    permissions = data.get("permission_ids", [])
    RolePermission.query.filter_by(role_id=role.id).delete()
    for pid in permissions:
        db.session.add(RolePermission(role_id=role.id, permission_id=pid))
    db.session.commit()
    log_action("role_permissions_updated", "role", role.id, new_value={"permission_ids": permissions}, company_id=user.company_id)
    return jsonify({"status": "success"})


@api_bp.route("/permissions", methods=["GET", "POST"])
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def permissions_collection():
    user = _resolve_user()
    if _user_role(user) not in ENTERPRISE_SCOPE_ROLES:
        abort(403)
    if request.method == "GET":
        perms = Permission.query.order_by(Permission.module.asc()).all()
        return jsonify([
            {"id": p.id, "name": p.name, "module": p.module, "action": p.action}
            for p in perms
        ])

    data = request.get_json() or {}
    perm = Permission(name=data.get("name"), module=data.get("module"), action=data.get("action"))
    db.session.add(perm)
    db.session.commit()
    log_action("permission_created", "permission", perm.id, new_value=data, company_id=user.company_id)
    return jsonify({"id": perm.id}), 201


@api_bp.route("/user-plant-mapping", methods=["POST", "DELETE"])
@jwt_required(optional=True, locations=["headers"])
@rate_limit()
def user_plant_mapping():
    user = _resolve_user()
    if _user_role(user) not in ENTERPRISE_SCOPE_ROLES:
        abort(403)
    data = request.get_json() or {}
    target_user_id = data.get("user_id")
    plant_id = data.get("plant_id")
    role_id = data.get("role_id")
    target_user = User.query.get_or_404(target_user_id)
    plant = Plant.query.get_or_404(plant_id)
    _check_company_access(user, plant.company_id)

    if request.method == "DELETE":
        mapping = UserPlantMapping.query.filter_by(user_id=target_user_id, plant_id=plant_id).first()
        if mapping:
            db.session.delete(mapping)
            db.session.commit()
            log_action("user_plant_unmapped", "user_plant_mapping", mapping.id, company_id=plant.company_id, plant_id=plant.id)
        return jsonify({"status": "deleted"})

    mapping = UserPlantMapping(user_id=target_user_id, plant_id=plant_id, role_id=role_id)
    db.session.add(mapping)
    db.session.commit()
    log_action("user_plant_mapped", "user_plant_mapping", mapping.id, new_value=data, company_id=plant.company_id, plant_id=plant.id)
    return jsonify({"id": mapping.id}), 201
