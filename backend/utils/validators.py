"""
Validation utilities for input data.
"""
import re
from datetime import datetime


def validate_email(email):
    if not email or not isinstance(email, str):
        return False, "Email is required and must be a string"
    email = email.strip()
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False, "Invalid email format"
    if len(email) > 100:
        return False, "Email must be less than 100 characters"
    return True, None


def validate_phone(phone):
    if not phone or not isinstance(phone, str):
        return False, "Phone is required and must be a string"
    digits_only = re.sub(r"[\s\-\(\)\+\.]", "", phone)
    if not digits_only.isdigit():
        return False, "Phone must contain only digits and valid separators"
    if len(digits_only) < 7 or len(digits_only) > 15:
        return False, "Phone must be between 7 and 15 digits"
    return True, None


def validate_date_string(date_str, fmt="%Y-%m-%d"):
    if not date_str or not isinstance(date_str, str):
        return False, "Date is required and must be a string"
    try:
        datetime.strptime(date_str, fmt)
        return True, None
    except ValueError:
        return False, f"Invalid date format. Expected {fmt}"


def validate_time_string(time_str, fmt="%H:%M:%S"):
    if not time_str or not isinstance(time_str, str):
        return False, "Time is required and must be a string"
    try:
        datetime.strptime(time_str, fmt)
        return True, None
    except ValueError:
        try:
            datetime.strptime(time_str, "%H:%M")
            return True, None
        except ValueError:
            return False, f"Invalid time format. Expected {fmt} or HH:MM"


def validate_required_fields(data, required_fields):
    if not isinstance(data, dict):
        return False, "Data must be a JSON object"
    missing = [f for f in required_fields if f not in data or data[f] is None]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    return True, None