from datetime import date
from flask import Blueprint, jsonify, request, abort
from flask_jwt_extended import jwt_required
from app.extensions import csrf
from sqlalchemy import func
from app.audit import log_action
from app.decorators import rate_limit
from app.api.management_routes import _resolve_user, _user_role, _check_company_access
from app.services.subscription_service import ensure_default_plans, start_subscription, get_active_subscription, feature_enabled
from app.services.usage_service import get_company_usage
from app.models.usage_analytics import UsageMetric
from app.services.payment_service import (
    create_subscription as gateway_create_subscription,
    verify_payment_signature,
    verify_webhook,
    handle_webhook,
)
from app.models.user import User


subscription_bp = Blueprint("subscription", __name__, url_prefix="/api/subscription")
usage_bp = Blueprint("usage", __name__, url_prefix="/api/usage")

ADMIN_ROLES = {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN"}


def _admin_guard(user):
    role = _user_role(user)
    if role not in ADMIN_ROLES:
        abort(403)


def _coerce_date(value: str | None):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@subscription_bp.route("/plans", methods=["GET"])
@jwt_required()
@rate_limit()
def list_plans():
    ensure_default_plans()
    from app.models.subscription import SubscriptionPlan

    plans = SubscriptionPlan.query.order_by(SubscriptionPlan.price_monthly.asc()).all()
    return jsonify([
        {
            "id": p.id,
            "name": p.name,
            "max_plants": p.max_plants,
            "max_machines": p.max_machines,
            "ai_prediction_limit": p.ai_prediction_limit,
            "advanced_reports_enabled": p.advanced_reports_enabled,
            "digital_twin_enabled": p.digital_twin_enabled,
            "workforce_analytics_enabled": p.workforce_analytics_enabled,
            "price_monthly": float(p.price_monthly or 0),
            "price_yearly": float(p.price_yearly or 0),
        }
        for p in plans
    ])


@subscription_bp.route("/start", methods=["POST"])
@csrf.exempt
@jwt_required()
@rate_limit()
def start_plan():
    user = _resolve_user()
    _admin_guard(user)
    data = request.get_json() or {}
    plan_name = data.get("plan_name")
    if not plan_name:
        abort(400)
    sub = start_subscription(user.company_id, plan_name, duration_months=data.get("duration_months", 1), razorpay_subscription_id=data.get("razorpay_subscription_id"))
    log_action("subscription_started", "subscription", sub.id, company_id=user.company_id, new_value={"plan_name": plan_name})
    return jsonify({"status": "started", "subscription_id": sub.id})


@subscription_bp.route("/status", methods=["GET"])
@jwt_required()
@rate_limit()
def subscription_status():
    user = _resolve_user()
    sub = get_active_subscription(user.company_id)
    if not sub:
        return jsonify({"active": False})
    return jsonify({
        "active": sub.is_active,
        "plan": sub.plan.name if sub.plan else None,
        "ends_at": sub.end_date.isoformat() if sub.end_date else None,
        "status": sub.status,
    })


@subscription_bp.route("/feature/<string:feature_name>", methods=["GET"])
@jwt_required()
@rate_limit()
def feature_check(feature_name: str):
    user = _resolve_user()
    return jsonify({"feature": feature_name, "enabled": feature_enabled(user.company_id, feature_name)})


@usage_bp.route("/company/<int:company_id>", methods=["GET"])
@jwt_required()
@rate_limit()
def company_usage(company_id: int):
    user = _resolve_user()
    _check_company_access(user, company_id)
    usage = get_company_usage(company_id)
    return jsonify(usage)


@usage_bp.route("/company/<int:company_id>/history", methods=["GET"])
@jwt_required()
@rate_limit()
def company_usage_history(company_id: int):
    user = _resolve_user()
    _check_company_access(user, company_id)
    metric = request.args.get("metric")
    start = _coerce_date(request.args.get("start_date"))
    end = _coerce_date(request.args.get("end_date"))

    query = (
        UsageMetric.query.with_entities(UsageMetric.date, UsageMetric.metric_type, func.sum(UsageMetric.count))
        .filter(UsageMetric.company_id == company_id)
    )
    if metric:
        query = query.filter(UsageMetric.metric_type == metric)
    if start:
        query = query.filter(UsageMetric.date >= start)
    if end:
        query = query.filter(UsageMetric.date <= end)

    rows = (
        query.group_by(UsageMetric.date, UsageMetric.metric_type)
        .order_by(UsageMetric.date.asc())
        .all()
    )
    history = [
        {"date": d.isoformat(), "metric": m, "count": int(total or 0)}
        for d, m, total in rows
    ]
    return jsonify(history)


def _compute_amount(seats: int, billing_cycle: str) -> float:
    included = 5
    if billing_cycle == "yearly":
        base = 14999
        seat_price = 2999
    else:
        base = 1499
        seat_price = 299
    extra = max(0, seats - included) * seat_price
    return float(base + extra)


@subscription_bp.route("/create", methods=["POST"])
@csrf.exempt
@jwt_required()
@rate_limit()
def create_subscription():
    user = _resolve_user()
    _admin_guard(user)
    payload = request.get_json() or {}
    seats = int(payload.get("seats") or 5)
    billing_cycle = (payload.get("billing_cycle") or "monthly").lower()
    current_users = User.query.filter_by(company_id=user.company_id, is_active=True).count()
    if seats < current_users:
        abort(400, description="Seat count below current usage")
    amount = _compute_amount(seats, billing_cycle)
    plan_id = payload.get("plan_id")
    if not plan_id:
        abort(400, description="plan_id required for Razorpay subscription")
    subscription = gateway_create_subscription(plan_id=plan_id, total_count=12, customer_notify=True)
    log_action("razorpay_subscription_created", "payment", user.id, company_id=user.company_id, new_value={"plan_id": plan_id, "seats": seats, "billing_cycle": billing_cycle, "amount": amount})
    return jsonify({"razorpay_subscription": subscription, "amount": amount, "billing_cycle": billing_cycle, "seats": seats})


@subscription_bp.route("/verify", methods=["POST"])
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


@subscription_bp.route("/webhook", methods=["POST"])
@csrf.exempt
def subscription_webhook():
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
    plan_name = notes.get("plan_name") or "PRO"
    seats = int(notes.get("seats") or 5)
    billing_cycle = notes.get("billing_cycle") or "monthly"
    if company_id and plan_name:
        start_subscription(company_id, plan_name, duration_months=1 if billing_cycle == "monthly" else 12, razorpay_subscription_id=entity.get("id"), seats=seats, billing_cycle=billing_cycle)
    log_action("razorpay_webhook_received", "payment", 0, company_id=company_id, new_value=event)
    return jsonify({"status": "ok"})
