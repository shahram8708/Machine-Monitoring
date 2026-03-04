from datetime import datetime
from flask import has_request_context, request
from flask_login import UserMixin, current_user
from sqlalchemy import event
from app.extensions import db, bcrypt


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="viewer")
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    primary_role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    company = db.relationship("Company", back_populates="users")
    primary_role = db.relationship("Role")
    plant_mappings = db.relationship(
        "UserPlantMapping",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    seat_allocation = db.relationship(
        "SeatAllocation",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        role_name = self.role or ""
        primary_name = self.primary_role.name if self.primary_role else None
        active_role = primary_name or role_name
        return active_role.lower() in {"admin", "super_admin", "enterprise_admin"}

    @property
    def active_role(self) -> str:
        if self.primary_role:
            return self.primary_role.name
        return self.role


    def __repr__(self):
        return f"<User {self.email}>"


@event.listens_for(User, "before_update")
def log_user_role_change(mapper, connection, target):
    state = db.inspect(target)
    history = state.attrs.role.history
    if not history.has_changes():
        return

    old_role = history.deleted[0] if history.deleted else None
    new_role = history.added[0] if history.added else None
    if old_role == new_role:
        return

    actor_id = None
    ip_address = None
    if has_request_context():
        actor_id = current_user.id if current_user.is_authenticated else None
        ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)

    from app.models.audit_log import AuditLog  # local import to avoid circular dependency

    connection.execute(
        AuditLog.__table__.insert(),
        {
            "user_id": actor_id,
            "company_id": target.company_id,
            "action": "user_role_changed",
            "action_type": "role_change",
            "entity_type": "user",
            "entity_id": target.id,
            "old_value": {"role": old_role},
            "previous_value": {"role": old_role},
            "new_value": {"role": new_role},
            "timestamp": datetime.utcnow(),
            "ip_address": ip_address,
        },
    )
