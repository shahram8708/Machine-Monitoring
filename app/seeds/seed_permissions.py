from app.extensions import db
from app.models import Permission

SEED_METADATA = {
    "name": "permissions",
    "order": 110,
    "description": "Granular permissions across modules",
}


PERMISSIONS = [
    ("machine", "view"),
    ("machine", "create"),
    ("machine", "update"),
    ("machine", "delete"),
    ("sensor", "view"),
    ("sensor", "create"),
    ("sensor", "update"),
    ("sensor", "delete"),
    ("alert", "view"),
    ("alert", "acknowledge"),
    ("alert", "resolve"),
    ("alert", "escalate"),
    ("ai", "view"),
    ("ai", "run"),
    ("kpi", "view"),
    ("kpi", "export"),
    ("twin", "view"),
    ("twin", "simulate"),
    ("twin", "whatif"),
    ("workforce", "view"),
    ("workforce", "assign"),
    ("spare_parts", "view"),
    ("spare_parts", "replenish"),
    ("spare_parts", "recommendation"),
    ("subscription", "view"),
    ("subscription", "manage"),
    ("payment", "view"),
    ("payment", "manage"),
    ("report", "view"),
    ("report", "generate"),
    ("report", "download"),
    ("user", "view"),
    ("user", "create"),
    ("user", "update"),
    ("user", "deactivate"),
    ("plant", "view"),
    ("plant", "create"),
    ("plant", "update"),
    ("plant", "delete"),
    ("department", "view"),
    ("department", "manage"),
    ("analytics", "view"),
    ("analytics", "export"),
    ("esg", "view"),
    ("financial", "view"),
    ("maintenance_task", "assign"),
    ("maintenance_task", "complete"),
]


def run():
    for module, action in PERMISSIONS:
        name = f"{module}.{action}"
        perm = Permission.query.filter_by(module=module, action=action).first()
        if not perm:
            perm = Permission(name=name, module=module, action=action)
            db.session.add(perm)
        else:
            perm.name = name
