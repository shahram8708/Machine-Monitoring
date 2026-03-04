from flask import abort, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.query import Query
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from flask_jwt_extended import JWTManager


class DevBypassQuery(Query):
    """Drop user/company scoping filters when dev flag is enabled."""

    _scope_keys = {
        "company_id",
        "user_id",
        "owner_id",
        "created_by",
        "created_by_id",
        "created_by_user_id",
        "author_id",
        "account_id",
    }

    @staticmethod
    def _bypass_enabled() -> bool:
        try:
            return current_app.config.get("DEV_SHOW_ALL_USERS_DATA", False)
        except Exception:
            return False

    def _should_skip(self, criterion) -> bool:
        if not self._bypass_enabled():
            return False
        key = getattr(getattr(criterion, "left", None), "key", None)
        return key in self._scope_keys

    def filter(self, *criteria):
        if self._bypass_enabled():
            criteria = tuple(c for c in criteria if not self._should_skip(c))
        return super().filter(*criteria)

    def filter_by(self, **kwargs):
        if self._bypass_enabled():
            kwargs = {k: v for k, v in kwargs.items() if k not in self._scope_keys}
        return super().filter_by(**kwargs)

    def get_or_404(self, ident, *, description: str | None = None):
        """Match Flask-SQLAlchemy helper so routes using query.get_or_404 keep working."""
        result = self.get(ident)
        if result is None:
            abort(404, description=description)
        return result

    def first_or_404(self, *, description: str | None = None):
        """Match Flask-SQLAlchemy helper so routes using query.first_or_404 keep working."""
        result = self.first()
        if result is None:
            abort(404, description=description)
        return result


db = SQLAlchemy(query_class=DevBypassQuery)
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()
scheduler = BackgroundScheduler()
mail = Mail()
jwt = JWTManager()
