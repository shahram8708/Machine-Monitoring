import os
import sys
import logging
from flask import Flask, render_template, request, current_app
from werkzeug.exceptions import HTTPException
from flask_login import current_user
from flask import redirect, url_for, flash
from flask_login import logout_user
from .extensions import db, migrate, login_manager, bcrypt, csrf, mail, jwt
from config import get_config
from .models.user import User
from .models import (
    Machine,
    Sensor,
    AuditLog,
    MachineData,
    AiAnalysis,
    Alert,
    TokenBlacklist,
    Plant,
    Department,
    Role,
    Permission,
    RolePermission,
    UserPlantMapping,
    MachineKPI,
    MachineHealthScore,
    AIPrediction,
    SparePart,
    MachineSpareMapping,
    SpareInventory,
    TechnicianPerformance,
    MaintenanceTask,
    ExecutiveReport,
)  # noqa: F401
from .models.company import Company
from .scheduler import init_scheduler
from .security import get_active_company_id, clear_active_company
from app.services.subscription_service import get_latest_subscription
from app.seeds.seed_runner import SeedRunner


def _configure_logging(app: Flask) -> None:
    """Emit verbose errors with stack traces to the console."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))

    if not any(isinstance(h, logging.StreamHandler) for h in app.logger.handlers):
        app.logger.addHandler(handler)

    app.logger.setLevel(logging.DEBUG)
    app.logger.propagate = False


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    _configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    jwt.init_app(app)

    from .auth import auth_bp
    from .main import main_bp
    from .machines import machines_bp
    from .api import api_bp
    from .analytics import analytics_bp
    from .ai import ai_bp
    from .alerts import alerts_bp
    from .reports import reports_bp
    from .admin import admin_bp
    from .routes.spare_routes import spare_bp
    from .routes.workforce_routes import workforce_bp
    from .routes.financial_routes import financial_bp
    from .routes.esg_routes import esg_bp
    from .routes.report_routes import report_api_bp
    from .routes.subscription_routes import subscription_bp, usage_bp
    from .routes.payment_routes import payment_bp
    from .routes.analytics_routes import advanced_analytics_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(machines_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(spare_bp)
    app.register_blueprint(workforce_bp)
    app.register_blueprint(financial_bp)
    app.register_blueprint(esg_bp)
    app.register_blueprint(report_api_bp)
    app.register_blueprint(subscription_bp)
    app.register_blueprint(usage_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(advanced_analytics_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    init_scheduler(app)

    @app.before_request
    def enforce_subscription_guard():
        if not current_user.is_authenticated:
            return
        if not current_app.config.get("SUBSCRIPTION_CHECK_ENABLED", True):
            return
        if request.blueprint in {"auth"}:
            return
        if request.path.startswith("/static"):
            return
        sub = get_latest_subscription(current_user.company_id)
        if sub and not sub.is_active:
            role = (current_user.active_role or "").upper()
            if role not in {"SUPER_ADMIN", "ENTERPRISE_ADMIN"}:
                logout_user()
                clear_active_company()
                flash("Subscription expired. Please contact an administrator to renew.", "danger")
                return redirect(url_for("auth.login"))
    @app.context_processor
    def inject_navbar_context():
        # Rendering can run outside a request (e.g., scheduled emails); guard against missing user context.
        user = getattr(current_user, "_get_current_object", lambda: None)()
        active_company_id = get_active_company_id()
        active_company = Company.query.get(active_company_id) if active_company_id else None

        companies = []
        if user and getattr(user, "is_authenticated", False) and getattr(user, "is_admin", False):
            companies = Company.query.order_by(Company.company_name.asc()).all()

        unread_alerts = []
        unread_alert_count = 0
        if user and getattr(user, "is_authenticated", False) and active_company_id:
            unread_alerts = (
                Alert.query.filter_by(company_id=active_company_id, is_resolved=False)
                .order_by(Alert.created_at.desc())
                .limit(5)
                .all()
            )
            unread_alert_count = (
                Alert.query.filter_by(company_id=active_company_id, is_resolved=False)
                .count()
            )

        return {
            "active_company": active_company,
            "company_options": companies,
            "unread_alerts": unread_alerts,
            "unread_alert_count": unread_alert_count,
        }

    # Start AI worker after app is ready
    from app.ai.worker import init_ai_worker  # Imported late to avoid circulars

    init_ai_worker(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        return TokenBlacklist.query.filter_by(token_jti=jti).first() is not None

    @jwt.additional_claims_loader
    def add_claims_to_access_token(identity):
        user = User.query.get(identity)
        if not user:
            return {}
        plant_ids = [m.plant_id for m in user.plant_mappings]
        return {
            "company_id": user.company_id,
            "role": user.active_role,
            "plants": plant_ids,
        }

    SeedRunner(app).run_if_enabled()

    def render_error(error):
        # Some exceptions carry a None code; fall back to 500 to avoid comparisons failing.
        status_code = getattr(error, "code", None) or 500
        # Defensive: some exceptions carry string codes; normalize to int for comparisons.
        try:
            status_code = int(status_code)
        except Exception:
            status_code = 500
        default_description = "Something went wrong. Please try again."
        description = getattr(error, "description", default_description) or default_description
        if status_code >= 500 and description == default_description:
            description = "Our server ran into an issue. Please try again in a moment."

        # Ignore favicon hits to avoid noisy logs.
        if getattr(request, "path", "") == "/favicon.ico":
            return "", status_code

        try:
            detail_text = str(error)
        except Exception:
            detail_text = "Unable to stringify error."

        try:
            json_payload = request.get_json(silent=True)
        except Exception:
            json_payload = None

        exc_info = (type(error), error, getattr(error, "__traceback__", None)) if isinstance(error, Exception) else None

        # Log rich context to the console for any error.
        app.logger.error(
            "Error %s | type=%s | method=%s | path=%s | user_id=%s | args=%s | form_keys=%s | json=%s",
            status_code,
            type(error).__name__,
            getattr(request, "method", "<no-request>"),
            getattr(request, "path", "<no-path>"),
            getattr(current_user, "id", None),
            getattr(request, "args", {}).to_dict(flat=False) if hasattr(request, "args") else {},
            list(getattr(request, "form", {}).keys()) if hasattr(request, "form") else [],
            json_payload,
            exc_info=exc_info,
        )

        return (
            render_template(
                "error.html",
                status_code=status_code,
                error_title=getattr(error, "name", "Unexpected Error"),
                description=description,
                request_path=request.path,
                error_details=detail_text,
                error_type=type(error).__name__,
            ),
            status_code,
        )

    for code in (400, 401, 403, 404, 405, 408, 410, 413, 415, 422, 429, 500, 503):
        app.register_error_handler(code, render_error)

    # Catch-all for any HTTPException not explicitly listed above.
    app.register_error_handler(HTTPException, render_error)

    app.register_error_handler(Exception, render_error)

    @app.after_request
    def log_non_success_responses(response):
        if response.status_code < 400:
            return response

        if getattr(request, "path", "") == "/favicon.ico":
            return response

        try:
            resp_json = response.get_json(silent=True)
        except Exception:
            resp_json = None

        try:
            body_preview = response.get_data(as_text=True)[:1000]
        except Exception:
            body_preview = "<unreadable-response-body>"

        try:
            req_json = request.get_json(silent=True)
        except Exception:
            req_json = None

        app.logger.error(
            "Response %s | method=%s | path=%s | user_id=%s | args=%s | form_keys=%s | req_json=%s | resp_json=%s | resp_body=%s",
            response.status_code,
            getattr(request, "method", "<no-method>"),
            getattr(request, "path", "<no-path>"),
            getattr(current_user, "id", None),
            getattr(request, "args", {}).to_dict(flat=False) if hasattr(request, "args") else {},
            list(getattr(request, "form", {}).keys()) if hasattr(request, "form") else [],
            req_json,
            resp_json,
            body_preview,
        )

        return response

    return app
