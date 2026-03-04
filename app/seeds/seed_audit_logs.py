from __future__ import annotations

import random
from datetime import date, datetime, timedelta

from app.extensions import db
from app.models import Alert, AuditLog, Company, Machine, Plant, User, UserPlantMapping

MIN_DATE = date(2026, 3, 1)
MAX_DATE = date(2026, 3, 3)
ANCHOR_NOW = datetime(2026, 3, 3, 12, 0, 0)


def _clamp_dt(value: datetime) -> datetime:
    if value.date() < MIN_DATE:
        return value.replace(year=2026, month=3, day=1)
    if value.date() > MAX_DATE:
        return value.replace(year=2026, month=3, day=3)
    return value


SEED_METADATA = {
    "name": "audit_logs",
    "order": 470,
    "description": "Authentication, configuration, and subscription audit trail",
}


def run():
    random.seed(55)
    now = ANCHOR_NOW

    users = User.query.all()
    machines = Machine.query.all()
    alerts = Alert.query.limit(80).all()
    companies = {c.id: c for c in Company.query.all()}
    plants = {p.id: p for p in Plant.query.all()}
    user_plants = {m.user_id: m.plant_id for m in UserPlantMapping.query.all()}

    if not users or not companies:
        return

    ip_pool = ["10.1.4.21", "10.1.4.37", "10.4.18.12", "172.16.5.42", "172.18.3.14", "192.168.10.55"]
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/17.0",
        "Mozilla/5.0 (X11; Linux x86_64) Firefox/120.0",
        "curl/8.4.0",
    ]

    records: list[AuditLog] = []

    for user in users:
        company_id = user.company_id
        plant_id = user_plants.get(user.id)
        for days_ago in [1, 2, 3, 5, 8, 13, 21]:
            login_time = _clamp_dt(now - timedelta(days=days_ago, hours=random.randint(0, 22), minutes=random.randint(0, 50)))
            records.append(
                AuditLog(
                    user_id=user.id,
                    company_id=company_id,
                    plant_id=plant_id,
                    action="user_login",
                    action_type="login",
                    entity_type="user",
                    entity_id=user.id,
                    old_value=None,
                    new_value={"user_agent": random.choice(user_agents)},
                    previous_value=None,
                    timestamp=login_time,
                    ip_address=random.choice(ip_pool),
                )
            )
            logout_time = _clamp_dt(login_time + timedelta(minutes=random.randint(20, 180)))
            records.append(
                AuditLog(
                    user_id=user.id,
                    company_id=company_id,
                    plant_id=plant_id,
                    action="user_logout",
                    action_type="logout",
                    entity_type="user",
                    entity_id=user.id,
                    old_value=None,
                    new_value=None,
                    previous_value=None,
                    timestamp=logout_time,
                    ip_address=random.choice(ip_pool),
                )
            )

    role_changes = [u for u in users if u.role.upper() in {"ADMIN", "PLANT_MANAGER", "MAINTENANCE_HEAD", "ENTERPRISE_ADMIN"}]
    for user in role_changes:
        new_role = "SUPER_ADMIN" if user.role.upper() == "ENTERPRISE_ADMIN" else user.role
        change_time = _clamp_dt(now - timedelta(days=random.randint(25, 90), hours=random.randint(0, 23)))
        records.append(
            AuditLog(
                user_id=user.id,
                company_id=user.company_id,
                plant_id=user_plants.get(user.id),
                action="user_role_updated",
                action_type="role_update",
                entity_type="user",
                entity_id=user.id,
                old_value={"role": user.role},
                new_value={"role": new_role},
                previous_value={"role": user.role},
                timestamp=change_time,
                ip_address=random.choice(ip_pool),
            )
        )

    for machine in machines:
        for offset in [7, 18, 34, 55]:
            ts = _clamp_dt(now - timedelta(days=offset, hours=random.randint(0, 20)))
            new_cost = float(machine.cost_per_hour or 0) * random.choice([0.98, 1.02, 1.05])
            new_state = random.choice(["ready", "maintenance", "calibrating"])
            records.append(
                AuditLog(
                    user_id=random.choice(users).id,
                    company_id=machine.company_id,
                    plant_id=machine.plant_id,
                    action="machine_configuration_updated",
                    action_type="config_change",
                    entity_type="machine",
                    entity_id=machine.id,
                    old_value={"operational_state": machine.operational_state, "cost_per_hour": float(machine.cost_per_hour or 0)},
                    new_value={"operational_state": new_state, "cost_per_hour": round(new_cost, 2)},
                    previous_value={"operational_state": machine.operational_state},
                    timestamp=ts,
                    ip_address=random.choice(ip_pool),
                )
            )

    for alert in alerts:
        company_id = alert.company_id
        plant_id = alert.plant_id or machines[0].plant_id if machines else None
        actor = random.choice(users)
        ts = _clamp_dt(now - timedelta(days=random.randint(1, 40), hours=random.randint(0, 22)))
        records.append(
            AuditLog(
                user_id=actor.id,
                company_id=company_id,
                plant_id=plant_id,
                action="alert_status_changed",
                action_type="alert_status",
                entity_type="alert",
                entity_id=alert.id,
                old_value={"status": alert.status},
                new_value={"status": random.choice(["ACKNOWLEDGED", "RESOLVED", "ESCALATED"]), "severity": alert.severity},
                previous_value={"status": alert.status},
                timestamp=ts,
                ip_address=random.choice(ip_pool),
            )
        )

    for company in companies.values():
        tier = company.subscription_tier
        upgrade_time = _clamp_dt(now - timedelta(days=random.randint(60, 180), hours=random.randint(1, 8)))
        records.append(
            AuditLog(
                user_id=random.choice(users).id,
                company_id=company.id,
                plant_id=None,
                action="subscription_upgraded",
                action_type="subscription",
                entity_type="subscription",
                entity_id=company.id,
                old_value={"tier": tier},
                new_value={"tier": random.choice(["professional", "enterprise"]), "seats": random.randint(50, 150)},
                previous_value={"tier": tier},
                timestamp=upgrade_time,
                ip_address=random.choice(ip_pool),
            )
        )

    for plant in plants.values():
        ts = _clamp_dt(now - timedelta(days=random.randint(20, 120)))
        records.append(
            AuditLog(
                user_id=random.choice(users).id,
                company_id=plant.company_id,
                plant_id=plant.id,
                action="plant_configuration_changed",
                action_type="plant_update",
                entity_type="plant",
                entity_id=plant.id,
                old_value={"operational_status": plant.operational_status},
                new_value={"operational_status": random.choice(["operational", "maintenance", "ramp-up"])},
                previous_value={"operational_status": plant.operational_status},
                timestamp=ts,
                ip_address=random.choice(ip_pool),
            )
        )

    while len(records) < 220:
        actor = random.choice(users)
        plant_id = user_plants.get(actor.id)
        ts = _clamp_dt(now - timedelta(days=random.randint(2, 75), hours=random.randint(0, 23)))
        records.append(
            AuditLog(
                user_id=actor.id,
                company_id=actor.company_id,
                plant_id=plant_id,
                action="policy_updated",
                action_type="policy_change",
                entity_type="security_policy",
                entity_id=actor.company_id,
                old_value={"mfa": True, "password_rotation_days": 90},
                new_value={"mfa": True, "password_rotation_days": 60},
                previous_value={"password_rotation_days": 90},
                timestamp=ts,
                ip_address=random.choice(ip_pool),
            )
        )

    for record in records:
        db.session.add(record)

