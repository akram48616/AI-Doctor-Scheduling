"""
Integration tests for scheduling service.
Uses SQLite in-memory database (no MySQL required).
"""

import threading
from datetime import datetime, timezone, date
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool

from backend.models import (
    Base,
    Doctor,
    DoctorAvailability,
    Appointment,
    Patient,
    Hospital,
    AppointmentStatus
)

from backend.services import scheduling

UTC = timezone.utc
DB_URL = "sqlite:///:memory:"


# ----------------------------
# Database Fixture
# ----------------------------
@pytest.fixture(scope="function")
def db_session_factory():
    engine = create_engine(
        DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Important for shared in-memory DB
    )

    Base.metadata.create_all(engine)

    factory = scoped_session(sessionmaker(bind=engine))
    yield factory

    factory.remove()
    Base.metadata.drop_all(engine)
    engine.dispose()


# ----------------------------
# Seed Data Fixture
# ----------------------------
@pytest.fixture
def seed_data(db_session_factory):
    session = db_session_factory()

    doctor = Doctor(
        id=1,
        first_name="Dr",
        last_name="Test",
        specialization="General",
        email="dr@test.com",
        phone="1234567890",
        consultation_duration=30,
        hospital_id=1,
    )

    patient = Patient(
        id=11,
        first_name="Patient",
        last_name="Test",
        email="patient@test.com",
        phone="9876543210",
    )

    hospital = Hospital(
        id=1,
        name="Test Hospital"
    )

    session.add_all([doctor, patient, hospital])

    avail = DoctorAvailability(
        doctor_id=1,
        day_of_week=0,  # Monday
        start_time=datetime.strptime("09:00:00", "%H:%M:%S").time(),
        end_time=datetime.strptime("17:00:00", "%H:%M:%S").time(),
        is_available=True
    )

    session.add(avail)
    session.commit()

    yield session
    session.close()


# ----------------------------
# Tests
# ----------------------------

def test_normalize_datetime_input_accepts_iso_and_date():
    dt = scheduling._normalize_datetime_input("2026-03-16T11:00:00")
    assert dt.tzinfo is not None and dt.hour == 11

    dt2 = scheduling._normalize_datetime_input("2026-03-16")
    assert dt2.hour == 0 and dt2.tzinfo is not None


def test_ensure_date_variants():
    assert scheduling._ensure_date("2026-03-16") == date(2026, 3, 16)
    assert scheduling._ensure_date(datetime(2026, 3, 16, 5, 0)) == date(2026, 3, 16)


def test_find_available_slots_no_conflict(seed_data, db_session_factory):
    original_get_session = scheduling.get_session
    scheduling.get_session = db_session_factory

    try:
        slots = scheduling.find_available_slots(
            doctor_id=1,
            date="2026-03-16",
            consultation_minutes=30
        )

        assert len(slots) > 0
        assert all(9 <= s.hour < 17 for s in slots)
    finally:
        scheduling.get_session = original_get_session


def test_booking_and_double_book_protection(seed_data, db_session_factory):
    session = db_session_factory()

    original_get_session = scheduling.get_session
    scheduling.get_session = lambda: session

    try:
        iso = "2026-03-16T11:00:00"

        res = scheduling.book_appointment(11, 1, 1, iso)
        assert res["success"]

        appt_id = res["appointment_id"]

        # Try double booking same slot
        res2 = scheduling.book_appointment(11, 1, 1, iso)
        assert not res2["success"]

        # Cancel appointment
        assert scheduling.cancel_appointment(appt_id)["success"]

        # Cancel again (should fail)
        assert not scheduling.cancel_appointment(appt_id)["success"]

    finally:
        scheduling.get_session = original_get_session


def test_concurrent_booking_race(seed_data, db_session_factory):
    iso = "2026-03-16T12:00:00"
    results = []

    def attempt_book():
        session = db_session_factory()
        original_get_session = scheduling.get_session
        scheduling.get_session = lambda: session

        try:
            results.append(
                scheduling.book_appointment(11, 1, 1, iso)
            )
        finally:
            scheduling.get_session = original_get_session
            session.close()

    t1 = threading.Thread(target=attempt_book)
    t2 = threading.Thread(target=attempt_book)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    successes = [r for r in results if r.get("success")]
    failures = [r for r in results if not r.get("success")]

    assert len(successes) == 1
    assert len(failures) == 1
