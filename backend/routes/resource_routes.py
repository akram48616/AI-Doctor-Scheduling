from flask import Blueprint, jsonify, request
from backend.services.optimization import optimize_slots
from datetime import datetime

bp = Blueprint("resource", __name__, url_prefix="/api/resource")

@bp.route("/optimized-slots", methods=["GET"])
def optimized_slots():
    doctors = request.args.get("doctors", "")
    date_str = request.args.get("date")
    doctor_ids = [int(x) for x in doctors.split(",") if x.strip().isdigit()]
    try:
        date = datetime.fromisoformat(date_str).date() if date_str else None
    except Exception:
        return jsonify({"error": "Invalid date format"}), 400
    slots = optimize_slots(doctor_ids, date)
    out = [{"doctor_id": s["doctor_id"], "slot": s["slot"].isoformat()} for s in slots]
    return jsonify({"slots": out})