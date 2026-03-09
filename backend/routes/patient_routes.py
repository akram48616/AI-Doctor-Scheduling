from flask import Blueprint, jsonify, request
from backend.services.scheduling import get_appointments_by_patient, book_appointment

bp = Blueprint("patient", __name__, url_prefix="/api/patient")

@bp.route("/<int:patient_id>/appointments", methods=["GET"])
def patient_appointments(patient_id):
    appointments = get_appointments_by_patient(patient_id)
    return jsonify(appointments)

@bp.route("/<int:patient_id>/book", methods=["POST"])
def patient_book(patient_id):
    data = request.get_json()
    doctor_id = data.get("doctor_id")
    datetime_str = data.get("datetime")
    result = book_appointment(patient_id, doctor_id, datetime_str)
    return jsonify(result)