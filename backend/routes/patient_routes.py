# File path: backend/routes/patient_routes.py
# This file handles patient appointment booking and viewing

from flask import Blueprint, jsonify, request
from backend.services.scheduling import get_appointments_by_patient, book_appointment
from backend.utils.validators import validate_appointment_booking, sanitize_error_message

bp = Blueprint("patient", __name__, url_prefix="/api/patient")

@bp.route("/<int:patient_id>/appointments", methods=["GET"])
def patient_appointments(patient_id):
    """
    Get all appointments for a patient.
    
    Args:
        patient_id: Patient ID (from URL)
    
    Returns:
        JSON with list of appointments
    """
    try:
        # Validate patient ID
        if patient_id <= 0:
            return jsonify({"success": False, "message": "Invalid patient ID"}), 400
        
        appointments = get_appointments_by_patient(patient_id)
        return jsonify(appointments)
    except Exception as e:
        return jsonify({"success": False, "message": sanitize_error_message(e)}), 500


@bp.route("/<int:patient_id>/book", methods=["POST"])
def patient_book(patient_id):
    """
    Book an appointment for a patient.
    
    Request JSON:
    {
        "doctor_id": 1,
        "datetime": "2026-03-15T14:00:00",
        "hospital_id": 1 (optional),
        "duration_minutes": 30 (optional),
        "reason": "Checkup" (optional)
    }
    
    Args:
        patient_id: Patient ID (from URL)
    
    Returns:
        JSON with booking result
    """
    try:
        # Validate patient ID
        if patient_id <= 0:
            return jsonify({"success": False, "message": "Invalid patient ID"}), 400
        
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No JSON data provided"}), 400
        
        # Extract fields
        doctor_id = data.get("doctor_id")
        datetime_str = data.get("datetime")
        hospital_id = data.get("hospital_id")
        duration_minutes = data.get("duration_minutes")
        reason = data.get("reason")
        
        # Validate input
        is_valid, error_msg = validate_appointment_booking(
            doctor_id=doctor_id,
            datetime_str=datetime_str,
            hospital_id=hospital_id,
            duration_minutes=duration_minutes,
            reason=reason
        )
        
        if not is_valid:
            return jsonify({"success": False, "message": error_msg}), 400
        
        # Book appointment
        result = book_appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_datetime=datetime_str,
            hospital_id=hospital_id,
            duration_minutes=duration_minutes,
            reason=reason
        )
        
        if result.get("success"):
            return jsonify(result), 201  # 201 Created
        else:
            return jsonify(result), 400
    
    except Exception as e:
        return jsonify({"success": False, "message": sanitize_error_message(e)}), 500