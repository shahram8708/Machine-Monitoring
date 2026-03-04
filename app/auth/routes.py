from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt,
    get_jwt_identity,
    set_refresh_cookies,
    unset_jwt_cookies,
)
from app.extensions import db
from app.models.user import User
from app.models.company import Company
from app.security import set_active_company, clear_active_company
from app.models.token_blacklist import TokenBlacklist
from app.decorators import rate_limit
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


@auth_bp.route("/api/login", methods=["POST"])
@rate_limit()
def api_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not user.is_active or not user.check_password(password):
        return {"status": "error", "message": "Invalid credentials"}, 401

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    response = jsonify({"status": "success", "access_token": access_token})
    set_refresh_cookies(response, refresh_token)
    return response


@auth_bp.route("/api/refresh", methods=["POST"])
@jwt_required(refresh=True)
def api_refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=str(identity))
    return {"status": "success", "access_token": access_token}, 200


@auth_bp.route("/api/logout", methods=["POST"])
@jwt_required()
def api_logout():
    jti = get_jwt().get("jti")
    identity = get_jwt_identity()
    try:
        identity_int = int(identity) if identity is not None else None
    except (TypeError, ValueError):
        identity_int = None
    if jti and identity_int is not None:
        db.session.add(TokenBlacklist(token_jti=jti, user_id=identity_int))
        db.session.commit()
    resp = jsonify({"status": "success"})
    unset_jwt_cookies(resp)
    return resp
