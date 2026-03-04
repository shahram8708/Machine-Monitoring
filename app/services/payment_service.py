import hmac
import hashlib
from typing import Dict, Any
import razorpay
from config import get_config
from app.services.subscription_service import start_subscription, update_subscription_status


def _client() -> razorpay.Client:
    cfg = get_config()
    return razorpay.Client(auth=(cfg.RAZORPAY_KEY_ID, cfg.RAZORPAY_SECRET))


def create_subscription(plan_id: str, total_count: int, customer_notify: bool = True) -> Dict[str, Any]:
    client = _client()
    payload = {
        "plan_id": plan_id,
        "total_count": total_count,
        "customer_notify": customer_notify,
    }
    return client.subscription.create(payload)


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    cfg = get_config()
    generated = hmac.new(cfg.RAZORPAY_SECRET.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(generated, signature)


def verify_webhook(body: bytes, signature: str) -> bool:
    cfg = get_config()
    expected = hmac.new(cfg.RAZORPAY_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def handle_webhook(event: Dict[str, Any]) -> None:
    payload = event.get("payload", {})
    entity = payload.get("subscription") or payload.get("payment") or {}
    subscription_id = entity.get("id")
    status = entity.get("status")
    if not subscription_id or not status:
        return
    # Update local subscription status when webhook arrives
    update_subscription_status_by_gateway_id(subscription_id, status)


def update_subscription_status_by_gateway_id(gateway_id: str, status: str) -> None:
    from app.models.subscription import CompanySubscription
    sub = CompanySubscription.query.filter_by(razorpay_subscription_id=gateway_id).first()
    if not sub:
        return
    update_subscription_status(sub.id, status.upper())
