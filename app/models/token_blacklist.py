from datetime import datetime
from app.extensions import db


class TokenBlacklist(db.Model):
    __tablename__ = "token_blacklist"
    __table_args__ = (
        db.UniqueConstraint("token_jti", name="uq_token_jti"),
        db.Index("ix_token_user", "user_id", "revoked_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    token_jti = db.Column(db.String(64), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User")

    def __repr__(self) -> str:
        return f"<TokenBlacklist {self.token_jti}>"
