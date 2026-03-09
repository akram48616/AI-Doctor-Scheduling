# backend/services/scheduling.py
import logging
from datetime import datetime, timedelta, time, timezone
from typing import List, Dict, Optional, Any
from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    Doctor,
    DoctorAvailability,
    Appointment,
    Patient,
    Hospital,
    AppointmentStatus,
)
from backend.utils.db import get_session
from backend.services.ml_model import get_predictor, build_features

logger = logging.getLogger(__name__)

SLOT_INCREMENT_MINUTES = 15
MAX_BOOKING_DAYS_AHEAD = 90
UTC = timezone.utc


def _ensure_date(date_input: Any):
    if isinstance(date_input, str):
        try:
            return datetime.strptime(date_input, "%Y-%m-%d").date()
        except Exception:
            try:
                return datetime.fromisoformat(date_input).date()
            except Exception:
                raise ValueError("Invalid date format. Use YYYY-MM-DD or ISO date.")
    if isinstance(date_input, datetime):
        return date_input.date()
    if hasattr(date_input, "year") and hasattr(date_input, "month") and hasattr(date_input, "day"):
        return date_input
    raise ValueError("Unsupported date input type")


def _normalize_datetime_input(value: Any) -> datetime:
    if value is None:
        raise ValueError("appointment_datetime is required")
    if isinstance(value, datetime):
        dt = value.replace(microsecond=0)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC).replace(microsecond=0)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            dt = dt.replace(microsecond=0)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC).replace(microsecond=0)
        except Exception:
            try:
                d = datetime.strptime(value, "%Y-%m-%d").date()
                return datetime.combine(d, time.min).replace(tzinfo=UTC)
            except Exception:
                raise ValueError("Invalid datetime format. Use ISO or YYYY-MM-DD.")
    raise ValueError("Unsupported datetime input type")


def _status_names(*statuses):
    return [s.name.upper() for s in statuses]


def find_available_slots(
    doctor_id: int,
    date,
    consultation_minutes: int = 30,
    session: Optional[Session] = None,
) -> List[datetime]:
    """
    Find available appointment slots for a doctor on a given date.
    
    Args:
        doctor_id: ID of the doctor
        date: Date to find slots for
        consultation_minutes: Duration of consultation in minutes (default: 30)
        session: Optional SQLAlchemy session. If not provided, creates a new one.
    
    Returns:
        List of available datetime slots
    """
    date = _ensure_date(date)
    weekday = date.weekday()
    
    # Use provided session or create new one
    if session is None:
        with get_session() as session:
            return _get_slots_from_db(doctor_id, date, weekday, consultation_minutes, session)
    else:
        return _get_slots_from_db(doctor_id, date, weekday, consultation_minutes, session)


def _get_slots_from_db(doctor_id, date, weekday, consultation_minutes, session):
    """Helper function to extract slots logic and reuse session"""
    availability_rows = session.query(DoctorAvailability).filter(
        and_(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.day_of_week == weekday,
            DoctorAvailability.is_available == True
        )
    ).all()
    if not availability_rows:
        return []
    start_of_day = datetime.combine(date, time.min).replace(tzinfo=UTC)
    next_day = start_of_day + timedelta(days=1)
    status_names = _status_names(
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CONFIRMED
    )
    existing_appointments = session.query(Appointment).filter(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_datetime >= start_of_day,
            Appointment.appointment_datetime < next_day,
            func.upper(Appointment.status).in_(status_names)
        )
    ).all()
    busy_intervals = []
    for appt in existing_appointments:
        start = appt.appointment_datetime
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        end = start + timedelta(
            minutes=getattr(appt, "duration_minutes", consultation_minutes)
        )
        busy_intervals.append((start, end))
    slots = set()
    increment = timedelta(minutes=SLOT_INCREMENT_MINUTES)
    for availability in availability_rows:
        start_dt = datetime.combine(date, availability.start_time).replace(tzinfo=UTC)
        end_dt = datetime.combine(date, availability.end_time).replace(tzinfo=UTC)
        current = start_dt
        while current + timedelta(minutes=consultation_minutes) <= end_dt:
            slot_end = current + timedelta(minutes=consultation_minutes)
            conflict = any(
                current < busy_end and slot_end > busy_start
                for busy_start, busy_end in busy_intervals
            )
            if not conflict:
                slots.add(current)
            current += increment
    return sorted(slots)


def evaluate_slots(
    patient_id: int,
    doctor_id: int,
    slots: List[datetime],
    session: Optional[Session] = None,
) -> List[Dict]:
    """
    Evaluate slots using ML model to predict no-show probability.
    
    Args:
        patient_id: ID of the patient
        doctor_id: ID of the doctor
        slots: List of available slots to evaluate
        session: Optional SQLAlchemy session. If not provided, creates a new one.
    
    Returns:
        List of evaluated slots with no-show probabilities
    """
    if session is None:
        with get_session() as session:
            return _evaluate_slots_with_session(patient_id, doctor_id, slots, session)
    else:
        return _evaluate_slots_with_session(patient_id, doctor_id, slots, session)


def _evaluate_slots_with_session(patient_id, doctor_id, slots, session):
    """Helper function to evaluate slots with provided session"""
    patient = session.query(Patient).filter_by(id=patient_id).first()
    doctor = session.query(Doctor).filter_by(id=doctor_id).first()
    if not patient or not doctor:
        return []
    predictor = get_predictor()
    evaluated = []
    for slot in slots:
        try:
            features = build_features(patient, doctor, slot, session=session)
            prediction = predictor.predict(features)
            probability = float(prediction.get("probability", 0.0))
        except Exception:
            logger.exception("ML prediction failed")
            probability = 0.5
        evaluated.append({
            "datetime": slot,
            "no_show_probability": probability
        })
    return sorted(evaluated, key=lambda x: x["no_show_probability"])


def book_appointment(
    patient_id: int,
    doctor_id: int,
    hospital_id: int,
    appointment_datetime,
    duration_minutes: int = 30,
    reason: Optional[str] = None,
    session: Optional[Session] = None,
) -> Dict:
    """
    Book an appointment for a patient with a doctor.
    
    Args:
        patient_id: ID of the patient
        doctor_id: ID of the doctor
        hospital_id: ID of the hospital
        appointment_datetime: Date and time of the appointment
        duration_minutes: Duration of the appointment in minutes (default: 30)
        reason: Reason for the appointment (optional)
        session: Optional SQLAlchemy session. If not provided, creates a new one.
    
    Returns:
        Dictionary with success status and result or error message
    """
    try:
        appointment_dt = _normalize_datetime_input(appointment_datetime)
        now = datetime.now(UTC)
        if appointment_dt <= now:
            return {"success": False, "message": "Cannot book in the past"}
        if appointment_dt > now + timedelta(days=MAX_BOOKING_DAYS_AHEAD):
            return {"success": False, "message": "Booking too far in future"}
        
        if session is None:
            with get_session() as session:
                return _book_appointment_with_session(
                    patient_id, doctor_id, hospital_id, appointment_dt, 
                    duration_minutes, reason, session
                )
        else:
            return _book_appointment_with_session(
                patient_id, doctor_id, hospital_id, appointment_dt, 
                duration_minutes, reason, session
            )
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception:
        logger.exception("Booking error")
        return {"success": False, "message": "Internal server error"}


def _book_appointment_with_session(patient_id, doctor_id, hospital_id, appointment_dt, duration_minutes, reason, session):
    """Helper function to book appointment with provided session"""
    patient = session.query(Patient).filter_by(id=patient_id).first()
    doctor = session.query(Doctor).filter_by(id=doctor_id).first()
    hospital = session.query(Hospital).filter_by(id=hospital_id).first()
    if not patient:
        return {"success": False, "message": "Patient not found"}
    if not doctor:
        return {"success": False, "message": "Doctor not found"}
    if not hospital:
        return {"success": False, "message": "Hospital not found"}
    
    available_slots = find_available_slots(
        doctor_id,
        appointment_dt.date(),
        consultation_minutes=duration_minutes,
        session=session
    )
    if appointment_dt.tzinfo is None:
        appointment_dt = appointment_dt.replace(tzinfo=UTC)
    else:
        appointment_dt = appointment_dt.astimezone(UTC)
    if appointment_dt not in available_slots:
        return {"success": False, "message": "Requested slot not available"}
    
    status_names = _status_names(
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CONFIRMED
    )
    existing = session.query(Appointment).filter(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_datetime == appointment_dt,
            func.upper(Appointment.status).in_(status_names)
        )
    ).first()
    if existing:
        return {"success": False, "message": "Slot already booked"}
    
    try:
        features = build_features(patient, doctor, appointment_dt, session=session)
        predictor = get_predictor()
        prediction = predictor.predict(features)
        probability = float(prediction.get("probability", 0.0))
    except Exception:
        logger.exception("Predictor failed during booking")
        probability = 0.5
    
    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        appointment_datetime=appointment_dt,
        duration_minutes=duration_minutes,
        status=AppointmentStatus.SCHEDULED,
        reason=reason,
        no_show_probability=probability
    )
    session.add(appointment)
    try:
        session.flush()
        appointment_id = appointment.id
        session.commit()
        return {
            "success": True,
            "appointment_id": appointment_id,
            "no_show_probability": probability
        }
    except IntegrityError:
        session.rollback()
        return {"success": False, "message": "Slot already booked"}
    except Exception:
        session.rollback()
        logger.exception("Booking error")
        return {"success": False, "message": "Internal server error"}


def cancel_appointment(appointment_id: int, session: Optional[Session] = None) -> Dict:
    """
    Cancel an appointment.
    
    Args:
        appointment_id: ID of the appointment to cancel
        session: Optional SQLAlchemy session. If not provided, creates a new one.
    
    Returns:
        Dictionary with success status and result or error message
    """
    if session is None:
        with get_session() as session:
            return _cancel_appointment_with_session(appointment_id, session)
    else:
        return _cancel_appointment_with_session(appointment_id, session)


def _cancel_appointment_with_session(appointment_id, session):
    """Helper function to cancel appointment with provided session"""
    appt = session.query(Appointment).filter_by(id=appointment_id).first()
    if not appt:
        return {"success": False, "message": "Appointment not found"}
    if appt.status in (
        AppointmentStatus.CANCELLED,
        AppointmentStatus.COMPLETED
    ):
        return {"success": False, "message": "Cannot cancel this appointment"}
    appt.status = AppointmentStatus.CANCELLED
    appt.updated_at = datetime.now(UTC)
    session.commit()
    return {"success": True, "message": "Appointment cancelled"}