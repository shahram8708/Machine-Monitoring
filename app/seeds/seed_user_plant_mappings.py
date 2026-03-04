from app.extensions import db
from app.models import Plant, Role, User, UserPlantMapping

SEED_METADATA = {
    "name": "user_plant_mappings",
    "order": 170,
    "description": "User to plant role assignments",
}


def run():
    users = {u.email: u for u in User.query.all()}
    plants = {p.plant_code: p for p in Plant.query.all()}
    roles = {r.name: r for r in Role.query.all()}

    mappings = [
        ("rahul.deshpande@aurora-precision.com", "AP-PUN", "PLANT_MANAGER"),
        ("sanjay.pillai@aurora-precision.com", "AP-PUN", "MAINTENANCE_HEAD"),
        ("priya.nair@aurora-precision.com", "AP-PUN", "TECHNICIAN"),
        ("priya.nair@aurora-precision.com", "AP-MAA", "TECHNICIAN"),
        ("rina.shah@northwind-auto.com", "NW-AHD", "PLANT_MANAGER"),
        ("amit.verma@northwind-auto.com", "NW-AHD", "TECHNICIAN"),
        ("mohit.arora@evergreen-foods.com", "EV-NOI", "MANAGER"),
        ("sara.fernandes@evergreen-foods.com", "EV-NOI", "VIEWER"),
    ]

    for email, plant_code, role_name in mappings:
        user = users.get(email)
        plant = plants.get(plant_code)
        role = roles.get(role_name)
        if not all([user, plant, role]):
            continue
        mapping = UserPlantMapping.query.filter_by(user_id=user.id, plant_id=plant.id).first()
        if not mapping:
            mapping = UserPlantMapping(user_id=user.id, plant_id=plant.id, role_id=role.id)
            db.session.add(mapping)
        else:
            mapping.role_id = role.id
