"""
Patient routes for registration, profile management, and appointment booking.
"""
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from backend.models import Patient, Appointment
from backend.utils.db import get_session
from backend.utils.validators import validate_email, validate_phone, validate_date_string, validate_required_fields
from backend.services.scheduling import book_appointment as scheduling_book_appointment

logger = logging.getLogger(__name__)
patient_bp = Blueprint("patient", __name__, url_prefix="/api/patient")


def json_response(success: bool, data=None, message: str = "", status: int = 200):
    payload = {"success": success, "data": data or {}, "message": message}
    return jsonify(payload), status


@patient_bp.route("/register", methods=["POST"])
def register_patient():
    try:
        data = request.get_json() or {}
        required = ["first_name", "last_name", "date_of_birth", "gender", "phone", "email"]
        is_valid, error = validate_required_fields(data, required)
        if not is_valid:
            return json_response(False, message=error, status=400)
        is_valid, error = validate_email(data["email"])
        if not is_valid:
            return json_response(False, message=error, status=400)
        is_valid, error = validate_phone(data["phone"])
        if not is_valid:
            return json_response(False, message=error, status=400)
        is_valid, error = validate_date_string(data["date_of_birth"])
        if not is_valid:
            return json_response(False, message=error, status=400)
        with get_session() as session:
            existing = session.query(Patient).filter(Patient.email == data["email"]).first()
            if existing:
                return json_response(False, message="Email already registered", status=409)
            patient = Patient(
                first_name=data["first_name"],
                last_name=data["last_name"],
                date_of_birth=datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date(),
                gender=data["gender"],
                phone=data["phone"],
                email=data["email"],
                address=data.get("address"),
                emergency_contact=data.get("emergency_contact"),
                emergency_phone=data.get("emergency_phone"),
                medical_history=data.get("medical_history")
            )
            session.add(patient)
            session.commit()
            logger.info("Patient registered: %s (id=%s)", patient.email, patient.id)
            return json_response(True, data={"patient_id": patient.id, "first_name": patient.first_name, "last_name": patient.last_name, "email": patient.email}, message="Patient registered", status=201)
    except Exception as e:
        logger.exception("Error registering patient")
        return json_response(False, message=str(e), status=500)


@patient_bp.route("/<int:patient_id>", methods=["GET"])
def get_patient(patient_id: int):
    try:
        with get_session() as session:
            patient = session.query(Patient).filter(Patient.id == patient_id).first()
            if not patient:
                return json_response(False, message=f"Patient {patient_id} not found", status=404)
            data = {
                "id": patient.id,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
                "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                "gender": patient.gender,
                "phone": patient.phone,
                "email": patient.email,
                "address": patient.address,
                "emergency_contact": patient.emergency_contact,
                "emergency_phone": patient.emergency_phone,
                "medical_history": patient.medical_history,
                "created_at": patient.created_at.isoformat() if patient.created_at else None
            }
            return json_response(True, data=data)
    except Exception as e:
        logger.exception("Error getting patient")
        return json_response(False, message=str(e), status=500)


@patient_bp.route("/<int:patient_id>", methods=["PUT"])
def update_patient(patient_id: int):
    try:
        data = request.get_json() or {}
        if "email" in data:
            is_valid, error = validate_email(data["email"])
            if not is_valid:
                return json_response(False, message=error, status=400)
        if "phone" in data:
            is_valid, error = validate_phone(data["phone"])
            if not is_valid:
                return json_response(False, message=error, status=400)
        if "date_of_birth" in data:
            is_valid, error = validate_date_string(data["date_of_birth"])
            if not is_valid:
                return json_response(False, message=error, status=400)
        with get_session() as session:
            patient = session.query(Patient).filter(Patient.id == patient_id).first()
            if not patient:
                return json_response(False, message=f"Patient {patient_id} not found", status=404)
            updatable = ["first_name", "last_name", "gender", "phone", "email", "address", "emergency_contact", "emergency_phone", "medical_history"]
            for field in updatable:
                if field in data:
                    setattr(patient, field, data[field])
            if "date_of_birth" in data:
                patient.date_of_birth = datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date()
            session.commit()
            logger.info("Patient %s updated", patient_id)
            return json_response(True, data={"patient_id": patient.id, "email": patient.email}, message="Patient updated")
    except Exception as e:
        logger.exception("Error updating patient")
        return json_response(False, message=str(e), status=500)


@patient_bp.route("/<int:patient_id>", methods=["DELETE"])
def delete_patient(patient_id: int):
    try:
        with get_session() as session:
            patient = session.query(Patient).filter(Patient.id == patient_id).first()
            if not patient:
                return json_response(False, message=f"Patient {patient_id} not found", status=404)
            session.delete(patient)
            session.commit()
            logger.info("Patient %s deleted", patient_id)
            return json_response(True, message="Patient deleted")
    except Exception as e:
        logger.exception("Error deleting patient")
        return json_response(False, message=str(e), status=500)


@patient_bp.route("/<int:patient_id>/appointments", methods=["GET"])
def get_patient_appointments(patient_id: int):
    try:
        with get_session() as session:
            patient = session.query(Patient).filter(Patient.id == patient_id).first()
            if not patient:
                return json_response(False, message=f"Patient {patient_id} not found", status=404)
            appts = session.query(Appointment).filter(Appointment.patient_id == patient_id).order_by(Appointment.appointment_datetime.desc()).all()
            data = [{"id": a.id, "doctor_id": a.doctor_id, "hospital_id": a.hospital_id, "appointment_datetime": a.appointment_datetime.isoformat(), "duration_minutes": a.duration_minutes, "status": getattr(a.status, "value", a.status), "reason": a.reason, "no_show_probability": a.no_show_probability} for a in appts]
            return json_response(True, data=data)
    except Exception as e:
        logger.exception("Error getting appointments")
        return json_response(False, message=str(e), status=500)
@patient_bp.route("/cancel/<int:appointment_id>", methods=["PUT"])
def cancel_appointment(appointment_id: int):
    try:
        with get_session() as session:
            appt = session.query(Appointment).filter(Appointment.id == appointment_id).first()
            if not appt:
                return json_response(False, message="Appointment not found", status=404)

            appt.status = "CANCELLED"
            session.commit()

            return json_response(True, message="Appointment cancelled")
    except Exception as e:
        return json_response(False, message=str(e), status=500)



@patient_bp.route("/book", methods=["POST"])
def book_patient_appointment():
    try:
        data = request.get_json() or {}
        required = ["patient_id", "doctor_id", "hospital_id"]
        is_valid, error = validate_required_fields(data, required)
        if not is_valid:
            return json_response(False, message=error, status=400)
        patient_id = int(data["patient_id"])
        doctor_id = int(data["doctor_id"])
        hospital_id = int(data["hospital_id"])
        appointment_datetime = data.get("appointment_datetime")
        preferred_date = data.get("preferred_date")
        duration_minutes = data.get("duration_minutes", 30)
        reason = data.get("reason")
        appt_dt = None
        if appointment_datetime:
            try:
                appt_dt = datetime.fromisoformat(appointment_datetime)
            except Exception:
                return json_response(False, message="Invalid appointment_datetime format", status=400)
        preferred_date_obj = None
        if not appt_dt and preferred_date:
            try:
                preferred_date_obj = datetime.strptime(preferred_date, "%Y-%m-%d").date()
            except Exception:
                return json_response(False, message="Invalid preferred_date format", status=400)
        result = scheduling_book_appointment(patient_id=patient_id, doctor_id=doctor_id, hospital_id=hospital_id, appointment_datetime=appt_dt or preferred_date_obj, duration_minutes=duration_minutes, reason=reason)
        if not result.get("success"):
            return json_response(False, message=result.get("message", "Booking failed"), status=400)
        return json_response(True, data=result.get("data"), message=result.get("message", "Appointment booked"), status=201)
    except Exception as e:
        logger.exception("Error booking appointment")
        return json_response(False, message=str(e), status=500)
@patient_bp.route("/optimal-slot", methods=["POST"])
def optimal_slot():
    try:
        data = request.get_json() or {}

        required = ["patient_id", "doctor_id", "preferred_date", "consultation_minutes"]
        is_valid, error = validate_required_fields(data, required)
        if not is_valid:
            return json_response(False, message=error, status=400)

        patient_id = int(data["patient_id"])
        doctor_id = int(data["doctor_id"])
        preferred_date = data["preferred_date"]
        consultation_minutes = int(data["consultation_minutes"])

        try:
            preferred_date_obj = datetime.strptime(preferred_date, "%Y-%m-%d").date()
        except Exception:
            return json_response(False, message="Invalid preferred_date format", status=400)

        # Temporary dummy logic
        optimal_datetime = datetime.combine(preferred_date_obj, datetime.strptime("11:00", "%H:%M").time())

        return json_response(
            True,
            data={
                "doctor_id": doctor_id,
                "optimal_datetime": optimal_datetime.isoformat(),
                "estimated_no_show_probability": 0.08
            },
            message="Optimal slot calculated"
        )

    except Exception as e:
        logger.exception("Error calculating optimal slot")
        return json_response(False, message=str(e), status=500)
