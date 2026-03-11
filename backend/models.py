# backend/models.py
from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Date, Time,
    DateTime, Float, ForeignKey, Boolean, Enum as SAEnum,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.utils.db import Base


class AppointmentStatus(Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class UserRole(str, Enum):
    """User roles in the system"""
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"
    RECEPTIONIST = "receptionist"


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    phone = Column(String(20))
    email = Column(String(100))

    doctors = relationship("Doctor", back_populates="hospital", cascade="all, delete")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    first_name = Column(String(100))
    last_name = Column(String(100))
    specialization = Column(String(100))
    phone = Column(String(20))
    email = Column(String(100), unique=True)
    consultation_duration = Column(Integer, default=30)

    hospital = relationship("Hospital", back_populates="doctors")
    availabilities = relationship("DoctorAvailability", cascade="all, delete")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    date_of_birth = Column(Date)
    gender = Column(String(20))
    phone = Column(String(20))
    email = Column(String(100), unique=True)


class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"

    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    day_of_week = Column(Integer)
    start_time = Column(Time)
    end_time = Column(Time)
    is_available = Column(Boolean, default=True)


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        UniqueConstraint("doctor_id", "appointment_datetime", name="uix_doctor_datetime"),
    )

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    appointment_datetime = Column(DateTime)
    duration_minutes = Column(Integer, default=30)
    status = Column(SAEnum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    no_show_probability = Column(Float, default=0.0)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now(), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)


class User(Base):
    """
    User account for authentication.
    Represents all users (patients, doctors, admin, receptionists).
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.PATIENT)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"