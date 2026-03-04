from flask import Blueprint, jsonify, request, abort
from flask_jwt_extended import jwt_required
from app.extensions import csrf
from app.audit import log_action
from app.decorators import rate_limit
from app.api.management_routes import _resolve_user, _user_role
from app.services.payment_service import create_subscription as gateway_create_subscription
from app.services.payment_service import verify_payment_signature, verify_webhook, handle_webhook
from app.services.subscription_service import start_subscription


payment_bp = Blueprint("payment", __name__, url_prefix="/api/payment")

ADMIN_ROLES = {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN"}


def _admin_guard(user):
    role = _user_role(user)
    if role not in ADMIN_ROLES:
        abort(403)


@payment_bp.route("/create-subscription", methods=["POST"])
@csrf.exempt
@jwt_required()
@rate_limit()
def create_subscription():
    user = _resolve_user()
    _admin_guard(user)
    data = request.get_json() or {}
    plan_id = data.get("plan_id")
    if not plan_id:
        abort(400)
    subscription = gateway_create_subscription(plan_id=plan_id, total_count=data.get("total_count", 12))
    log_action("razorpay_subscription_created", "payment", user.id, company_id=user.company_id, new_value={"plan_id": plan_id})
    return jsonify(subscription)


@payment_bp.route("/verify", methods=["POST"])
@csrf.exempt
@jwt_required()
@rate_limit()
def verify():
    user = _resolve_user()
    _admin_guard(user)
    data = request.get_json() or {}
    order_id = data.get("order_id")
    payment_id = data.get("payment_id")
    signature = data.get("signature")
    if not all([order_id, payment_id, signature]):
        abort(400)
    verified = verify_payment_signature(order_id, payment_id, signature)
    if verified:
        log_action("payment_verified", "payment", user.id, company_id=user.company_id, new_value=data)
    return jsonify({"verified": verified})


@payment_bp.route("/webhook", methods=["POST"])
@csrf.exempt
def webhook():
    signature = request.headers.get("X-Razorpay-Signature")
    body = request.get_data()
    if not signature or not verify_webhook(body, signature):
        abort(400)
    event = request.get_json() or {}
    handle_webhook(event)
    entity = event.get("payload", {}).get("subscription", {}).get("entity") or {}
    company_id = None
    plan_name = None
    notes = entity.get("notes") or {}
    if notes.get("company_id"):
        try:
            company_id = int(notes.get("company_id"))
        except (TypeError, ValueError):
            company_id = None
    plan_name = notes.get("plan_name")
    if company_id and plan_name:
        start_subscription(company_id, plan_name, duration_months=1, razorpay_subscription_id=entity.get("id"))
    log_action("razorpay_webhook_received", "payment", 0, company_id=company_id, new_value=event)
    return jsonify({"status": "ok"})
