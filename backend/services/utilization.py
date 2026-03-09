# backend/services/utilization.py
from datetime import datetime
from typing import Dict
from backend.utils.db import get_session
from backend.models import Appointment, DoctorAvailability
from sqlalchemy import func

def utilization_report(start_date: datetime, end_date: datetime, session=None) -> Dict:
    """
    Aggregate appointments and availability to compute utilization metrics.
    Returns a small summary dict suitable for dashboards.
    """
    close_session = False
    if session is None:
        session = get_session().__enter__()
        close_session = True
    try:
        booked_slots = session.query(func.count(Appointment.id)).filter(
            Appointment.appointment_datetime >= start_date,
            Appointment.appointment_datetime < end_date
        ).scalar() or 0
        avail_rows = session.query(DoctorAvailability).all()
        total_slots = max(1, len(avail_rows) * 8)  # placeholder estimate
        utilization_percent = (booked_slots / total_slots) * 100 if total_slots > 0 else 0.0
        return {"utilization_percent": utilization_percent, "total_slots": total_slots, "booked_slots": booked_slots}
    finally:
        if close_session:
            get_session().__exit__(None, None, None)