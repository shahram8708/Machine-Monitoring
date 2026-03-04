from app.extensions import db
from app.models import Machine, MachineSpareMapping, SparePart

SEED_METADATA = {
    "name": "spare_mappings",
    "order": 430,
    "description": "Map machines to preferred spare parts",
}


def run():
    parts = {p.part_code: p for p in SparePart.query.all()}
    machines = {m.machine_code: m for m in Machine.query.all()}

    mappings = [
        {
            "machine_code": "AP-PUN-LATHE-01",
            "part_code": "AP-SPD-BRG-6205",
            "replacement_frequency_hours": 12000,
            "criticality_level": "high",
        },
        {
            "machine_code": "AP-MAA-MILL-01",
            "part_code": "AP-SPD-BRG-6205",
            "replacement_frequency_hours": 11000,
            "criticality_level": "medium",
        },
        {
            "machine_code": "AP-MAA-MILL-01",
            "part_code": "AP-CLT-PMP-03",
            "replacement_frequency_hours": 9000,
            "criticality_level": "high",
        },
        {
            "machine_code": "NW-AHD-PRESS-01",
            "part_code": "NW-HYD-SEAL-300",
            "replacement_frequency_hours": 6000,
            "criticality_level": "high",
        },
        {
            "machine_code": "EV-NOI-PACK-01",
            "part_code": "EV-HTR-01",
            "replacement_frequency_hours": 5000,
            "criticality_level": "medium",
        },
    ]

    for mapping in mappings:
        machine = machines.get(mapping["machine_code"])
        part = parts.get(mapping["part_code"])
        if not machine or not part:
            continue
        payload = {
            "machine_id": machine.id,
            "spare_part_id": part.id,
            "replacement_frequency_hours": mapping["replacement_frequency_hours"],
            "criticality_level": mapping["criticality_level"],
        }

        existing = MachineSpareMapping.query.filter_by(machine_id=machine.id, spare_part_id=part.id).first()
        if not existing:
            db.session.add(MachineSpareMapping(**payload))
        else:
            for field, value in payload.items():
                setattr(existing, field, value)
