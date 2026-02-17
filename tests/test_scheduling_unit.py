"""
Scheduling service: slot generation, evaluation (no-show predictor), booking and cancellation.

This module is written to be test-friendly:
- All public functions accept an optional `session` parameter (SQLAlchemy Session).
- If `session` is None, a module-level `get_session()` will create one from env var.
- Tests can override `scheduling.get_session` to inject test sessions.
- ML predictor is read via `ml_model.get_predictor()` if available, otherwise `ml_model._MODEL_SINGLETON`.
"""

from __future__ import annotations

import os
from datetime import datetime, date, time, timedelta, timezone
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy import and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine

from backend.models import (
    Doctor,
    DoctorAvailability,
    Appointment,
    AppointmentStatus,
    Patient,
    Hospital,
)

from backend.services import ml_model

UTC = timezone.utc

# ---------------------------------------------------------------------
# Database session factory (used when caller doesn't provide session)
# ---------------------------------------------------------------------
_DATABASE_URL = os.getenv("TEST_MYSQL_URL") or os.getenv("DATABASE_URL") or os.getenv(
    "SQLALCHEMY_DATABASE_URI"
)
# Fallback to a local sqlite file if nothing provided (safe default)
if not _DATABASE_URL:
    _DATABASE_URL = "sqlite:///./dev_db.sqlite3"

_ENGINE = None
_SessionFactory = None


def _ensure_session_factory():
    global _ENGINE, _SessionFactory
    if _SessionFactory is None:
        _ENGINE = create_engine(_DATABASE_URL, echo=False, pool_pre_ping=True)
        _SessionFactory = sessionmaker(bind=_ENGINE)
    return _SessionFactory


def get_session() -> Session:
    """
    Return a new SQLAlchemy Session.
    Tests may override this function (e.g., scheduling.get_session = lambda: test_session).
    """
    factory = _ensure_session_factory()
    return factory()


# ---------------------------------------------------------------------
# ML predictor helper
# ---------------------------------------------------------------------
def _get_predictor():
    """
    Return a predictor object with a .predict(features: dict) -> dict interface.
    Tests set ml_model._MODEL_SINGLETON or provide ml_model.get_predictor().
    """
    if hasattr(ml_model, "get_predictor"):
        try:
            p = ml_model.get_predictor()
            if p is not None:
                return p
        except Exception:
            pass
    # fallback to internal singleton
    if getattr(ml_model, "_MODEL_SINGLETON", None) is not None:
        return ml_model._MODEL_SINGLETON
    # If no predictor available, return a dummy predictor that returns neutral probability
    class _Fallback:
        def predict(self, features: dict) -> dict:
            return {"probability": 0.0, "label": 0}

    return _Fallback()


# ---------------------------------------------------------------------
# Utility functions for datetime handling
# ---------------------------------------------------------------------
def _ensure_date(d: Any) -> date:
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        # Accept ISO date string
        return datetime.fromisoformat(d).date()
    raise ValueError("Unsupported date input")


def _normalize_datetime_input(dt_in: Any) -> datetime:
    """
    Accepts:
      - datetime (naive or tz-aware)
      - ISO datetime string "YYYY-MM-DDTHH:MM:SS"
      - ISO date string "YYYY-MM-DD" (interpreted as midnight)
    Returns timezone-aware datetime in UTC.
    """
    if isinstance(dt_in, datetime):
        dt = dt_in
    elif isinstance(dt_in, str):
        # If only date provided, parse as midnight
        if "T" not in dt_in:
            dt = datetime.fromisoformat(dt_in)
        else:
            dt = datetime.fromisoformat(dt_in)
    else:
        raise ValueError("Unsupported datetime input")

    # If naive, assume local naive means UTC for consistency in scheduling
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt


# ---------------------------------------------------------------------
# Slot generation
# ---------------------------------------------------------------------
def find_available_slots(
    doctor_id: int,
    date_or_iso: Any,
    consultation_minutes: int = 30,
    session: Optional[Session] = None,
) -> List[datetime]:
    """
    Return list of timezone-aware UTC datetimes representing available slot start times
    for the given doctor on the given date.
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True

    try:
        target_date = _ensure_date(date_or_iso)
        weekday = target_date.weekday()  # Monday=0

        # Fetch availability rows for doctor and weekday
        avails = (
            session.query(DoctorAvailability)
            .filter(
                DoctorAvailability.doctor_id == doctor_id,
                DoctorAvailability.day_of_week == weekday,
                DoctorAvailability.is_available == True,
            )
            .all()
        )

        slots: List[datetime] = []
        for a in avails:
            # Build start and end datetimes in UTC for the target date
            start_dt = datetime.combine(target_date, a.start_time).replace(tzinfo=UTC)
            end_dt = datetime.combine(target_date, a.end_time).replace(tzinfo=UTC)

            # Generate slots
            cur = start_dt
            delta = timedelta(minutes=consultation_minutes)
            while cur + timedelta(seconds=1) <= end_dt:
                # Check if slot conflicts with existing confirmed appointments
                overlapping = (
                    session.query(Appointment)
                    .filter(
                        Appointment.doctor_id == doctor_id,
                        Appointment.status == AppointmentStatus.CONFIRMED,
                        # appointment start < slot_end AND appointment end > slot_start
                        and_(
                            Appointment.appointment_datetime < (cur + delta),
                            (Appointment.appointment_datetime + func.cast(Appointment.duration_minutes, type_=type(consultation_minutes))) > cur,
                        ),
                    )
                    .count()
                )
                # Note: Some DBs don't support arithmetic on columns; if your Appointment model stores end time, use that.
                if overlapping == 0:
                    slots.append(cur)
                cur = cur + delta
        # Deduplicate and sort
        slots = sorted(list({s: None for s in slots}.keys()))
        return slots
    finally:
        if close_session:
            session.close()


# ---------------------------------------------------------------------
# Slot evaluation using ML predictor
# ---------------------------------------------------------------------
def evaluate_slots(
    patient_id: int,
    doctor_id: int,
    slots: List[datetime],
    session: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """
    For each slot, compute features and call predictor.predict(features).
    Returns list of dicts: {"slot": datetime, "no_show_probability": float, ...}
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True

    try:
        predictor = _get_predictor()
        results: List[Dict[str, Any]] = []

        # Minimal patient/doctor info for features (optional)
        patient = session.query(Patient).filter_by(id=patient_id).first()
        doctor = session.query(Doctor).filter_by(id=doctor_id).first()

        now = datetime.now(UTC)
        for s in slots:
            lead_time = s - now
            lead_days = max(0, lead_time.total_seconds() / 86400.0)
            features = {
                "lead_time_days": int(lead_days),
                "doctor_id": doctor_id,
                "patient_id": patient_id,
                # Add more features if your model expects them
            }
            pred = predictor.predict(features)
            prob = None
            if isinstance(pred, dict):
                prob = float(pred.get("probability", 0.0))
            else:
                # If predictor returns a scalar probability
                try:
                    prob = float(pred)
                except Exception:
                    prob = 0.0
            results.append({"slot": s, "no_show_probability": prob, "features": features})
        return results
    finally:
        if close_session:
            session.close()


# ---------------------------------------------------------------------
# Booking and cancellation
# ---------------------------------------------------------------------
def book_appointment(
    patient_id: int,
    doctor_id: int,
    hospital_id: int,
    appointment_datetime: Any,
    duration_minutes: int = 30,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Attempt to book an appointment. Returns dict with success flag and data/message.
    Ensures double-book protection using DB unique constraints or transactional checks.
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True

    try:
        appt_dt = _normalize_datetime_input(appointment_datetime)

        # Basic validation: patient/doctor/hospital exist
        patient = session.query(Patient).filter_by(id=patient_id).first()
        doctor = session.query(Doctor).filter_by(id=doctor_id).first()
        hospital = session.query(Hospital).filter_by(id=hospital_id).first()
        if not (patient and doctor and hospital):
            return {"success": False, "message": "Invalid patient/doctor/hospital id"}

        # Check doctor availability for that day
        weekday = appt_dt.date().weekday()
        avail = (
            session.query(DoctorAvailability)
            .filter_by(doctor_id=doctor_id, day_of_week=weekday, is_available=True)
            .first()
        )
        if not avail:
            return {"success": False, "message": "Doctor not available on requested date"}

        # Check slot falls within availability window
        start_time = datetime.combine(appt_dt.date(), avail.start_time).replace(tzinfo=UTC)
        end_time = datetime.combine(appt_dt.date(), avail.end_time).replace(tzinfo=UTC)
        if not (start_time <= appt_dt < end_time):
            return {"success": False, "message": "Requested slot not within availability"}

        # Check for overlapping confirmed appointments
        slot_end = appt_dt + timedelta(minutes=duration_minutes)
        overlapping = (
            session.query(Appointment)
            .filter(
                Appointment.doctor_id == doctor_id,
                Appointment.status == AppointmentStatus.CONFIRMED,
                and_(
                    Appointment.appointment_datetime < slot_end,
                    (Appointment.appointment_datetime + func.cast(Appointment.duration_minutes, type_=type(duration_minutes))) > appt_dt,
                ),
            )
            .with_for_update(read=True)
            .count()
        )
        if overlapping > 0:
            return {"success": False, "message": "Slot already booked"}

        # Create appointment
        appt = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            hospital_id=hospital_id,
            appointment_datetime=appt_dt,
            duration_minutes=duration_minutes,
            status=AppointmentStatus.CONFIRMED,
            created_at=datetime.now(UTC),
        )
        session.add(appt)
        try:
            session.commit()
        except IntegrityError as e:
            session.rollback()
            return {"success": False, "message": "Database integrity error (possible double-book)"}
        return {"success": True, "data": {"appointment_id": appt.id}}
    except Exception as exc:
        # Rollback if we created the session or if an error occurred
        try:
            session.rollback()
        except Exception:
            pass
        return {"success": False, "message": f"Error booking appointment: {exc}"}
    finally:
        if close_session:
            session.close()


def cancel_appointment(appointment_id: int, session: Optional[Session] = None) -> Dict[str, Any]:
    """
    Cancel an appointment by setting its status to CANCELLED.
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True

    try:
        appt = session.query(Appointment).filter_by(id=appointment_id).first()
        if not appt:
            return {"success": False, "message": "Appointment not found"}
        if appt.status == AppointmentStatus.CANCELLED:
            return {"success": False, "message": "Appointment already cancelled"}
        appt.status = AppointmentStatus.CANCELLED
        appt.cancelled_at = datetime.now(UTC)
        session.add(appt)
        session.commit()
        return {"success": True}
    except Exception as exc:
        try:
            session.rollback()
        except Exception:
            pass
        return {"success": False, "message": f"Error cancelling appointment: {exc}"}
    finally:
        if close_session:
            session.close()
