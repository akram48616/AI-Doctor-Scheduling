# tests/test_utilization.py
def test_utilization_report_smoke(seed_data, db_session_factory):
    from backend.services.utilization import utilization_report
    start = seed_data.query_date
    end = start
    report = utilization_report(start, end, session=db_session_factory())
    assert "utilization_percent" in report