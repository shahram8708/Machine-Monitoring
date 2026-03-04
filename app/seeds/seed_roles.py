from app.extensions import db
from app.models import Role

SEED_METADATA = {
    "name": "roles",
    "order": 100,
    "description": "Base role catalog for access control",
}


def run():
    roles = [
        {"name": "SUPER_ADMIN", "description": "Platform superuser with enterprise scope"},
        {"name": "ENTERPRISE_ADMIN", "description": "Enterprise admin for multi-plant governance"},
        {"name": "ADMIN", "description": "Company administrator"},
        {"name": "MANAGER", "description": "Operations manager"},
        {"name": "PLANT_MANAGER", "description": "Plant-level manager"},
        {"name": "MAINTENANCE_HEAD", "description": "Heads maintenance teams"},
        {"name": "TECHNICIAN", "description": "Technician handling work orders"},
        {"name": "VIEWER", "description": "Read-only viewer"},
    ]

    for data in roles:
        role = Role.query.filter_by(name=data["name"]).first()
        if not role:
            role = Role(**data)
            db.session.add(role)
        else:
            role.description = data.get("description", role.description)
