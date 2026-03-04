from datetime import datetime, timedelta
from app.extensions import db


class SubscriptionPlan(db.Model):
    __tablename__ = "subscription_plans"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    base_seats = db.Column(db.Integer, nullable=False, default=5)
    max_plants = db.Column(db.Integer, nullable=False, default=1)
    max_machines = db.Column(db.Integer, nullable=False, default=5)
    ai_prediction_limit = db.Column(db.Integer, nullable=False, default=500)
    advanced_reports_enabled = db.Column(db.Boolean, nullable=False, default=False)
    digital_twin_enabled = db.Column(db.Boolean, nullable=False, default=False)
    workforce_analytics_enabled = db.Column(db.Boolean, nullable=False, default=False)
    price_monthly = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    price_yearly = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    seat_price_monthly = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    seat_price_yearly = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    def __repr__(self) -> str:  # pragma: no cover - repr only
        return f"<SubscriptionPlan {self.name}>"


class CompanySubscription(db.Model):
    __tablename__ = "company_subscriptions"
    __table_args__ = (
        db.Index("ix_company_subscription_status", "company_id", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey("subscription_plans.id"), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    expiry_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="ACTIVE")
    billing_cycle = db.Column(db.String(10), nullable=False, default="monthly")
    purchased_seats = db.Column(db.Integer, nullable=False, default=5)
    active_seats = db.Column(db.Integer, nullable=False, default=0)
    razorpay_subscription_id = db.Column(db.String(120))

    plan = db.relationship("SubscriptionPlan")

    def activate(self, months: int = 1, seats: int | None = None, billing_cycle: str = "monthly") -> None:
        self.start_date = datetime.utcnow()
        self.end_date = self.start_date + timedelta(days=30 * months)
        self.expiry_date = self.end_date
        self.status = "ACTIVE"
        self.billing_cycle = billing_cycle
        if seats:
            self.purchased_seats = max(self.purchased_seats, seats)

    @property
    def is_active(self) -> bool:
        if self.status != "ACTIVE":
            return False
        edge = self.expiry_date or self.end_date
        if edge and edge < datetime.utcnow():
            return False
        return True

    @property
    def seats_available(self) -> int:
        return max(self.purchased_seats, self.plan.base_seats if self.plan else 0)

    @property
    def expires_in_days(self) -> int | None:
        edge = self.expiry_date or self.end_date
        if not edge:
            return None
        return max(0, (edge - datetime.utcnow()).days)

    def __repr__(self) -> str:  # pragma: no cover - repr only
        return f"<CompanySubscription company={self.company_id} plan={self.plan_id} status={self.status}>"


class SeatAllocation(db.Model):
    __tablename__ = "seat_allocations"
    __table_args__ = (
        db.UniqueConstraint("company_id", "user_id", name="uq_seat_allocation_user"),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("company_subscriptions.id"), nullable=True)
    allocated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    released_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default="ACTIVE")

    subscription = db.relationship("CompanySubscription")


class PaymentTransaction(db.Model):
    __tablename__ = "payment_transactions"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("company_subscriptions.id"))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(8), nullable=False, default="INR")
    billing_cycle = db.Column(db.String(10), nullable=False, default="monthly")
    seats = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="INITIATED")
    razorpay_payment_id = db.Column(db.String(120))
    razorpay_subscription_id = db.Column(db.String(120))
    signature_verified = db.Column(db.Boolean, default=False, nullable=False)
    meta = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    subscription = db.relationship("CompanySubscription")


class ContactInquiry(db.Model):
    __tablename__ = "contact_inquiries"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    organization = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    industry = db.Column(db.String(80))
    users_needed = db.Column(db.Integer)
    category = db.Column(db.String(80), nullable=False)
    message = db.Column(db.Text, nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

