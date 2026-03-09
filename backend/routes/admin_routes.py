from flask import Blueprint, jsonify
from backend.services.overbooking import generate_plan
from backend.services.optimization import run_daily_plan
from backend.services.utilization import generate_report

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

@bp.route("/overbooking/plan", methods=["GET"])
def overbooking_plan():
    plan = generate_plan()
    return jsonify(plan)

@bp.route("/optimization/run", methods=["POST"])
def optimization_run():
    result = run_daily_plan()
    return jsonify(result)

@bp.route("/utilization/report", methods=["GET"])
def utilization_report():
    report = generate_report()
    return jsonify(report)