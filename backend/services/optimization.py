# backend/services/optimization.py
from typing import List, Dict
from datetime import datetime
from backend.services.scheduling import find_available_slots
from backend.utils.db import get_session

def optimize_slots(doctor_ids: List[int], date: datetime, session=None) -> List[Dict]:
    """
    Return ranked slots across doctors for the given date.
    Placeholder: implement LP or heuristic to maximize utilization.
    Returns list of dicts: {"doctor_id": int, "slot": datetime}
    """
    close_session = False
    if session is None:
        session = get_session().__enter__()
        close_session = True
    try:
        all_slots = []
        for d in doctor_ids:
            slots = find_available_slots(d, date, session=session)
            for s in slots:
                all_slots.append({"doctor_id": d, "slot": s})
        # Simple heuristic: earliest slots first
        all_slots_sorted = sorted(all_slots, key=lambda x: x["slot"])
        return all_slots_sorted
    finally:
        if close_session:
            get_session().__exit__(None, None, None)