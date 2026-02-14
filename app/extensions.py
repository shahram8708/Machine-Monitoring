from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf import CSRFProtect
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()
csrf = CSRFProtect()
scheduler = BackgroundScheduler()
mail = Mail()
