from datetime import datetime
from app.extensions import db

class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(120), unique=True, nullable=False)
    industry_type = db.Column(db.String(80))
    subscription_tier = db.Column(db.String(40), default="standard", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    users = db.relationship("User", back_populates="company", lazy="dynamic")
    machines = db.relationship(
        "Machine", back_populates="company", lazy="dynamic", cascade="all, delete-orphan"
    )
    plants = db.relationship(
        "Plant", back_populates="company", lazy="dynamic", cascade="all, delete-orphan"
    )
    subscriptions = db.relationship(
        "CompanySubscription", backref="company", lazy="dynamic", cascade="all, delete-orphan"
    )
    seat_allocations = db.relationship(
        "SeatAllocation", backref="company", lazy="dynamic", cascade="all, delete-orphan"
    )
    payment_transactions = db.relationship(
        "PaymentTransaction", backref="company", lazy="dynamic", cascade="all, delete-orphan"
    )
    contact_inquiries = db.relationship(
        "ContactInquiry", backref="company", lazy="dynamic", cascade="all, delete-orphan"
    )
    advanced_reports = db.relationship(
        "AdvancedReport", backref="company", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Company {self.company_name}>"

    @property
    def name(self) -> str:
        return self.company_name

    @name.setter
    def name(self, value: str) -> None:
        self.company_name = value
