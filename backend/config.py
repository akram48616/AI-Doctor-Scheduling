"""
Configuration module for AI Doctor Scheduling Backend.
Reads environment variables and constructs DATABASE_URL for MySQL if needed.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    ENV = os.getenv("FLASK_ENV", "development")
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SQLALCHEMY_POOL_SIZE = int(os.getenv("SQLALCHEMY_POOL_SIZE", 10))
    SQLALCHEMY_POOL_RECYCLE = int(os.getenv("SQLALCHEMY_POOL_RECYCLE", 3600))
    SQLALCHEMY_POOL_TIMEOUT = int(os.getenv("SQLALCHEMY_POOL_TIMEOUT", 30))


class DevConfig(BaseConfig):
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True

    @property
    def DATABASE_URL(self):
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return database_url
        db_host = os.getenv("DB_HOST")
        if db_host:
            db_user = os.getenv("DB_USER", "root")
            db_password = os.getenv("DB_PASSWORD", "")
            db_name = os.getenv("DB_NAME", "doctor_scheduling_ai")
            db_port = os.getenv("DB_PORT", "3306")
            return f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        return "sqlite:///dev.db"


class ProdConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

    @property
    def DATABASE_URL(self):
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return database_url
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT", "3306")
        db_name = os.getenv("DB_NAME")
        if not all([db_user, db_password, db_host, db_name]):
            raise RuntimeError("Production DB configuration incomplete")
        return f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def get_config():
    env = os.getenv("FLASK_ENV", "development").lower()
    if env == "production":
        return ProdConfig()
    return DevConfig()