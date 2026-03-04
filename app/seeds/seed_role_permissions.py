from app.extensions import db
from app.models import Role, Permission, RolePermission

SEED_METADATA = {
    "name": "role_permissions",
    "order": 120,
    "description": "Role to permission mapping",
}


ROLE_PERMISSIONS = {
    "ADMIN": {
        "machine.view",
        "machine.create",
        "machine.update",
        "machine.delete",
        "sensor.view",
        "sensor.create",
        "sensor.update",
        "sensor.delete",
        "alert.view",
        "alert.acknowledge",
        "alert.resolve",
        "alert.escalate",
        "ai.view",
        "ai.run",
        "kpi.view",
        "kpi.export",
        "twin.view",
        "twin.simulate",
        "twin.whatif",
        "workforce.view",
        "workforce.assign",
        "spare_parts.view",
        "spare_parts.replenish",
        "spare_parts.recommendation",
        "subscription.view",
        "subscription.manage",
        "payment.view",
        "payment.manage",
        "report.view",
        "report.generate",
        "report.download",
        "user.view",
        "user.create",
        "user.update",
        "user.deactivate",
        "plant.view",
        "plant.create",
        "plant.update",
        "plant.delete",
        "department.view",
        "department.manage",
        "analytics.view",
        "analytics.export",
        "esg.view",
        "financial.view",
        "maintenance_task.assign",
        "maintenance_task.complete",
    },
    "MANAGER": {
        "machine.view",
        "machine.update",
        "sensor.view",
        "alert.view",
        "alert.acknowledge",
        "ai.view",
        "ai.run",
        "kpi.view",
        "kpi.export",
        "twin.view",
        "workforce.view",
        "spare_parts.view",
        "spare_parts.recommendation",
        "subscription.view",
        "payment.view",
        "report.view",
        "report.generate",
        "report.download",
        "analytics.view",
        "analytics.export",
        "esg.view",
        "financial.view",
        "maintenance_task.assign",
    },
    "PLANT_MANAGER": {
        "machine.view",
        "machine.update",
        "sensor.view",
        "alert.view",
        "alert.acknowledge",
        "alert.resolve",
        "ai.view",
        "kpi.view",
        "twin.view",
        "workforce.view",
        "spare_parts.view",
        "spare_parts.recommendation",
        "report.view",
        "report.generate",
        "analytics.view",
        "esg.view",
        "financial.view",
        "maintenance_task.assign",
    },
    "MAINTENANCE_HEAD": {
        "machine.view",
        "machine.update",
        "sensor.view",
        "sensor.update",
        "alert.view",
        "alert.acknowledge",
        "alert.resolve",
        "ai.view",
        "kpi.view",
        "twin.view",
        "workforce.view",
        "spare_parts.view",
        "spare_parts.replenish",
        "report.view",
        "analytics.view",
        "maintenance_task.assign",
        "maintenance_task.complete",
    },
    "TECHNICIAN": {
        "machine.view",
        "sensor.view",
        "alert.view",
        "alert.acknowledge",
        "ai.view",
        "kpi.view",
        "twin.view",
        "workforce.view",
        "spare_parts.view",
        "report.view",
        "maintenance_task.complete",
    },
    "VIEWER": {
        "machine.view",
        "sensor.view",
        "alert.view",
        "ai.view",
        "kpi.view",
        "report.view",
        "analytics.view",
    },
}


def run():
    roles = {r.name: r for r in Role.query.all()}
    perms = {p.name: p for p in Permission.query.all()}

    # Expand enterprise roles to all permissions
    all_perm_names = set(perms.keys())
    ROLE_PERMISSIONS.setdefault("SUPER_ADMIN", all_perm_names)
    ROLE_PERMISSIONS.setdefault("ENTERPRISE_ADMIN", all_perm_names)

    for role_name, perm_names in ROLE_PERMISSIONS.items():
        role = roles.get(role_name)
        if not role:
            continue
        for perm_name in perm_names:
            perm = perms.get(perm_name)
            if not perm:
                continue
            exists = RolePermission.query.filter_by(role_id=role.id, permission_id=perm.id).first()
            if not exists:
                db.session.add(RolePermission(role_id=role.id, permission_id=perm.id))
