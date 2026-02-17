# backend/models.py

from enum import Enum
from sqlalchemy import (
    Column, Integer, String, Text, Date, Time,
    DateTime, Float, ForeignKey, Boolean,
    Enum as SAEnum, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.utils.db import Base


# ==========================================================
# ENUMS
# ==========================================================

class AppointmentStatus(Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


# ==========================================================
# HOSPITAL
# ==========================================================

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

    doctors = relationship(
        "Doctor",
        back_populates="hospital",
        cascade="all, delete-orphan"
    )

    appointments = relationship("Appointment", back_populates="hospital")


# ==========================================================
# DOCTOR
# ==========================================================

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)

    first_name = Column(String(100))
    last_name = Column(String(100))
    specialization = Column(String(100))
    phone = Column(String(20))
    email = Column(String(100), unique=True)
    consultation_duration = Column(Integer, default=30)

    hospital = relationship("Hospital", back_populates="doctors")

    availabilities = relationship(
        "DoctorAvailability",
        back_populates="doctor",
        cascade="all, delete-orphan"
    )

    appointments = relationship("Appointment", back_populates="doctor")


# ==========================================================
# PATIENT
# ==========================================================

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    date_of_birth = Column(Date)
    gender = Column(String(20))
    phone = Column(String(20))
    email = Column(String(100), unique=True)

    appointments = relationship("Appointment", back_populates="patient")


# ==========================================================
# DOCTOR AVAILABILITY
# ==========================================================

class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"

    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))

    day_of_week = Column(Integer)  # 0 = Monday, 6 = Sunday
    start_time = Column(Time)
    end_time = Column(Time)
    is_available = Column(Boolean, default=True)

    doctor = relationship("Doctor", back_populates="availabilities")


# ==========================================================
# APPOINTMENT
# ==========================================================

class Appointment(Base):
    __tablename__ = "appointments"

    __table_args__ = (
        UniqueConstraint(
            "doctor_id",
            "appointment_datetime",
            name="uix_doctor_datetime"
        ),
        Index("idx_doctor_id", "doctor_id"),
        Index("idx_patient_id", "patient_id"),
    )

    id = Column(Integer, primary_key=True)

    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    hospital_id = Column(Integer, ForeignKey("hospitals.id"))

    appointment_datetime = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)

    # SQLite-safe enum storage
    status = Column(
        SAEnum(AppointmentStatus, native_enum=False),
        default=AppointmentStatus.SCHEDULED
    )

    no_show_probability = Column(Float, default=0.0)
    reason = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    cancelled_at = Column(DateTime)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    hospital = relationship("Hospital", back_populates="appointments")
