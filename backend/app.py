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
from backend.utils.db import init_engine, init_session_factory, create_tables_if_not_exists
from backend.routes.patient_routes import patient_bp
from backend.routes.doctor_routes import doctor_bp
from backend.routes.admin_routes import admin_bp
from backend.routes.resource_routes import resource_bp

# Configure logging
LOG_FILE = os.getenv("APP_LOG_FILE", "app.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_FILE)]
)
logger = logging.getLogger(__name__)


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    config = get_config()
    app.config.from_object(config)

    logger.info("Starting application in %s mode", app.config.get("ENV", "development"))

    # Enable CORS
    CORS(app)

    # Initialize DB
    try:
        database_url = config.DATABASE_URL
        logger.info("Initializing database engine")
        engine = init_engine(database_url, echo=app.config.get("SQLALCHEMY_ECHO", False))
        init_session_factory(engine)

        if isinstance(config, type) and config.__name__ == "DevConfig":
            # If config is a class object (rare), skip; typical get_config returns instance
            pass

        # If running in development, create tables if not exist
        if app.config.get("ENV", "").lower() == "development":
            logger.info("Development mode: creating tables if not exists")
            create_tables_if_not_exists()

        logger.info("Database initialized")
    except Exception as e:
        logger.exception("Failed to initialize database: %s", e)
        raise

    # Register blueprints
    logger.info("Registering blueprints")
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


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = app.config.get("ENV", "").lower() == "development"
    logger.info("Starting Flask server on port %s (debug=%s)", port, debug)
    app.run(host="0.0.0.0", port=port, debug=debug)