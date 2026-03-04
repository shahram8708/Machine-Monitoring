from datetime import datetime
from app.extensions import db


class APIRateLimit(db.Model):
    __tablename__ = "api_rate_limits"
    __table_args__ = (
        db.UniqueConstraint("user_id", "endpoint", "window_start", name="uq_rate_limit_window"),
        db.Index("ix_rate_limit_user_endpoint", "user_id", "endpoint"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    endpoint = db.Column(db.String(255), nullable=False)
    request_count = db.Column(db.Integer, default=0, nullable=False)
    window_start = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User")

    def __repr__(self) -> str:
        return f"<APIRateLimit user={self.user_id} endpoint={self.endpoint} count={self.request_count}>"
