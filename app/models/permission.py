from app.extensions import db


class Permission(db.Model):
    __tablename__ = "permissions"
    __table_args__ = (db.UniqueConstraint("module", "action", name="uq_permission_module_action"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    module = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(80), nullable=False)

    roles = db.relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Permission {self.module}:{self.action}>"
