# backend/services/scheduling.py

import logging
from datetime import datetime, timedelta, time, timezone
from typing import List, Dict, Optional, Any
from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError

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


# ==========================================================
# Helpers
# ==========================================================

def _ensure_date(date_input: Any):
    if isinstance(date_input, str):
        try:
            return datetime.strptime(date_input, "%Y-%m-%d").date()
        except Exception:
            return datetime.fromisoformat(date_input).date()

    if isinstance(date_input, datetime):
        return date_input.date()

    return date_input


def _normalize_datetime_input(value: Any) -> datetime:
    if value is None:
        raise ValueError("appointment_datetime is required")

    if isinstance(value, datetime):
        dt = value.replace(microsecond=0)
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value).replace(microsecond=0)
    else:
        raise ValueError("Unsupported datetime input type")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)

    return dt


def _status_names(*statuses):
    return [s.name.upper() for s in statuses]


# ==========================================================
# Slot Finder
# ==========================================================

def find_available_slots(
    doctor_id: int,
    date,
    consultation_minutes: int = 30,
) -> List[datetime]:

    date = _ensure_date(date)
    weekday = date.weekday()

    with get_session() as session:

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

        active_status = _status_names(
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CONFIRMED
        )

        existing = session.query(Appointment).filter(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_datetime >= start_of_day,
                Appointment.appointment_datetime < next_day,
                func.upper(Appointment.status).in_(active_status)
            )
        ).all()

        busy = []
        for appt in existing:
            start = appt.appointment_datetime
            if start.tzinfo is None:
                start = start.replace(tzinfo=UTC)

            end = start + timedelta(minutes=appt.duration_minutes)
            busy.append((start, end))

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
                    for busy_start, busy_end in busy
                )

                if not conflict:
                    slots.add(current)

                current += increment

        return sorted(slots)


# ==========================================================
# Booking
# ==========================================================

def book_appointment(
    patient_id: int,
    doctor_id: int,
    hospital_id: int,
    appointment_datetime,
    duration_minutes: int = 30,
    reason: Optional[str] = None,
) -> Dict:

    try:
        appointment_dt = _normalize_datetime_input(appointment_datetime)
        now = datetime.now(UTC)

        if appointment_dt <= now:
            return {"success": False, "message": "Cannot book in the past"}

        if appointment_dt > now + timedelta(days=MAX_BOOKING_DAYS_AHEAD):
            return {"success": False, "message": "Booking too far in future"}

        with get_session() as session:

            patient = session.query(Patient).filter_by(id=patient_id).first()
            doctor = session.query(Doctor).filter_by(id=doctor_id).first()
            hospital = session.query(Hospital).filter_by(id=hospital_id).first()

            if not patient:
                return {"success": False, "message": "Patient not found"}
            if not doctor:
                return {"success": False, "message": "Doctor not found"}
            if not hospital:
                return {"success": False, "message": "Hospital not found"}

            # ML Prediction
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
                session.flush()  # triggers unique constraint

                appointment_id = appointment.id  # safe BEFORE commit

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

    except Exception as e:
        logger.exception("Booking error")
        return {"success": False, "message": str(e)}


# ==========================================================
# Cancel
# ==========================================================

def cancel_appointment(appointment_id: int) -> Dict:

    with get_session() as session:

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
