# tests/test_optimization.py
def test_optimize_slots_smoke(seed_data, db_session_factory):
    from backend.services.optimization import optimize_slots
    slots = optimize_slots([1], seed_data.query_date, session=db_session_factory())
    assert isinstance(slots, list)