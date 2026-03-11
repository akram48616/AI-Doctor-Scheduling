# backend/services/utilization.py
"""
Utilization service for computing doctor and hospital utilization metrics.
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.utils.db import get_session
from backend.models import Appointment, DoctorAvailability, Doctor, AppointmentStatus


def utilization_report(start_date: datetime, end_date: datetime, session: Optional[Session] = None) -> Dict:
    """
    Aggregate appointments and availability to compute utilization metrics.
    Returns a small summary dict suitable for dashboards.
    
    Args:
        start_date: Start date for utilization calculation
        end_date: End date for utilization calculation
        session: Optional SQLAlchemy session
    
    Returns:
        Dictionary with utilization metrics
    """
    if session is None:
        with get_session() as session:
            return _utilization_report_with_session(start_date, end_date, session)
    else:
        return _utilization_report_with_session(start_date, end_date, session)


def _utilization_report_with_session(start_date, end_date, session):
    """Helper function to generate report with session"""
    booked_slots = session.query(func.count(Appointment.id)).filter(
        Appointment.appointment_datetime >= start_date,
        Appointment.appointment_datetime < end_date
    ).scalar() or 0
    
    avail_rows = session.query(DoctorAvailability).all()
    total_slots = max(1, len(avail_rows) * 8)  # placeholder estimate
    utilization_percent = (booked_slots / total_slots) * 100 if total_slots > 0 else 0.0
    
    return {
        "success": True,
        "utilization_percent": utilization_percent,
        "total_slots": total_slots,
        "booked_slots": booked_slots
    }


def compute_doctor_utilization(doctor_id: int, session: Optional[Session] = None) -> Dict:
    """
    Compute utilization metrics for a specific doctor.
    
    Args:
        doctor_id: ID of the doctor
        session: Optional SQLAlchemy session. If not provided, creates a new one.
    
    Returns:
        Dictionary with doctor's utilization metrics
    """
    if session is None:
        with get_session() as session:
            return _compute_doctor_utilization_with_session(doctor_id, session)
    else:
        return _compute_doctor_utilization_with_session(doctor_id, session)


def _compute_doctor_utilization_with_session(doctor_id, session):
    """Helper function to compute utilization with session"""
    doctor = session.query(Doctor).filter_by(id=doctor_id).first()
    if not doctor:
        return {"success": False, "message": "Doctor not found"}
    
    # Get all appointments for this doctor
    appointments = session.query(Appointment).filter_by(doctor_id=doctor_id).all()
    
    # Calculate booked hours
    booked_minutes = 0
    for appt in appointments:
        if appt.status not in (AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW):
            booked_minutes += appt.duration_minutes or 30
    
    booked_hours = booked_minutes / 60.0
    
    # Get doctor availability to estimate available hours
    # Assume standard 8-hour workday
    available_hours = 8 * 5  # 40 hours per week (5 days)
    
    utilization_rate = (booked_hours / available_hours) if available_hours > 0 else 0.0
    
    # Calculate no-show risk (average no_show_probability of all appointments)
    no_show_risk = 0.0
    if appointments:
        total_prob = sum(appt.no_show_probability or 0 for appt in appointments)
        no_show_risk = total_prob / len(appointments)
    
    return {
        "success": True,
        "doctor_id": doctor_id,
        "doctor_name": f"{doctor.first_name} {doctor.last_name}",
        "available_hours": available_hours,
        "booked_hours": round(booked_hours, 2),
        "utilization_rate": round(utilization_rate, 2),
        "no_show_risk": round(no_show_risk, 2),
        "total_appointments": len(appointments)
    }


def generate_report(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, session: Optional[Session] = None) -> Dict:
    """
    Generate a comprehensive utilization report.
    
    Args:
        start_date: Start date for report (defaults to 30 days ago)
        end_date: End date for report (defaults to today)
        session: Optional SQLAlchemy session
    
    Returns:
        Dictionary with comprehensive utilization report
    """
    if start_date is None:
        start_date = datetime.now() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.now() + timedelta(days=1)
    
    if session is None:
        with get_session() as session:
            return _generate_report_with_session(start_date, end_date, session)
    else:
        return _generate_report_with_session(start_date, end_date, session)


def _generate_report_with_session(start_date, end_date, session):
    """Helper function to generate report with session"""
    # Get overall utilization
    overall = _utilization_report_with_session(start_date, end_date, session)
    
    # Get per-doctor utilization
    doctors = session.query(Doctor).all()
    doctor_utilization = []
    for doctor in doctors:
        doc_util = _compute_doctor_utilization_with_session(doctor.id, session)
        if doc_util.get("success"):
            doctor_utilization.append(doc_util)
    
    return {
        "success": True,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "overall_utilization": overall,
        "by_doctor": doctor_utilization,
        "total_doctors": len(doctors)
    }