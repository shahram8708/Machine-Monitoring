from app.extensions import db


class RolePermission(db.Model):
    __tablename__ = "role_permissions"
    __table_args__ = (
        db.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
        db.Index("ix_role_permission", "role_id", "permission_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey("permissions.id"), nullable=False)

    role = db.relationship("Role", back_populates="permissions")
    permission = db.relationship("Permission", back_populates="roles")

    def __repr__(self) -> str:
        return f"<RolePermission role={self.role_id} perm={self.permission_id}>"
