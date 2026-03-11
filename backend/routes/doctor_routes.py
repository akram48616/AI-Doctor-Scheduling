# File path: backend/routes/doctor_routes.py
# This file handles doctor schedule and utilization endpoints

from flask import Blueprint, jsonify
from backend.services.scheduling import get_schedule_by_doctor
from backend.services.utilization import compute_doctor_utilization
from backend.utils.validators import sanitize_error_message

bp = Blueprint("doctor", __name__, url_prefix="/api/doctor")

@bp.route("/<int:doctor_id>/schedule", methods=["GET"])
def doctor_schedule(doctor_id):
    """
    Get schedule for a doctor.
    
    Args:
        doctor_id: Doctor ID (from URL)
    
    Returns:
        JSON with doctor's schedule and appointments
    """
    try:
        # Validate doctor ID
        if doctor_id <= 0:
            return jsonify({"success": False, "message": "Invalid doctor ID"}), 400
        
        schedule = get_schedule_by_doctor(doctor_id)
        return jsonify(schedule)
    except Exception as e:
        return jsonify({"success": False, "message": sanitize_error_message(e)}), 500


@bp.route("/<int:doctor_id>/utilization", methods=["GET"])
def doctor_utilization(doctor_id):
    """
    Get utilization metrics for a doctor.
    
    Args:
        doctor_id: Doctor ID (from URL)
    
    Returns:
        JSON with utilization metrics
    """
    try:
        # Validate doctor ID
        if doctor_id <= 0:
            return jsonify({"success": False, "message": "Invalid doctor ID"}), 400
        
        utilization = compute_doctor_utilization(doctor_id)
        return jsonify(utilization)
    except Exception as e:
        return jsonify({"success": False, "message": sanitize_error_message(e)}), 500