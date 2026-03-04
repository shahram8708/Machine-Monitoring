from __future__ import annotations

import random
from datetime import date, datetime, timedelta

MIN_DATE = date(2026, 3, 1)
MAX_DATE = date(2026, 3, 3)
ANCHOR_NOW = datetime(2026, 3, 3, 12, 0, 0)


def _clamp_dt(value: datetime) -> datetime:
    if value.date() < MIN_DATE:
        return value.replace(year=2026, month=3, day=1)
    if value.date() > MAX_DATE:
        return value.replace(year=2026, month=3, day=3)
    return value

from app.extensions import db
from app.models import MaintenanceTask, Machine, Plant, Role, User, UserPlantMapping

SEED_METADATA = {
    "name": "maintenance_tasks",
    "order": 450,
    "description": "Work orders across plants with mixed statuses",
}


def _set_password(user: User, password: str):
    if not password:
        return
    if not user.password_hash or not user.check_password(password):
        user.set_password(password)


def run():
    random.seed(42)
    now = ANCHOR_NOW

    tech_role = Role.query.filter_by(name="TECHNICIAN").first()
    plants = {p.plant_code: p for p in Plant.query.all()}
    machines_by_plant = {}
    for machine in Machine.query.all():
        machines_by_plant.setdefault(machine.plant_id, []).append(machine)

    if not tech_role or not plants or not machines_by_plant:
        return

    technician_specs = [
        {"name": "Priya Nair", "email": "priya.nair@aurora-precision.com", "plant_code": "AP-PUN", "tenure_days": 265, "skills": "vibration, lubrication"},
        {"name": "Amit Verma", "email": "amit.verma@northwind-auto.com", "plant_code": "NW-AHD", "tenure_days": 228, "skills": "hydraulics, pneumatics"},
        {"name": "Sahil Menon", "email": "sahil.menon@aurora-precision.com", "plant_code": "AP-PUN", "tenure_days": 180, "skills": "servo tuning, controls"},
        {"name": "Nisha Kulkarni", "email": "nisha.kulkarni@aurora-precision.com", "plant_code": "AP-PUN", "tenure_days": 150, "skills": "coolant, fixture"},
        {"name": "Karan Iyer", "email": "karan.iyer@aurora-precision.com", "plant_code": "AP-PUN", "tenure_days": 120, "skills": "alignment, spindle"},
        {"name": "Deepika Rao", "email": "deepika.rao@aurora-precision.com", "plant_code": "AP-MAA", "tenure_days": 140, "skills": "laser calibration, tooling"},
        {"name": "Gaurav Shetty", "email": "gaurav.shetty@aurora-precision.com", "plant_code": "AP-MAA", "tenure_days": 160, "skills": "PLC, drives"},
        {"name": "Aditya Bhagat", "email": "aditya.bhagat@aurora-precision.com", "plant_code": "AP-MAA", "tenure_days": 110, "skills": "robotics, motion"},
        {"name": "Ritika Joshi", "email": "ritika.joshi@aurora-precision.com", "plant_code": "AP-MAA", "tenure_days": 95, "skills": "coolant, spindle"},
        {"name": "Mehul Shah", "email": "mehul.shah@aurora-precision.com", "plant_code": "AP-MAA", "tenure_days": 130, "skills": "feeds, speeds"},
        {"name": "Sneha Bhat", "email": "sneha.bhat@northwind-auto.com", "plant_code": "NW-AHD", "tenure_days": 170, "skills": "press safety, hydraulics"},
        {"name": "Yashwant Giri", "email": "yashwant.giri@northwind-auto.com", "plant_code": "NW-AHD", "tenure_days": 155, "skills": "die setup, lubrication"},
        {"name": "Bhavna Sethi", "email": "bhavna.sethi@northwind-auto.com", "plant_code": "NW-AHD", "tenure_days": 125, "skills": "controls, pneumatics"},
        {"name": "Harish Pal", "email": "harish.pal@northwind-auto.com", "plant_code": "NW-AHD", "tenure_days": 115, "skills": "electrical, sensors"},
        {"name": "Naveen Reddy", "email": "naveen.reddy@northwind-auto.com", "plant_code": "NW-AHD", "tenure_days": 105, "skills": "welding, fixtures"},
        {"name": "Leena Fernandes", "email": "leena.fernandes@evergreen-foods.com", "plant_code": "EV-NOI", "tenure_days": 150, "skills": "packaging, sealing"},
        {"name": "Varun Mehta", "email": "varun.mehta@evergreen-foods.com", "plant_code": "EV-NOI", "tenure_days": 135, "skills": "conveyors, pneumatics"},
        {"name": "Anita Das", "email": "anita.das@evergreen-foods.com", "plant_code": "EV-NOI", "tenure_days": 125, "skills": "clean-in-place, sensors"},
        {"name": "Prakash Jha", "email": "prakash.jha@evergreen-foods.com", "plant_code": "EV-NOI", "tenure_days": 115, "skills": "motors, drives"},
        {"name": "Farhan Ali", "email": "farhan.ali@evergreen-foods.com", "plant_code": "EV-NOI", "tenure_days": 100, "skills": "vision, labeling"},
        {"name": "Ira Khanna", "email": "ira.khanna@aurora-precision.com", "plant_code": "AP-PUN", "tenure_days": 90, "skills": "cooling, pneumatics"},
        {"name": "Vivek Ram", "email": "vivek.ram@aurora-precision.com", "plant_code": "AP-PUN", "tenure_days": 85, "skills": "tooling, balancing"},
    ]

    technicians: list[tuple[User, Plant]] = []
    tech_skills: dict[int, str] = {}
    for spec in technician_specs:
        plant = plants.get(spec["plant_code"])
        if not plant:
            continue
        user = User.query.filter_by(email=spec["email"].lower()).first()
        created_at = _clamp_dt(now - timedelta(days=spec["tenure_days"]))
        if not user:
            user = User(
                name=spec["name"],
                email=spec["email"].lower(),
                role="TECHNICIAN",
                company_id=plant.company_id,
                primary_role_id=tech_role.id,
                is_active=True,
                created_at=created_at,
            )
            _set_password(user, "Maint!Tech#25")
            db.session.add(user)
        else:
            user.role = "TECHNICIAN"
            user.company_id = plant.company_id
            user.primary_role_id = tech_role.id
            user.is_active = True
            user.created_at = user.created_at or created_at
            _set_password(user, "Maint!Tech#25")
        db.session.flush()

        mapping = UserPlantMapping.query.filter_by(user_id=user.id, plant_id=plant.id).first()
        if not mapping:
            db.session.add(UserPlantMapping(user_id=user.id, plant_id=plant.id, role_id=tech_role.id))

        technicians.append((user, plant))
        tech_skills[user.id] = spec["skills"]

    db.session.flush()

    task_types = [
        ("Preventive", "low"),
        ("Corrective", "medium"),
        ("Corrective", "high"),
        ("Emergency", "critical"),
    ]
    status_choices = ["pending", "in_progress", "completed", "overdue"]

    total_tasks = 0
    for _ in range(165):
        tech, plant = random.choice(technicians)
        plant_machines = machines_by_plant.get(plant.id, [])
        if not plant_machines:
            continue
        machine = random.choice(plant_machines)
        task_type, priority = random.choice(task_types)

        assigned_at = _clamp_dt(now - timedelta(days=random.randint(2, 120), hours=random.randint(0, 22)))
        status = random.choices(status_choices, weights=[0.25, 0.25, 0.4, 0.1])[0]
        sla_minutes = random.choice([240, 360, 480, 720])
        completed_at = None

        if status in {"completed", "overdue"}:
            duration_minutes = random.randint(int(sla_minutes * 0.5), int(sla_minutes * 1.8))
            completed_at = _clamp_dt(assigned_at + timedelta(minutes=duration_minutes))
            delay_minutes = duration_minutes - sla_minutes
            if status == "completed":
                delay_minutes = max(-45, delay_minutes)
            else:
                delay_minutes = max(30, delay_minutes)
        elif status == "in_progress":
            duration_minutes = random.randint(int(sla_minutes * 0.3), int(sla_minutes * 1.1))
            completed_at = None
            delay_minutes = duration_minutes - sla_minutes if duration_minutes > sla_minutes else 0
        else:
            delay_minutes = random.randint(0, 180)

        skill_tags = f"type:{task_type},skills:{tech_skills.get(tech.id, task_type.lower())},core:{random.choice(['mechanical','electrical','automation','process'])},tech:{tech.email.split('@')[0]}"

        task = MaintenanceTask(
            machine_id=machine.id,
            assigned_to=tech.id,
            assigned_at=assigned_at,
            completed_at=completed_at,
            status=status,
            priority=priority,
            delay_minutes=delay_minutes,
            sla_minutes=sla_minutes,
            skill_tags=skill_tags,
        )
        db.session.add(task)
        total_tasks += 1

    if total_tasks < 150:
        needed = 150 - total_tasks
        all_machines = [machine for machine_list in machines_by_plant.values() for machine in machine_list]
        fallback_machine = all_machines[0] if all_machines else None
        for i in range(needed):
            tech, plant = random.choice(technicians)
            machine = fallback_machine or (machines_by_plant.get(plant.id, [None])[0] if machines_by_plant.get(plant.id) else None)
            if not machine:
                continue
            assigned_at = _clamp_dt(now - timedelta(days=10 + i, hours=i % 5))
            db.session.add(
                MaintenanceTask(
                    machine_id=machine.id,
                    assigned_to=tech.id,
                    assigned_at=assigned_at,
                    completed_at=None,
                    status="pending",
                    priority="medium",
                    delay_minutes=60,
                    sla_minutes=360,
                    skill_tags=f"type:Preventive,skills:general,tech:{tech.email.split('@')[0]}",
                )
            )

