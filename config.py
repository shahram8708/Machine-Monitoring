import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'app.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SIMULATION_MODE = os.getenv("SIMULATION_MODE", "false").lower() == "true"
    SIM_API_BASE_URL = os.getenv("SIM_API_BASE_URL", "http://127.0.0.1:5000/api/v1")
    SIM_INGEST_INTERVAL_SECONDS = int(os.getenv("SIM_INGEST_INTERVAL_SECONDS", "5"))
    SIM_HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("SIM_HEARTBEAT_INTERVAL_SECONDS", "30"))
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    WTF_CSRF_TIME_LIMIT = None
    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "25"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "false").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "alerts@monitoring.local")
    ALERT_ESCALATION_MINUTES = int(os.getenv("ALERT_ESCALATION_MINUTES", "10"))
    DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "UTC")
    SIMULATION_MODE = os.getenv("SIMULATION_MODE", "true").lower() == "true"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_map.get(env.lower(), DevelopmentConfig)
