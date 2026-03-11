# backend/utils/validators.py
"""
Input validation module using Pydantic V2 for request schema validation.
Provides type-safe validation for all API inputs.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Base Models
# ============================================================================

class PatientBase(BaseModel):
    """Base patient validation schema"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: str = Field(..., description="ISO format date (YYYY-MM-DD)")
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v):
        """Sanitize names - remove special characters"""
        if not v.replace(' ', '').isalpha():
            raise ValueError("Names must contain only letters and spaces")
        return v.strip()
    
    @field_validator('date_of_birth')
    @classmethod
    def validate_date_of_birth(cls, v):
        """Validate date format"""
        try:
            dob = datetime.fromisoformat(v).date()
            if dob > datetime.now().date():
                raise ValueError("Date of birth cannot be in the future")
            return v
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD")


class DoctorBase(BaseModel):
    """Base doctor validation schema"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    hospital_id: int = Field(..., gt=0)
    consultation_duration: int = Field(default=30, ge=15, le=120)
    
    @field_validator('first_name', 'last_name')
    @classmethod
    def validate_name(cls, v):
        """Sanitize names"""
        if not v.replace(' ', '').isalpha():
            raise ValueError("Names must contain only letters and spaces")
        return v.strip()


class HospitalBase(BaseModel):
    """Base hospital validation schema"""
    name: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None)
    phone: Optional[str] = Field(None)
    email: Optional[str] = Field(None)


# ============================================================================
# Appointment Schemas
# ============================================================================

class AppointmentBookRequest(BaseModel):
    """Schema for booking an appointment"""
    doctor_id: int = Field(..., gt=0, description="Doctor ID")
    datetime: str = Field(..., description="ISO format datetime (YYYY-MM-DDTHH:MM:SS)")
    hospital_id: Optional[int] = Field(None, gt=0, description="Hospital ID (optional)")
    duration_minutes: Optional[int] = Field(30, ge=15, le=120)
    reason: Optional[str] = Field(None, max_length=500)
    
    @field_validator('datetime')
    @classmethod
    def validate_datetime(cls, v):
        """Validate ISO format datetime"""
        try:
            dt = datetime.fromisoformat(v)
            if dt < datetime.now():
                raise ValueError("Appointment time cannot be in the past")
            return v
        except ValueError:
            raise ValueError("Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
    
    @field_validator('reason')
    @classmethod
    def sanitize_reason(cls, v):
        """Sanitize reason text"""
        if v:
            # Remove potential HTML/script tags
            v = v.replace('<', '&lt;').replace('>', '&gt;')
        return v


class AppointmentCancelRequest(BaseModel):
    """Schema for cancelling an appointment"""
    appointment_id: int = Field(..., gt=0)


class SlotOptimizationRequest(BaseModel):
    """Schema for requesting optimized slots"""
    doctor_ids: list = Field(..., description="List of doctor IDs")
    date: str = Field(..., description="ISO format date (YYYY-MM-DD)")
    
    @field_validator('doctor_ids')
    @classmethod
    def validate_doctor_ids(cls, v):
        """Validate doctor ID list"""
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("doctor_ids must be a non-empty list")
        if not all(isinstance(id, int) and id > 0 for id in v):
            raise ValueError("All doctor IDs must be positive integers")
        return v
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v):
        """Validate date format"""
        try:
            dt = datetime.fromisoformat(v).date()
            return v
        except ValueError:
            raise ValueError("Invalid date format. Use YYYY-MM-DD")


# ============================================================================
# Validation Functions
# ============================================================================

def validate_patient_input(first_name: str, last_name: str, date_of_birth: str) -> tuple:
    """
    Validate patient input.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        PatientBase(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth
        )
        return True, ""
    except Exception as e:
        errors = str(e)
        return False, errors


def validate_doctor_input(first_name: str, last_name: str, hospital_id: int, 
                         consultation_duration: int = 30) -> tuple:
    """
    Validate doctor input.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        DoctorBase(
            first_name=first_name,
            last_name=last_name,
            hospital_id=hospital_id,
            consultation_duration=consultation_duration
        )
        return True, ""
    except Exception as e:
        errors = str(e)
        return False, errors


def validate_appointment_booking(doctor_id: int, datetime_str: str, 
                                hospital_id: Optional[int] = None,
                                duration_minutes: Optional[int] = None,
                                reason: Optional[str] = None) -> tuple:
    """
    Validate appointment booking input.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        AppointmentBookRequest(
            doctor_id=doctor_id,
            datetime=datetime_str,
            hospital_id=hospital_id,
            duration_minutes=duration_minutes,
            reason=reason
        )
        return True, ""
    except Exception as e:
        errors = str(e)
        return False, errors


def validate_slot_optimization(doctor_ids: list, date: str) -> tuple:
    """
    Validate slot optimization input.
    
    Returns:
        (is_valid, error_message)
    """
    try:
        SlotOptimizationRequest(doctor_ids=doctor_ids, date=date)
        return True, ""
    except Exception as e:
        errors = str(e)
        return False, errors


def sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error messages to avoid leaking sensitive information.
    
    Args:
        error: The exception to sanitize
    
    Returns:
        User-friendly error message
    """
    error_str = str(error).lower()
    
    # Map database errors to user-friendly messages
    if "unique constraint" in error_str:
        return "This resource already exists"
    elif "foreign key constraint" in error_str:
        return "Related resource not found"
    elif "not null constraint" in error_str:
        return "Required field is missing"
    elif "check constraint" in error_str:
        return "Invalid value for field"
    else:
        # Generic safe message
        return "An error occurred while processing your request"