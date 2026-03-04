from datetime import datetime
from flask import render_template, redirect, url_for, request, flash, abort, current_app
from flask_login import login_required, current_user
from flask_jwt_extended import create_access_token
from app.decorators import role_required
from app.extensions import db
from app.services.email_service import send_email
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.company import Company
from app.models.machine import Machine
from app.security import set_active_company, get_active_company_id, dev_show_all_data_enabled
from app.models.subscription import ContactInquiry
from . import main_bp


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.route("/dashboard")
@login_required
@role_required("admin", "manager", "viewer", "plant_manager", "maintenance_head", "technician", "super_admin", "enterprise_admin")
def dashboard():
    role = (current_user.active_role or "").upper()
    if role in {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN"}:
        return render_template("dashboard/ceo_dashboard.html")
    if role in {"PLANT_MANAGER"}:
        plant = current_user.plant_mappings.first().plant if current_user.plant_mappings.first() else None
        if plant:
            return redirect(url_for("main.plant_dashboard", plant_id=plant.id))
    if role in {"MAINTENANCE_HEAD"}:
        return render_template("dashboard/maintenance_dashboard.html")
    if role in {"TECHNICIAN"}:
        plant = current_user.plant_mappings.first().plant if current_user.plant_mappings.first() else None
        return render_template("dashboard/technician_dashboard.html", plant_id=plant.id if plant else None)
    return render_template("dashboard.html")


@main_bp.route("/dashboard/plant/<int:plant_id>")
@login_required
@role_required("PLANT_MANAGER", "ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN")
def plant_dashboard(plant_id: int):
    from app.models.plant import Plant

    plant = Plant.query.get_or_404(plant_id)
    if not dev_show_all_data_enabled():
        active_company_id = get_active_company_id()
        if active_company_id and plant.company_id != active_company_id:
            abort(403)
    return render_template("dashboard/plant_dashboard.html", plant=plant)


@main_bp.route("/dashboard/ceo")
@login_required
@role_required("ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN")
def ceo_dashboard():
    return render_template("dashboard/ceo_dashboard.html")


@main_bp.route("/dashboard/maintenance")
@login_required
@role_required("MAINTENANCE_HEAD", "ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN")
def maintenance_dashboard():
    return render_template("dashboard/maintenance_dashboard.html")


@main_bp.route("/dashboard/technician")
@login_required
@role_required("TECHNICIAN", "MAINTENANCE_HEAD", "ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN")
def technician_dashboard():
    plant = current_user.plant_mappings.first().plant if current_user.plant_mappings.first() else None
    return render_template("dashboard/technician_dashboard.html", plant_id=plant.id if plant else None)


@main_bp.route("/dashboard/rca")
@login_required
@role_required("TECHNICIAN", "MAINTENANCE_HEAD", "PLANT_MANAGER", "ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN", "MANAGER")
def rca_dashboard_view():
    token = create_access_token(identity=str(current_user.id))
    machines = Machine.query.filter_by(company_id=current_user.company_id).order_by(Machine.machine_name.asc()).all()
    return render_template(
        "dashboard/rca_dashboard.html",
        access_token=token,
        company_id=current_user.company_id,
        machines=machines,
    )


@main_bp.route("/dashboard/digital-twin/<int:machine_id>")
@login_required
@role_required("TECHNICIAN", "MAINTENANCE_HEAD", "PLANT_MANAGER", "ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN", "MANAGER", "VIEWER")
def digital_twin_dashboard(machine_id: int):
    machine = Machine.query.get_or_404(machine_id)
    if not dev_show_all_data_enabled():
        active_company_id = get_active_company_id()
        if active_company_id and machine.company_id != active_company_id:
            abort(403)

        if (current_user.active_role or "").upper() not in {"SUPER_ADMIN", "ENTERPRISE_ADMIN", "ADMIN"}:
            mapping_ids = {m.plant_id for m in current_user.plant_mappings}
            if machine.plant_id and machine.plant_id not in mapping_ids:
                abort(403)

    token = create_access_token(identity=str(current_user.id))
    return render_template("dashboard/digital_twin.html", machine=machine, access_token=token)


@main_bp.route("/dashboard/alerts/analytics")
@login_required
@role_required("TECHNICIAN", "MAINTENANCE_HEAD", "PLANT_MANAGER", "ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN", "MANAGER", "VIEWER")
def alert_analytics_dashboard():
    token = create_access_token(identity=str(current_user.id))
    plant_ids = [m.plant_id for m in current_user.plant_mappings]
    return render_template("dashboard/alert_analytics.html", access_token=token, plant_ids=plant_ids, company_id=current_user.company_id)


@main_bp.route("/dashboard/spares")
@login_required
@role_required("TECHNICIAN", "MAINTENANCE_HEAD", "PLANT_MANAGER", "ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN", "MANAGER", "VIEWER")
def spare_parts_dashboard():
    token = create_access_token(identity=str(current_user.id))
    default_machine = (
        Machine.query.filter_by(company_id=current_user.company_id)
        .order_by(Machine.machine_name.asc())
        .first()
    )
    return render_template(
        "dashboard/spare_parts_dashboard.html",
        access_token=token,
        default_machine_id=default_machine.id if default_machine else None,
    )


@main_bp.route("/dashboard/workforce")
@login_required
@role_required("MAINTENANCE_HEAD", "PLANT_MANAGER", "ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN", "MANAGER")
def workforce_dashboard():
    token = create_access_token(identity=str(current_user.id))
    return render_template("dashboard/workforce_dashboard.html", access_token=token)


@main_bp.route("/dashboard/financial")
@login_required
@role_required("PLANT_MANAGER", "ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN", "MANAGER")
def financial_dashboard():
    token = create_access_token(identity=str(current_user.id))
    return render_template("dashboard/financial_dashboard.html", access_token=token)


@main_bp.route("/dashboard/esg")
@login_required
@role_required("TECHNICIAN", "MAINTENANCE_HEAD", "PLANT_MANAGER", "ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN", "MANAGER", "VIEWER")
def esg_dashboard():
    token = create_access_token(identity=str(current_user.id))
    return render_template("dashboard/esg_dashboard.html", access_token=token)


@main_bp.route("/dashboard/subscription")
@login_required
@role_required("ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN")
def subscription_dashboard():
    token = create_access_token(identity=str(current_user.id))
    return render_template(
        "dashboard/subscription_dashboard.html",
        access_token=token,
        company_id=current_user.company_id,
    )


@main_bp.route("/dashboard/advanced-reports")
@login_required
@role_required("ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN", "MANAGER", "PLANT_MANAGER")
def advanced_reports_dashboard():
    token = create_access_token(identity=str(current_user.id))
    return render_template("dashboard/advanced_reports.html", access_token=token, company_id=current_user.company_id)


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
@role_required("ADMIN", "SUPER_ADMIN", "ENTERPRISE_ADMIN")
def switch_company(company_id: int):
    company = Company.query.get_or_404(company_id)
    set_active_company(company.id)
    flash(f"Switched to {company.company_name}.", "success")
    next_url = request.referrer or url_for("main.dashboard")
    return redirect(next_url)


@main_bp.route("/contact-sales", methods=["GET", "POST"])
def contact_sales():
    categories = [
        "Enterprise Plan",
        "Security Compliance",
        "Custom Integration",
        "On-Premise Deployment",
        "Volume Discount",
        "API Access",
        "Technical Support",
        "Pricing Clarification",
        "General Inquiry",
    ]

    if request.method == "POST":
        payload = {
            "full_name": request.form.get("full_name", "").strip(),
            "organization": request.form.get("organization", "").strip(),
            "email": request.form.get("email", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "industry": request.form.get("industry", "").strip(),
            "users_needed": request.form.get("users_needed", type=int),
            "category": request.form.get("category", "").strip(),
            "message": request.form.get("message", "").strip(),
            "company_id": current_user.company_id if current_user.is_authenticated else None,
        }
        if not payload["full_name"] or not payload["email"] or not payload["message"] or not payload["category"]:
            flash("Please fill in all required fields.", "danger")
            return render_template("contact_sales.html", categories=categories)
        inquiry = ContactInquiry(**payload)
        db.session.add(inquiry)
        db.session.commit()
        support_email = current_app.config.get("SALES_SUPPORT_EMAIL", "support@yourdomain.com")
        send_email(
            subject=f"New Sales Inquiry: {payload['category']}",
            recipients=[support_email],
            template="contact_inquiry",
            context={
                "subject": "New Contact Sales Inquiry",
                "headline": "A prospect reached out",
                "intro": "Someone submitted the contact form and is waiting for a response.",
                "full_name": payload["full_name"],
                "organization": payload["organization"],
                "email": payload["email"],
                "phone": payload["phone"],
                "industry": payload["industry"],
                "users_needed": payload["users_needed"],
                "category": payload["category"],
                "message": payload["message"],
                "company_id": payload["company_id"],
                "submitted_at": datetime.utcnow(),
                "action_url": current_app.config.get("CRM_INBOX_URL", "#"),
                "current_year": datetime.utcnow().year,
                "support_email": support_email,
            },
        )
        flash("Your request has been submitted. We will contact you shortly.", "success")
        return redirect(url_for("main.contact_sales"))

    return render_template("contact_sales.html", categories=categories)
