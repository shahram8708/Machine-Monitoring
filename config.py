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
    DEV_SHOW_ALL_USERS_DATA = os.getenv("DEV_SHOW_ALL_USERS_DATA", "false").lower() == "true"
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-jwt-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "15")))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7")))
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", "false").lower() == "true"
    JWT_COOKIE_SAMESITE = os.getenv("JWT_COOKIE_SAMESITE", "Lax")
    JWT_COOKIE_CSRF_PROTECT = True
    RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "120"))
    RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "200"))
    SIMULATION_MODE = os.getenv("SIMULATION_MODE", "false").lower() == "true"
    SIM_API_BASE_URL = os.getenv("SIM_API_BASE_URL", "http://127.0.0.1:5000/api/v1")
    SIM_INGEST_INTERVAL_SECONDS = int(os.getenv("SIM_INGEST_INTERVAL_SECONDS", "5"))
    SIM_HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("SIM_HEARTBEAT_INTERVAL_SECONDS", "30"))
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "20"))
    GEMINI_MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "2"))
    AI_FAILURE_THRESHOLD = float(os.getenv("AI_FAILURE_THRESHOLD", "65"))
    AI_HEALTH_THRESHOLD = float(os.getenv("AI_HEALTH_THRESHOLD", "60"))
    AI_DEGRADATION_THRESHOLD = float(os.getenv("AI_DEGRADATION_THRESHOLD", "70"))
    EXPORT_BASE_DIR = os.getenv("EXPORT_BASE_DIR", str(BASE_DIR / "generated_reports"))
    CACHE_DEFAULT_TTL_SECONDS = int(os.getenv("CACHE_DEFAULT_TTL_SECONDS", "300"))
    REPORT_CACHE_TTL_SECONDS = int(os.getenv("REPORT_CACHE_TTL_SECONDS", "900"))
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_SECRET = os.getenv("RAZORPAY_SECRET", "")
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
    SUBSCRIPTION_CHECK_ENABLED = os.getenv("SUBSCRIPTION_CHECK_ENABLED", "true").lower() == "true"


class DevelopmentConfig(Config):
    DEBUG = True
    DEV_SHOW_ALL_USERS_DATA = os.getenv("DEV_SHOW_ALL_USERS_DATA", "true").lower() == "true"
    SUBSCRIPTION_CHECK_ENABLED = os.getenv("SUBSCRIPTION_CHECK_ENABLED", "false").lower() == "true"


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
