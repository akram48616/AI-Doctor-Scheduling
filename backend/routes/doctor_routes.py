from flask import Blueprint, jsonify
from backend.services.scheduling import get_schedule_by_doctor
from backend.services.utilization import compute_doctor_utilization

bp = Blueprint("doctor", __name__, url_prefix="/api/doctor")

@bp.route("/<int:doctor_id>/schedule", methods=["GET"])
def doctor_schedule(doctor_id):
    schedule = get_schedule_by_doctor(doctor_id)
    return jsonify(schedule)

@bp.route("/<int:doctor_id>/utilization", methods=["GET"])
def doctor_utilization(doctor_id):
    utilization = compute_doctor_utilization(doctor_id)
    return jsonify(utilization)