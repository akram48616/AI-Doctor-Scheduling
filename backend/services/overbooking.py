# backend/services/overbooking.py
from typing import Dict

def compute_overbooking_allowance(no_show_probability: float, policy: Dict) -> int:
    """
    Compute allowed extra bookings for a slot based on policy.
    policy example: {"max_overbook": 2, "scale": 1.0}
    """
    scale = float(policy.get("scale", 1.0))
    max_overbook = int(policy.get("max_overbook", 1))
    allowance = int(no_show_probability * scale)
    return min(allowance, max_overbook)