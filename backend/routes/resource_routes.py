# File path: backend/routes/resource_routes.py
# This file handles resource optimization endpoints

from flask import Blueprint, jsonify, request
from backend.services.optimization import optimize_slots
from backend.utils.validators import validate_slot_optimization, sanitize_error_message
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
bp = Blueprint("resource", __name__, url_prefix="/api/resource")

@bp.route("/optimized-slots", methods=["GET"])
def optimized_slots():
    """
    Get optimized appointment slots.
    
    Query Parameters:
        doctors: Comma-separated list of doctor IDs (required)
        date: ISO format date (YYYY-MM-DD) (required)
    
    Example:
        GET /api/resource/optimized-slots?doctors=1,2,3&date=2026-03-15
    
    Returns:
        JSON with list of optimized slots
    """
    try:
        # Get query parameters
        doctors_str = request.args.get("doctors", "")
        date_str = request.args.get("date", "")
        
        # Validate that parameters are provided
        if not doctors_str or not date_str:
            return jsonify({
                "error": "Missing required parameters",
                "message": "Both 'doctors' and 'date' parameters are required"
            }), 400
        
        # Parse doctor IDs
        try:
            doctor_ids = [int(x.strip()) for x in doctors_str.split(",") if x.strip().isdigit()]
        except ValueError:
            return jsonify({
                "error": "Invalid doctor IDs",
                "message": "Doctor IDs must be comma-separated integers"
            }), 400
        
        if not doctor_ids:
            return jsonify({
                "error": "Invalid doctor IDs",
                "message": "At least one valid doctor ID is required"
            }), 400
        
        # Validate input
        is_valid, error_msg = validate_slot_optimization(doctor_ids=doctor_ids, date=date_str)
        
        if not is_valid:
            return jsonify({"error": "Invalid input", "message": error_msg}), 400
        
        # Parse date
        try:
            date = datetime.fromisoformat(date_str).date()
        except ValueError:
            return jsonify({
                "error": "Invalid date format",
                "message": "Date must be in ISO format (YYYY-MM-DD)"
            }), 400
        
        # Get optimized slots
        logger.info(f"Getting optimized slots for doctors {doctor_ids} on {date}")
        slots = optimize_slots(doctor_ids, date)
        
        # Format response
        out = [{"doctor_id": s["doctor_id"], "slot": s["slot"].isoformat()} for s in slots]
        
        return jsonify({
            "success": True,
            "slots": out,
            "count": len(out)
        }), 200
    
    except Exception as e:
        logger.exception(f"Error getting optimized slots: {e}")
        return jsonify({
            "error": "Internal server error",
            "message": sanitize_error_message(e)
        }), 500