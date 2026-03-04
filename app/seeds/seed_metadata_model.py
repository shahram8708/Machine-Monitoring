from datetime import datetime
from app.extensions import db


class SeedMetadata(db.Model):
    __tablename__ = "seed_metadata"
    __table_args__ = (db.UniqueConstraint("name", name="uq_seed_metadata_name"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.String(255))
    applied_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime(2026, 3, 3, 12, 0, 0))
    runtime_seconds = db.Column(db.Float)
    success = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<SeedMetadata {self.name} at {self.applied_at.isoformat()}>"
