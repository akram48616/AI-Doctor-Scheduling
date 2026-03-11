# File path: backend/services/scheduling.py
# This file contains appointment scheduling logic with transaction management

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
    """Convert various date input formats to date object."""
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
    """Convert various datetime input formats to UTC datetime object."""
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
    """Convert status enums to uppercase names for SQL queries."""
    return [s.name.upper() for s in statuses]


# ============================================================================
# Patient Scheduling
# ============================================================================

def get_appointments_by_patient(patient_id: int, session: Optional[Session] = None) -> Dict:
    """
    Get all appointments for a patient.
    
    Args:
        patient_id: ID of the patient
        session: Optional SQLAlchemy session
    
    Returns:
        Dictionary with patient appointments
    """
    if session is None:
        with get_session() as session:
            return _get_appointments_with_session(patient_id, session)
    else:
        return _get_appointments_with_session(patient_id, session)


def _get_appointments_with_session(patient_id, session):
    """Helper function to get appointments with provided session"""
    patient = session.query(Patient).filter_by(id=patient_id).first()
    if not patient:
        return {"success": False, "message": "Patient not found"}
    
    appointments = session.query(Appointment).filter_by(patient_id=patient_id).all()
    
    return {
        "success": True,
        "patient_id": patient_id,
        "appointments": [
            {
                "appointment_id": appt.id,
                "doctor_id": appt.doctor_id,
                "hospital_id": appt.hospital_id,
                "appointment_datetime": appt.appointment_datetime.isoformat() if appt.appointment_datetime else None,
                "duration_minutes": appt.duration_minutes,
                "status": appt.status.name if appt.status else None,
                "reason": appt.reason,
                "no_show_probability": appt.no_show_probability
            }
            for appt in appointments
        ],
        "total": len(appointments)
    }


def book_appointment(
    patient_id: int,
    doctor_id: int,
    appointment_datetime,
    hospital_id: int = None,
    duration_minutes: int = 30,
    reason: Optional[str] = None,
    session: Optional[Session] = None,
) -> Dict:
    """
    Book an appointment for a patient with a doctor.
    
    TRANSACTION GUARANTEED: Uses database locking to prevent race conditions.
    
    Args:
        patient_id: ID of the patient
        doctor_id: ID of the doctor
        appointment_datetime: Date and time of the appointment
        hospital_id: ID of the hospital (optional)
        duration_minutes: Duration of the appointment in minutes
        reason: Reason for the appointment (optional)
        session: Optional SQLAlchemy session
    
    Returns:
        Dictionary with success status and result or error message
    """
    try:
        appointment_dt = _normalize_datetime_input(appointment_datetime)
        now = datetime.now(UTC)
        
        # Validation before transaction
        if appointment_dt <= now:
            return {"success": False, "message": "Cannot book in the past"}
        if appointment_dt > now + timedelta(days=MAX_BOOKING_DAYS_AHEAD):
            return {"success": False, "message": "Booking too far in future"}
        
        if session is None:
            with get_session() as session:
                return _book_appointment_with_transaction(
                    patient_id, doctor_id, appointment_dt, 
                    hospital_id, duration_minutes, reason, session
                )
        else:
            return _book_appointment_with_transaction(
                patient_id, doctor_id, appointment_dt, 
                hospital_id, duration_minutes, reason, session
            )
    except ValueError as ve:
        return {"success": False, "message": str(ve)}
    except Exception:
        logger.exception("Booking error")
        return {"success": False, "message": "Internal server error"}


def _book_appointment_with_transaction(patient_id, doctor_id, appointment_dt, hospital_id, duration_minutes, reason, session):
    """Execute booking within a transaction with row-level locking."""
    try:
        # Lock doctor and validate
        doctor = session.query(Doctor).with_for_update().filter_by(id=doctor_id).first()
        if not doctor:
            session.rollback()
            return {"success": False, "message": "Doctor not found"}
        
        # Validate patient
        patient = session.query(Patient).filter_by(id=patient_id).first()
        if not patient:
            session.rollback()
            return {"success": False, "message": "Patient not found"}
        
        # Determine hospital
        if hospital_id is None:
            hospital_id = doctor.hospital_id
        
        hospital = session.query(Hospital).filter_by(id=hospital_id).first()
        if not hospital:
            session.rollback()
            return {"success": False, "message": "Hospital not found"}
        
        # Check availability
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
            session.rollback()
            return {"success": False, "message": "Requested slot not available"}
        
        # Double-check for concurrent bookings
        status_names = _status_names(
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CONFIRMED
        )
        
        existing = session.query(Appointment).with_for_update().filter(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_datetime == appointment_dt,
                func.upper(Appointment.status).in_(status_names)
            )
        ).first()
        
        if existing:
            session.rollback()
            return {"success": False, "message": "Slot already booked (just booked by another user)"}
        
        # ML prediction
        try:
            features = build_features(patient, doctor, appointment_dt, session=session)
            predictor = get_predictor()
            prediction = predictor.predict(features)
            probability = float(prediction.get("probability", 0.0))
        except Exception:
            logger.exception("Predictor failed during booking")
            probability = 0.5
        
        # Create appointment
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
            
            logger.info(f"Appointment {appointment_id} booked successfully for patient {patient_id}")
            
            return {
                "success": True,
                "appointment_id": appointment_id,
                "no_show_probability": probability
            }
        except IntegrityError as ie:
            session.rollback()
            logger.warning(f"Integrity constraint violated: {ie}")
            return {"success": False, "message": "Slot already booked (database constraint)"}
    
    except Exception as e:
        session.rollback()
        logger.exception("Transaction error during booking")
        return {"success": False, "message": "Transaction failed: " + str(e)}


# ============================================================================
# Doctor Scheduling
# ============================================================================

def get_schedule_by_doctor(doctor_id: int, session: Optional[Session] = None) -> Dict:
    """Get schedule for a doctor."""
    if session is None:
        with get_session() as session:
            return _get_schedule_with_session(doctor_id, session)
    else:
        return _get_schedule_with_session(doctor_id, session)


def _get_schedule_with_session(doctor_id, session):
    """Helper to get doctor schedule with session"""
    doctor = session.query(Doctor).filter_by(id=doctor_id).first()
    if not doctor:
        return {"success": False, "message": "Doctor not found"}
    
    appointments = session.query(Appointment).filter_by(doctor_id=doctor_id).all()
    
    return {
        "success": True,
        "doctor_id": doctor_id,
        "appointments": [
            {
                "appointment_id": appt.id,
                "patient_id": appt.patient_id,
                "appointment_datetime": appt.appointment_datetime.isoformat() if appt.appointment_datetime else None,
                "status": appt.status.name if appt.status else None
            }
            for appt in appointments
        ],
        "total": len(appointments)
    }


# ============================================================================
# Slot Management
# ============================================================================

def find_available_slots(
    doctor_id: int,
    date,
    consultation_minutes: int = 30,
    session: Optional[Session] = None,
) -> List[datetime]:
    """Find available appointment slots for a doctor on a given date."""
    date = _ensure_date(date)
    weekday = date.weekday()
    
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
    """Evaluate slots using ML model to predict no-show probability."""
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


# ============================================================================
# Appointment Management
# ============================================================================

def cancel_appointment(appointment_id: int, session: Optional[Session] = None) -> Dict:
    """Cancel an appointment."""
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