# File path: backend/routes/admin_routes.py
# This file handles admin operations for overbooking, optimization, and reporting

from flask import Blueprint, jsonify
from backend.services.overbooking import generate_plan
from backend.services.optimization import run_daily_plan
from backend.services.utilization import generate_report
from backend.utils.validators import sanitize_error_message
import logging

logger = logging.getLogger(__name__)
bp = Blueprint("admin", __name__, url_prefix="/api/admin")

@bp.route("/overbooking/plan", methods=["GET"])
def overbooking_plan():
    """
    Generate overbooking plan.
    
    Admin-only endpoint that generates recommendations for overbooking slots
    based on no-show probabilities.
    
    Returns:
        JSON with overbooking plan
    """
    try:
        logger.info("Generating overbooking plan")
        plan = generate_plan()
        return jsonify(plan)
    except Exception as e:
        logger.exception("Error generating overbooking plan")
        return jsonify({"success": False, "message": sanitize_error_message(e)}), 500

@bp.route("/optimization/run", methods=["POST"])
def optimization_run():
    """
    Run daily optimization plan.
    
    Admin-only endpoint that triggers the daily optimization engine to
    optimize appointment slots across all doctors.
    
    Returns:
        JSON with optimization results
    """
    try:
        logger.info("Running daily optimization")
        result = run_daily_plan()
        return jsonify(result)
    except Exception as e:
        logger.exception("Error running optimization")
        return jsonify({"success": False, "message": sanitize_error_message(e)}), 500

@bp.route("/utilization/report", methods=["GET"])
def utilization_report():
    """
    Generate utilization report.
    
    Admin-only endpoint that generates a comprehensive utilization report
    across all doctors and appointments.
    
    Returns:
        JSON with utilization metrics
    """
    try:
        logger.info("Generating utilization report")
        report = generate_report()
        return jsonify(report)
    except Exception as e:
        logger.exception("Error generating utilization report")
        return jsonify({"success": False, "message": sanitize_error_message(e)}), 500