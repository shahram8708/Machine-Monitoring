from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.company import Company
from app.security import set_active_company, clear_active_company
from . import auth_bp
from .forms import RegistrationForm, LoginForm


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():
        company_name = form.company_name.data.strip()
        company = Company.query.filter_by(company_name=company_name).first()
        if not company:
            company = Company(company_name=company_name)
            db.session.add(company)
            db.session.flush()

        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower(),
            role=form.role.data,
            company=company,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.is_active and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            set_active_company(user.company_id)
            flash("Welcome back!", "success")
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("main.dashboard"))
        elif user and not user.is_active:
            flash("Account is deactivated. Contact an administrator.", "danger")
        else:
            flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    clear_active_company()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
