from flask import Flask
from backend.routes import patient_routes, doctor_routes, admin_routes, resource_routes

def create_app():
    app = Flask(__name__)
    app.register_blueprint(patient_routes.bp)
    app.register_blueprint(doctor_routes.bp)
    app.register_blueprint(admin_routes.bp)
    app.register_blueprint(resource_routes.bp)
    return app