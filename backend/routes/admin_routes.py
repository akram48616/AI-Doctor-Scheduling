"""
Admin routes for analytics and system management.
"""
import logging
from flask import Blueprint, jsonify, request
from sqlalchemy import func

from backend.models import Patient, Doctor, Appointment, AppointmentStatus
from backend.utils.db import get_session

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/analytics", methods=["GET"])
def get_analytics():
    try:
        with get_session() as session:
            total_patients = session.query(func.count(Patient.id)).scalar()
            total_doctors = session.query(func.count(Doctor.id)).scalar()
            total_appointments = session.query(func.count(Appointment.id)).scalar()
            status_counts = {}
            for status in AppointmentStatus:
                count = session.query(func.count(Appointment.id)).filter(Appointment.status == status).scalar()
                status_counts[status.value] = count
            no_show_count = status_counts.get("no_show", 0)
            completed_count = status_counts.get("completed", 0)
            total_past = no_show_count + completed_count
            no_show_rate = round((no_show_count / total_past) * 100, 2) if total_past > 0 else 0.0
            avg_no_show_prob = session.query(func.avg(Appointment.no_show_probability)).filter(Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])).scalar()
            avg_no_show_prob = round(float(avg_no_show_prob), 3) if avg_no_show_prob else 0.0
            logger.info("Analytics retrieved")
            return jsonify({"success": True, "data": {"total_patients": total_patients, "total_doctors": total_doctors, "total_appointments": total_appointments, "no_show_rate": no_show_rate, "avg_predicted_no_show_probability": avg_no_show_prob, "appointments_by_status": status_counts}}), 200
    except Exception as e:
        logger.exception("Error getting analytics")
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route("/appointments/high-risk", methods=["GET"])
def get_high_risk_appointments():
    try:
        threshold = float(request.args.get("threshold", 0.5))
        with get_session() as session:
            high_risk = session.query(Appointment).filter(Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]), Appointment.no_show_probability >= threshold).order_by(Appointment.no_show_probability.desc()).all()
            logger.info("Retrieved %s high-risk appointments", len(high_risk))
            data = [{"id": a.id, "patient_id": a.patient_id, "doctor_id": a.doctor_id, "appointment_datetime": a.appointment_datetime.isoformat(), "status": getattr(a.status, "value", a.status), "no_show_probability": a.no_show_probability} for a in high_risk]
            return jsonify({"success": True, "data": {"threshold": threshold, "count": len(high_risk), "appointments": data}}), 200
    except Exception as e:
        logger.exception("Error getting high-risk appointments")
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route("/doctors", methods=["GET"])
def list_doctors():
    try:
        with get_session() as session:
            doctors = session.query(Doctor).all()
            data = [{"id": d.id, "hospital_id": d.hospital_id, "first_name": d.first_name, "last_name": d.last_name, "specialization": d.specialization, "email": d.email} for d in doctors]
            return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        logger.exception("Error listing doctors")
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route("/patients", methods=["GET"])
def list_patients():
    try:
        with get_session() as session:
            patients = session.query(Patient).all()
            data = [{"id": p.id, "first_name": p.first_name, "last_name": p.last_name, "email": p.email, "phone": p.phone, "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None} for p in patients]
            return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        logger.exception("Error listing patients")
        return jsonify({"success": False, "message": str(e)}), 500