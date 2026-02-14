from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.decorators import role_required
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.company import Company
from app.security import set_active_company
from . import main_bp


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.route("/dashboard")
@login_required
@role_required("admin", "manager", "viewer")
def dashboard():
    return render_template("dashboard.html")


@main_bp.route("/audit-logs")
@login_required
@role_required("admin")
def audit_history():
    action = request.args.get("action", "").strip()
    entity_type = request.args.get("entity_type", "").strip()
    user_id = request.args.get("user_id", "").strip()

    query = AuditLog.query.order_by(AuditLog.timestamp.desc())
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if user_id.isdigit():
        query = query.filter(AuditLog.user_id == int(user_id))

    logs = query.limit(200).all()
    users = User.query.order_by(User.name).all()

    return render_template(
        "audit/history.html",
        logs=logs,
        filter_action=action,
        filter_entity=entity_type,
        filter_user=user_id,
        users=users,
    )


@main_bp.route("/switch-company/<int:company_id>", methods=["POST"])
@login_required
@role_required("admin")
def switch_company(company_id: int):
    company = Company.query.get_or_404(company_id)
    set_active_company(company.id)
    flash(f"Switched to {company.company_name}.", "success")
    next_url = request.referrer or url_for("main.dashboard")
    return redirect(next_url)
