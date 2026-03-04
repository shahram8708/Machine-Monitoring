from app.extensions import db


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255))

    permissions = db.relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    user_mappings = db.relationship("UserPlantMapping", back_populates="role", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Role {self.name}>"
