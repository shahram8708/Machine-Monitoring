from flask import Flask
from flask_login import current_user
from .extensions import db, migrate, login_manager, bcrypt, csrf, mail
from config import get_config
from .models.user import User
from .models import Machine, Sensor, AuditLog, MachineData, AiAnalysis, Alert  # noqa: F401
from .models.company import Company
from .scheduler import init_scheduler
from .security import get_active_company_id

def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

    from .auth import auth_bp
    from .main import main_bp
    from .machines import machines_bp
    from .api import api_bp
    from .analytics import analytics_bp
    from .ai import ai_bp
    from .alerts import alerts_bp
    from .reports import reports_bp
    from .admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(machines_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    init_scheduler(app)

    @app.context_processor
    def inject_navbar_context():
        active_company_id = get_active_company_id()
        active_company = None
        if active_company_id:
            active_company = Company.query.get(active_company_id)

        companies = []
        if current_user.is_authenticated and current_user.is_admin:
            companies = Company.query.order_by(Company.company_name.asc()).all()

        unread_alerts = []
        unread_alert_count = 0
        if current_user.is_authenticated and active_company_id:
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

    return app
