# tests/test_validation.py
"""Tests for input validation module"""
import pytest
from backend.utils.validators import (
    validate_patient_input,
    validate_doctor_input,
    validate_appointment_booking,
    validate_slot_optimization,
    sanitize_error_message,
    PatientBase,
    DoctorBase,
    AppointmentBookRequest,
    SlotOptimizationRequest
)


class TestPatientValidation:
    """Test patient input validation"""
    
    def test_valid_patient_input(self):
        """Test valid patient input"""
        is_valid, error = validate_patient_input(
            first_name="John",
            last_name="Doe",
            date_of_birth="1990-01-15"
        )
        assert is_valid is True
        assert error == ""
    
    def test_invalid_first_name_empty(self):
        """Test invalid first name (empty)"""
        is_valid, error = validate_patient_input(
            first_name="",
            last_name="Doe",
            date_of_birth="1990-01-15"
        )
        assert is_valid is False
    
    def test_invalid_date_of_birth_future(self):
        """Test invalid date of birth (in future)"""
        is_valid, error = validate_patient_input(
            first_name="John",
            last_name="Doe",
            date_of_birth="2030-01-15"
        )
        assert is_valid is False


class TestDoctorValidation:
    """Test doctor input validation"""
    
    def test_valid_doctor_input(self):
        """Test valid doctor input"""
        is_valid, error = validate_doctor_input(
            first_name="Jane",
            last_name="Smith",
            hospital_id=1,
            consultation_duration=30
        )
        assert is_valid is True
        assert error == ""
    
    def test_invalid_hospital_id(self):
        """Test invalid hospital ID"""
        is_valid, error = validate_doctor_input(
            first_name="Jane",
            last_name="Smith",
            hospital_id=-1,
            consultation_duration=30
        )
        assert is_valid is False


class TestAppointmentValidation:
    """Test appointment booking validation"""
    
    def test_valid_appointment_booking(self):
        """Test valid appointment booking"""
        is_valid, error = validate_appointment_booking(
            doctor_id=1,
            datetime_str="2026-03-15T14:00:00",
            hospital_id=1,
            duration_minutes=30,
            reason="Checkup"
        )
        assert is_valid is True
        assert error == ""
    
    def test_invalid_doctor_id(self):
        """Test invalid doctor ID"""
        is_valid, error = validate_appointment_booking(
            doctor_id=-1,
            datetime_str="2026-03-15T14:00:00"
        )
        assert is_valid is False
    
    def test_invalid_datetime_past(self):
        """Test datetime in the past"""
        is_valid, error = validate_appointment_booking(
            doctor_id=1,
            datetime_str="2020-01-01T14:00:00"
        )
        assert is_valid is False


class TestSlotOptimizationValidation:
    """Test slot optimization validation"""
    
    def test_valid_slot_optimization(self):
        """Test valid slot optimization input"""
        is_valid, error = validate_slot_optimization(
            doctor_ids=[1, 2, 3],
            date="2026-03-15"
        )
        assert is_valid is True
        assert error == ""
    
    def test_invalid_doctor_ids_empty(self):
        """Test invalid doctor IDs (empty list)"""
        is_valid, error = validate_slot_optimization(
            doctor_ids=[],
            date="2026-03-15"
        )
        assert is_valid is False


class TestErrorSanitization:
    """Test error message sanitization"""
    
    def test_sanitize_unique_constraint_error(self):
        """Test sanitizing unique constraint error"""
        error = Exception("UNIQUE constraint failed: appointments.datetime")
        sanitized = sanitize_error_message(error)
        assert "UNIQUE" not in sanitized
        assert "This resource already exists" in sanitized
    
    def test_sanitize_foreign_key_error(self):
        """Test sanitizing foreign key error"""
        error = Exception("FOREIGN KEY constraint failed")
        sanitized = sanitize_error_message(error)
        assert "FOREIGN" not in sanitized
        assert "Related resource not found" in sanitized
    
    def test_sanitize_generic_error(self):
        """Test sanitizing generic error"""
        error = Exception("Some database error")
        sanitized = sanitize_error_message(error)
        assert "An error occurred" in sanitized