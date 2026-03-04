import csv
import io
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import login_required, current_user

from app.decorators import admin_required
from app.extensions import db
from app.models.company import Company
from app.models.user import User
from app.models.user_plant_mapping import UserPlantMapping
from app.models.subscription import SeatAllocation
from app.services.subscription_service import compute_seat_limit, check_seat_available, get_latest_subscription
from . import admin_bp
from .forms import AdminUserForm, AdminUserInlineForm, CSVUploadForm


@admin_bp.route("/users", methods=["GET", "POST"])
@login_required
@admin_required
def users():
    role = (current_user.active_role or "").upper()
    if role not in {"SUPER_ADMIN", "ENTERPRISE_ADMIN"}:
        abort(403)

    company_filter = request.args.get("company_id", type=int) or current_user.company_id
    create_form = AdminUserInlineForm()
    csv_form = CSVUploadForm()
    create_form.company_id.data = company_filter
    csv_form.company_id.data = company_filter

    query = User.query.filter_by(company_id=company_filter)
    users = query.order_by(User.created_at.desc()).all()
    companies = Company.query.order_by(Company.company_name.asc()).all()

    seat_limit, latest_sub = compute_seat_limit(company_filter)
    active_users = User.query.filter_by(company_id=company_filter, is_active=True).count()
    seat_usage = {
        "limit": seat_limit,
        "used": active_users,
        "available": max(0, seat_limit - active_users),
        "subscription": latest_sub,
    }

    import_summary = None

    if create_form.submit_create.data and create_form.validate_on_submit():
        if not check_seat_available(create_form.company_id.data, 1):
            flash("Seat limit reached. Purchase additional seats to add users.", "danger")
        else:
            user = User(
                name=create_form.username.data.strip(),
                email=create_form.email.data.lower(),
                role=create_form.role.data,
                company_id=create_form.company_id.data,
                is_active=True,
            )
            user.set_password(create_form.username.data.strip())
            db.session.add(user)
            db.session.flush()
            if create_form.plant_id.data:
                db.session.add(UserPlantMapping(user_id=user.id, plant_id=create_form.plant_id.data))
            db.session.add(SeatAllocation(company_id=user.company_id, user_id=user.id, subscription_id=latest_sub.id if latest_sub else None))
            if latest_sub:
                latest_sub.active_seats = max(0, (latest_sub.active_seats or 0) + 1)
            db.session.commit()
            flash("User created with default password (username).", "success")
            return redirect(url_for("admin.users", company_id=company_filter))

    if csv_form.submit_upload.data and csv_form.validate_on_submit():
        file_storage = csv_form.file.data
        try:
            content = file_storage.read().decode("utf-8")
        except Exception:
            flash("Unable to read CSV file.", "danger")
            return redirect(url_for("admin.users", company_id=company_filter))

        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        seats_needed = len(rows)
        if not check_seat_available(csv_form.company_id.data, seats_needed):
            flash("Not enough seats for bulk upload. Purchase more seats and retry.", "danger")
        else:
            created = 0
            skipped = 0
            failed = 0
            for row in rows:
                username = (row.get("username") or "").strip()
                email = (row.get("email") or "").lower().strip()
                role_value = (row.get("role") or "").strip()
                if not username or not email or not role_value:
                    failed += 1
                    continue
                if User.query.filter_by(email=email).first():
                    skipped += 1
                    continue
                user = User(
                    name=username,
                    email=email,
                    role=role_value,
                    company_id=csv_form.company_id.data,
                    is_active=True,
                )
                user.set_password(username)
                db.session.add(user)
                db.session.flush()
                db.session.add(SeatAllocation(company_id=user.company_id, user_id=user.id, subscription_id=latest_sub.id if latest_sub else None))
                created += 1
            if latest_sub:
                latest_sub.active_seats = max(0, (latest_sub.active_seats or 0) + created)
            db.session.commit()
            import_summary = {"created": created, "skipped": skipped, "failed": failed}
            flash(f"Import complete. Created {created}, skipped {skipped}, failed {failed}.", "info")

    return render_template(
        "admin/users.html",
        users=users,
        companies=companies,
        company_filter=company_filter,
        seat_usage=seat_usage,
        create_form=create_form,
        csv_form=csv_form,
        import_summary=import_summary,
    )


@admin_bp.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    role = (current_user.active_role or "").upper()
    if role not in {"SUPER_ADMIN", "ENTERPRISE_ADMIN"}:
        abort(403)
    form = AdminUserForm()
    if form.validate_on_submit():
        if not check_seat_available(form.company_id.data, 1):
            flash("Seat limit reached. Purchase additional seats to add users.", "danger")
        else:
            user = User(
                name=form.name.data.strip(),
                email=form.email.data.lower(),
                role=form.role.data,
                company_id=form.company_id.data,
                is_active=form.active.data,
            )
            user.set_password(form.name.data.strip())
            db.session.add(user)
            db.session.flush()
            latest_sub = get_latest_subscription(user.company_id)
            db.session.add(SeatAllocation(company_id=user.company_id, user_id=user.id, subscription_id=latest_sub.id if latest_sub else None))
            if latest_sub:
                latest_sub.active_seats = max(0, (latest_sub.active_seats or 0) + 1)
            db.session.commit()
            flash("User created with default password (username).", "success")
            return redirect(url_for("admin.users", company_id=user.company_id))
    return render_template("admin/user_form.html", form=form, is_edit=False)


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id: int):
    user = User.query.get_or_404(user_id)
    form = AdminUserForm(obj=user)
    form.user_id = user.id
    if form.validate_on_submit():
        user.name = form.name.data.strip()
        user.email = form.email.data.lower()
        user.role = form.role.data
        user.company_id = form.company_id.data
        user.is_active = form.active.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash("User updated.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, is_edit=True)


@admin_bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@login_required
@admin_required
def deactivate_user(user_id: int):
    user = User.query.get_or_404(user_id)
    user.is_active = False
    allocation = SeatAllocation.query.filter_by(user_id=user.id, company_id=user.company_id, status="ACTIVE").first()
    if allocation:
        allocation.status = "RELEASED"
        allocation.released_at = allocation.released_at or allocation.allocated_at
    latest_sub = get_latest_subscription(user.company_id)
    if latest_sub and latest_sub.active_seats:
        latest_sub.active_seats = max(0, latest_sub.active_seats - 1)
    db.session.commit()
    flash("User deactivated.", "info")
    return redirect(url_for("admin.users"))
