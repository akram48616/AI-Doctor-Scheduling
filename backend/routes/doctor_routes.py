"""
Doctor routes for viewing schedules and managing availability.
"""
import logging
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta

from backend.models import Doctor, DoctorAvailability, Appointment, AppointmentStatus
from backend.utils.db import get_session
from backend.utils.validators import validate_time_string

logger = logging.getLogger(__name__)
doctor_bp = Blueprint("doctor", __name__, url_prefix="/api/doctor")


def json_response(success: bool, data=None, message: str = "", status: int = 200):
    return jsonify({"success": success, "data": data or {}, "message": message}), status


@doctor_bp.route("/<int:doctor_id>", methods=["GET"])
def get_doctor(doctor_id):
    try:
        with get_session() as session:
            doctor = session.query(Doctor).filter(Doctor.id == doctor_id).first()
            if not doctor:
                return json_response(False, message="Doctor not found", status=404)
            data = {"id": doctor.id, "hospital_id": doctor.hospital_id, "first_name": doctor.first_name, "last_name": doctor.last_name, "specialization": doctor.specialization, "phone": doctor.phone, "email": doctor.email, "consultation_duration": doctor.consultation_duration, "created_at": doctor.created_at.isoformat() if doctor.created_at else None}
            return json_response(True, data=data)
    except Exception as e:
        logger.exception("Error getting doctor")
        return json_response(False, message=str(e), status=500)


@doctor_bp.route("/<int:doctor_id>/schedule", methods=["GET"])
def get_doctor_schedule(doctor_id):
    try:
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        if not start_date_str:
            start_date = datetime.now().date()
        else:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        if not end_date_str:
            end_date = (datetime.now() + timedelta(days=7)).date()
        else:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        with get_session() as session:
            doctor = session.query(Doctor).filter(Doctor.id == doctor_id).first()
            if not doctor:
                return json_response(False, message="Doctor not found", status=404)
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            appts = session.query(Appointment).filter(Appointment.doctor_id == doctor_id, Appointment.appointment_datetime >= start_dt, Appointment.appointment_datetime <= end_dt).order_by(Appointment.appointment_datetime).all()
            data = {"doctor_id": doctor_id, "start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "appointments": [{"id": a.id, "patient_id": a.patient_id, "appointment_datetime": a.appointment_datetime.isoformat(), "duration_minutes": a.duration_minutes, "status": getattr(a.status, "value", a.status), "reason": a.reason, "no_show_probability": a.no_show_probability} for a in appts]}
            return json_response(True, data=data)
    except Exception as e:
        logger.exception("Error getting schedule")
        return json_response(False, message=str(e), status=500)


@doctor_bp.route("/<int:doctor_id>/availability", methods=["GET"])
def get_doctor_availability(doctor_id):
    try:
        with get_session() as session:
            doctor = session.query(Doctor).filter(Doctor.id == doctor_id).first()
            if not doctor:
                return json_response(False, message="Doctor not found", status=404)
            avail = session.query(DoctorAvailability).filter(DoctorAvailability.doctor_id == doctor_id).order_by(DoctorAvailability.day_of_week).all()
            data = [{"id": a.id, "day_of_week": a.day_of_week, "start_time": a.start_time.strftime("%H:%M:%S"), "end_time": a.end_time.strftime("%H:%M:%S"), "is_available": bool(a.is_available)} for a in avail]
            return json_response(True, data=data)
    except Exception as e:
        logger.exception("Error getting availability")
        return json_response(False, message=str(e), status=500)


@doctor_bp.route("/<int:doctor_id>/availability", methods=["POST"])
def add_doctor_availability(doctor_id):
    try:
        data = request.get_json() or {}
        if "day_of_week" not in data or "start_time" not in data or "end_time" not in data:
            return json_response(False, message="day_of_week, start_time, end_time required", status=400)
        is_valid, error = validate_time_string(data["start_time"])
        if not is_valid:
            return json_response(False, message=f"start_time: {error}", status=400)
        is_valid, error = validate_time_string(data["end_time"])
        if not is_valid:
            return json_response(False, message=f"end_time: {error}", status=400)
        with get_session() as session:
            doctor = session.query(Doctor).filter(Doctor.id == doctor_id).first()
            if not doctor:
                return json_response(False, message="Doctor not found", status=404)
            availability = DoctorAvailability(doctor_id=doctor_id, day_of_week=int(data["day_of_week"]), start_time=datetime.strptime(data["start_time"], "%H:%M:%S").time(), end_time=datetime.strptime(data["end_time"], "%H:%M:%S").time(), is_available=1 if data.get("is_available", True) else 0)
            session.add(availability)
            session.commit()
            logger.info("Availability added for doctor %s", doctor_id)
            return json_response(True, data={"id": availability.id, "doctor_id": doctor_id, "day_of_week": availability.day_of_week, "start_time": availability.start_time.strftime("%H:%M:%S"), "end_time": availability.end_time.strftime("%H:%M:%S")}, message="Availability added", status=201)
    except Exception as e:
        logger.exception("Error adding availability")
        return json_response(False, message=str(e), status=500)


@doctor_bp.route("/<int:doctor_id>/availability/<int:availability_id>", methods=["PUT"])
def update_doctor_availability(doctor_id, availability_id):
    try:
        data = request.get_json() or {}
        with get_session() as session:
            availability = session.query(DoctorAvailability).filter(DoctorAvailability.id == availability_id, DoctorAvailability.doctor_id == doctor_id).first()
            if not availability:
                return json_response(False, message="Availability not found", status=404)
            if "day_of_week" in data:
                availability.day_of_week = int(data["day_of_week"])
            if "start_time" in data:
                is_valid, error = validate_time_string(data["start_time"])
                if not is_valid:
                    return json_response(False, message=error, status=400)
                availability.start_time = datetime.strptime(data["start_time"], "%H:%M:%S").time()
            if "end_time" in data:
                is_valid, error = validate_time_string(data["end_time"])
                if not is_valid:
                    return json_response(False, message=error, status=400)
                availability.end_time = datetime.strptime(data["end_time"], "%H:%M:%S").time()
            if "is_available" in data:
                availability.is_available = 1 if data["is_available"] else 0
            session.commit()
            logger.info("Availability %s updated", availability_id)
            return json_response(True, message="Availability updated")
    except Exception as e:
        logger.exception("Error updating availability")
        return json_response(False, message=str(e), status=500)