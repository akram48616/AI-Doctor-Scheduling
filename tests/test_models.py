"""
Unit tests for ORM models.
Uses an in-memory SQLite database to validate CRUD operations and relationships.
"""
import unittest
from datetime import datetime, date, time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import (
    Base,
    Doctor,
    Patient,
    Hospital,
    Appointment,
    DoctorAvailability,
    AppointmentStatus,
)


class TestModels(unittest.TestCase):
    """Test suite for ORM models."""

    def setUp(self):
        """Create fresh in-memory SQLite database for EACH test."""
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def tearDown(self):
        """Clean up after each test."""
        self.session.close()
        self.engine.dispose()

    def test_hospital_creation(self):
        hospital = Hospital(
            name="Test Hospital",
            address="123 Test St",
            city="Test City",
            state="TS",
            zip_code="12345",
            phone="555-1234",
            email="test@hospital.com"
        )
        self.session.add(hospital)
        self.session.commit()

        retrieved = self.session.query(Hospital).filter_by(name="Test Hospital").first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.city, "Test City")

    def test_doctor_creation(self):
        hospital = Hospital(
            name="Test Hospital",
            address="123 Test St",
            city="Test City",
            state="TS",
            zip_code="12345",
            phone="555-1234",
            email="test@hospital.com"
        )
        self.session.add(hospital)
        self.session.commit()

        doctor = Doctor(
            hospital_id=hospital.id,
            first_name="John",
            last_name="Doe",
            specialization="Cardiology",
            phone="555-5678",
            email="john.doe@hospital.com",
            consultation_duration=45
        )
        self.session.add(doctor)
        self.session.commit()

        retrieved = self.session.query(Doctor).filter_by(email="john.doe@hospital.com").first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.first_name, "John")
        self.assertEqual(retrieved.hospital_id, hospital.id)

    def test_patient_creation(self):
        patient = Patient(
            first_name="Alice",
            last_name="Smith",
            date_of_birth=date(1990, 1, 1),
            gender="Female",
            phone="555-9999",
            email="alice@email.com"
        )
        self.session.add(patient)
        self.session.commit()

        retrieved = self.session.query(Patient).filter_by(email="alice@email.com").first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.first_name, "Alice")

    def test_appointment_creation(self):
        hospital = Hospital(
            name="Test Hospital",
            address="123 Test St",
            city="Test City",
            state="TS",
            zip_code="12345",
            phone="555-1234",
            email="test@hospital.com"
        )
        self.session.add(hospital)
        self.session.commit()

        doctor = Doctor(
            hospital_id=hospital.id,
            first_name="John",
            last_name="Doe",
            specialization="Cardiology",
            phone="555-5678",
            email="john.doe@hospital.com"
        )
        self.session.add(doctor)
        self.session.commit()

        patient = Patient(
            first_name="Alice",
            last_name="Smith",
            date_of_birth=date(1990, 1, 1),
            gender="Female",
            phone="555-9999",
            email="alice@email.com"
        )
        self.session.add(patient)
        self.session.commit()

        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            hospital_id=hospital.id,
            appointment_datetime=datetime(2026, 3, 1, 10, 0),
            duration_minutes=45,
            status=AppointmentStatus.SCHEDULED,
            reason="Annual checkup",
            no_show_probability=0.15
        )
        self.session.add(appointment)
        self.session.commit()

        retrieved = self.session.query(Appointment).first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.patient_id, patient.id)
        self.assertEqual(retrieved.doctor_id, doctor.id)
        self.assertEqual(retrieved.status, AppointmentStatus.SCHEDULED)
        self.assertAlmostEqual(retrieved.no_show_probability, 0.15)

    def test_doctor_availability(self):
        hospital = Hospital(
            name="Test Hospital",
            address="123 Test St",
            city="Test City",
            state="TS",
            zip_code="12345",
            phone="555-1234",
            email="test@hospital.com"
        )
        self.session.add(hospital)
        self.session.commit()

        doctor = Doctor(
            hospital_id=hospital.id,
            first_name="John",
            last_name="Doe",
            specialization="Cardiology",
            phone="555-5678",
            email="john.doe@hospital.com"
        )
        self.session.add(doctor)
        self.session.commit()

        availability = DoctorAvailability(
            doctor_id=doctor.id,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_available=True
        )
        self.session.add(availability)
        self.session.commit()

        retrieved = self.session.query(DoctorAvailability).filter_by(doctor_id=doctor.id).first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.day_of_week, 0)

    def test_cascade_delete(self):
        hospital = Hospital(
            name="Test Hospital",
            address="123 Test St",
            city="Test City",
            state="TS",
            zip_code="12345",
            phone="555-1234",
            email="test@hospital.com"
        )
        self.session.add(hospital)
        self.session.commit()

        doctor = Doctor(
            hospital_id=hospital.id,
            first_name="John",
            last_name="Doe",
            specialization="Cardiology",
            phone="555-5678",
            email="john.doe@hospital.com"
        )
        self.session.add(doctor)
        self.session.commit()

        doctor_id = doctor.id

        self.session.delete(hospital)
        self.session.commit()

        deleted_doctor = self.session.query(Doctor).filter_by(id=doctor_id).first()
        self.assertIsNone(deleted_doctor)


if __name__ == "__main__":
    unittest.main()
