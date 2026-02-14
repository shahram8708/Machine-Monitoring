from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.decorators import admin_required
from app.extensions import db
from app.models.company import Company
from app.models.user import User
from . import admin_bp
from .forms import AdminUserForm


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    company_filter = request.args.get("company_id", type=int)
    query = User.query
    if company_filter:
        query = query.filter_by(company_id=company_filter)
    users = query.order_by(User.created_at.desc()).all()
    companies = Company.query.order_by(Company.company_name.asc()).all()
    return render_template("admin/users.html", users=users, companies=companies, company_filter=company_filter)


@admin_bp.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    form = AdminUserForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower(),
            role=form.role.data,
            company_id=form.company_id.data,
            is_active=form.active.data,
        )
        user.set_password(form.password.data or "ChangeMe123!")
        db.session.add(user)
        db.session.commit()
        flash("User created.", "success")
        return redirect(url_for("admin.users"))
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
    db.session.commit()
    flash("User deactivated.", "info")
    return redirect(url_for("admin.users"))
