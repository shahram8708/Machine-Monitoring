from datetime import datetime
from app.extensions import db


class UserPlantMapping(db.Model):
    __tablename__ = "user_plant_mappings"
    __table_args__ = (
        db.UniqueConstraint("user_id", "plant_id", name="uq_user_plant"),
        db.Index("ix_user_plant_role", "user_id", "plant_id", "role_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    plant_id = db.Column(db.Integer, db.ForeignKey("plants.id"), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="plant_mappings")
    plant = db.relationship("Plant", back_populates="user_mappings")
    role = db.relationship("Role", back_populates="user_mappings")

    def __repr__(self) -> str:
        return f"<UserPlantMapping user={self.user_id} plant={self.plant_id} role={self.role_id}>"
