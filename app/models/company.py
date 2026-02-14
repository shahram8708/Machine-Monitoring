from datetime import datetime
from app.extensions import db

class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    users = db.relationship("User", back_populates="company", lazy="dynamic")
    machines = db.relationship(
        "Machine", back_populates="company", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Company {self.company_name}>"
