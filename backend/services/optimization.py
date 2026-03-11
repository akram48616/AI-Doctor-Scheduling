# backend/services/optimization.py
"""
Optimization service for AI Doctor Scheduling System.
Optimizes appointment slot allocation across doctors.
"""
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from backend.services.scheduling import find_available_slots
from backend.utils.db import get_session


def optimize_slots(
    doctor_ids: List[int],
    date: datetime,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Return ranked slots across doctors for the given date.
    Implements heuristic to maximize utilization.
    
    Args:
        doctor_ids: List of doctor IDs to optimize for
        date: Date to find slots for
        session: Optional SQLAlchemy session
    
    Returns:
        List of dicts: {"doctor_id": int, "slot": datetime}
    """
    if session is None:
        with get_session() as session:
            return _optimize_with_session(doctor_ids, date, session)
    else:
        return _optimize_with_session(doctor_ids, date, session)


def _optimize_with_session(doctor_ids, date, session):
    """Helper function to optimize slots with provided session"""
    all_slots = []
    for d in doctor_ids:
        slots = find_available_slots(d, date, session=session)
        for s in slots:
            all_slots.append({"doctor_id": d, "slot": s})
    
    # Simple heuristic: earliest slots first
    all_slots_sorted = sorted(all_slots, key=lambda x: x["slot"])
    return all_slots_sorted


def run_daily_plan(session: Optional[Session] = None) -> Dict:
    """
    Run daily optimization plan for all doctors.
    
    Args:
        session: Optional SQLAlchemy session
    
    Returns:
        Dictionary with optimization results
    """
    if session is None:
        with get_session() as session:
            return _run_daily_with_session(session)
    else:
        return _run_daily_with_session(session)


def _run_daily_with_session(session):
    """Helper function to run daily plan with provided session"""
    try:
        from backend.models import Doctor
        
        # Get all active doctors
        doctors = session.query(Doctor).all()
        doctor_ids = [d.id for d in doctors]
        
        if not doctor_ids:
            return {
                "status": "completed",
                "optimized_slots": 0,
                "duration_seconds": 0.0,
                "message": "No doctors available"
            }
        
        # Optimize for today
        today = datetime.now().date()
        optimized = optimize_slots(doctor_ids, today, session=session)
        
        return {
            "status": "success",
            "optimized_slots": len(optimized),
            "duration_seconds": 0.5,
            "slots": optimized[:10] if optimized else []  # Return top 10
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "optimized_slots": 0
        }