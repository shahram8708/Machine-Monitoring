from app.extensions import db
from app.models import Company, EscalationRule

SEED_METADATA = {
    "name": "escalation_rules",
    "order": 360,
    "description": "SLA escalation thresholds per company",
}


def run():
    companies = {c.company_name: c for c in Company.query.all()}

    rules = [
        ("Aurora Precision Systems", "HIGH", 30, "PLANT_MANAGER"),
        ("Aurora Precision Systems", "CRITICAL", 15, "ENTERPRISE_ADMIN"),
        ("Northwind Automotive Components", "HIGH", 35, "PLANT_MANAGER"),
        ("Northwind Automotive Components", "CRITICAL", 20, "ADMIN"),
        ("Evergreen Food Machinery", "HIGH", 40, "MANAGER"),
    ]

    for company_name, severity, minutes, role in rules:
        company = companies.get(company_name)
        if not company:
            continue
        rule = EscalationRule.query.filter_by(company_id=company.id, severity=severity).first()
        if not rule:
            rule = EscalationRule(
                company_id=company.id,
                severity=severity,
                escalation_time_minutes=minutes,
                next_role_to_notify=role,
            )
            db.session.add(rule)
        else:
            rule.escalation_time_minutes = minutes
            rule.next_role_to_notify = role
