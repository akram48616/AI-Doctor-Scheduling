"""
Main Flask application for AI Doctor Scheduling System.
Initializes app, config, DB, and registers blueprints.
"""
import logging
import sys
import os
from flask import Flask, jsonify
from flask_cors import CORS

from backend.config import get_config
from backend.utils.db import init_engine, init_session_factory, Base
from backend.routes.patient_routes import bp as patient_bp
from backend.routes.doctor_routes import bp as doctor_bp
from backend.routes.admin_routes import bp as admin_bp
from backend.routes.resource_routes import bp as resource_bp
from backend.routes.auth_routes import bp as auth_bp

# Configure logging
LOG_FILE = os.getenv("APP_LOG_FILE", "app.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_FILE)]
)
logger = logging.getLogger(__name__)


def create_app(test_engine=None):
    """
    Create and configure the Flask application.

    Args:
        test_engine: Optional SQLAlchemy Engine to use for testing. If provided,
                     the app will use this engine instead of calling init_engine().
    """
    app = Flask(__name__)

    # Load configuration
    config = get_config()
    app.config.from_object(config)

    logger.info("Starting application in %s mode", app.config.get("ENV", "development"))

    # Enable CORS
    CORS(app)

    # Initialize DB using provided engine or production init
    try:
        if test_engine is not None:
            engine = test_engine
            logger.info("Using injected test engine for DB")
        else:
            database_url = config.DATABASE_URL
            logger.info("Initializing database engine")
            engine = init_engine(database_url, echo=app.config.get("SQLALCHEMY_ECHO", False))

        if engine is None:
            raise RuntimeError("Failed to initialize database engine")

        # Wire engine into your session factory so get_session() works
        # init_session_factory should set up the sessionmaker/scoped_session used by get_session()
        init_session_factory(engine)

        # In development only: create tables if they don't exist
        if app.config.get("ENV", "").lower() == "development":
            logger.info("Development mode: creating tables if not exists")
            Base.metadata.create_all(bind=engine)

        logger.info("Database initialized successfully")
    except Exception as e:
        logger.exception("Failed to initialize database: %s", e)
        # Re-raise a clear error so callers (tests) can handle it
        raise RuntimeError("Failed to initialize database engine") from e

    # Register blueprints
    logger.info("Registering blueprints")
    app.register_blueprint(auth_bp)
    logger.info("Registered auth_bp at /api/auth")
    app.register_blueprint(patient_bp)
    logger.info("Registered patient_bp at /api/patient")
    app.register_blueprint(doctor_bp)
    logger.info("Registered doctor_bp at /api/doctor")
    app.register_blueprint(admin_bp)
    logger.info("Registered admin_bp at /api/admin")
    app.register_blueprint(resource_bp)
    logger.info("Registered resource_bp at /api/resource")

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({"status": "ok", "service": "AI Doctor Scheduling API", "version": "1.0.0"}), 200

    @app.route("/", methods=["GET"])
    def root():
        return jsonify({
            "service": "AI Doctor Scheduling API",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "auth": "/api/auth",
                "patient": "/api/patient",
                "doctor": "/api/doctor",
                "admin": "/api/admin",
                "resource": "/api/resource"
            }
        }), 200

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "message": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.exception("Internal server error: %s", error)
        return jsonify({"success": False, "message": "Internal server error"}), 500

    logger.info("Application setup complete")
    return app

# NOTE: Do not create an app at module import time. Use a separate runner for production.
# Example runner (outside this module):
#   from backend.app import create_app
#   app = create_app()
#   app.run(...)