# tests/test_overbooking.py
def test_overbooking_allowance_basic():
    from backend.services.overbooking import compute_overbooking_allowance
    allowance = compute_overbooking_allowance(0.5, {"scale":2.0, "max_overbook":2})
    assert 0 <= allowance <= 2