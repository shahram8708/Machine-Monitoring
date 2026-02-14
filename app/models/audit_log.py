from datetime import datetime
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    action = db.Column(db.String(120), nullable=False)
    entity_type = db.Column(db.String(60), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    old_value = db.Column(db.JSON)
    new_value = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip_address = db.Column(db.String(45))

    user = db.relationship("User")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} on {self.entity_type}:{self.entity_id}>"
