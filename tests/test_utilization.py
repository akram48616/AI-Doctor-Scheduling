# tests/test_utilization.py
"""Tests for utilization service"""
import pytest
from datetime import datetime, timedelta


def test_utilization_report_smoke(seed_data, db_session_factory):
    """Test that utilization_report returns data without errors"""
    from backend.services.utilization import utilization_report
    
    # Get date range
    start = datetime.now() - timedelta(days=1)
    end = datetime.now() + timedelta(days=1)
    
    # Call utilization_report with the seed_data session to use same DB
    report = utilization_report(start, end, session=seed_data)
    
    # Should return a dict with utilization data
    assert isinstance(report, dict)
    assert "utilization_percent" in report or "success" in report