# tests/test_optimization.py
"""Tests for optimization service"""
import pytest
from datetime import datetime, timedelta


def test_optimize_slots_smoke(seed_data, db_session_factory):
    """Test that optimize_slots returns slots without errors"""
    from backend.services.optimization import optimize_slots
    
    # Get tomorrow's date from seed data
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    
    # Call optimize_slots with correct parameters
    slots = optimize_slots([1], tomorrow)
    
    # Should return a list (may be empty if no availability)
    assert isinstance(slots, list)