"""
Pytest configuration and fixtures for AI Doctor Scheduling System tests.

This file sets up a file-backed SQLite database for proper concurrent testing.
"""
import pytest
import tempfile
import os
from datetime import datetime, timezone, time, timedelta, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the shared Base and ensure models are registered on it
from backend.utils.db import Base, init_session_factory, get_session as real_get_session
import backend.models  # ensure all model classes are imported and registered on Base


@pytest.fixture(scope="function")
def test_db():
    """
    Create a file-backed SQLite database for each test.

    Yields:
        Dict with:
        - engine: SQLAlchemy engine
        - SessionLocal: sessionmaker factory
        - db_path: path to temporary database file
    """
    fd, db_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)

    db_url = f"sqlite:///{db_path}"
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
    )

    # Ensure all models are registered on Base before creating tables
    Base.metadata.create_all(engine)

    # Create session factory compatible with tests
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    yield {
        "engine": engine,
        "SessionLocal": SessionLocal,
        "db_path": db_path
    }

    # Cleanup
    try:
        engine.dispose()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture(autouse=True)
def setup_test_session(test_db, monkeypatch):
    """
    Automatically patch backend.utils.db to use the test database.

    This fixture runs for every test automatically.
    """
    SessionLocal = test_db["SessionLocal"]

    # Wire the utils.db session factory to the test engine so code that calls
    # init_session_factory or get_session will use the test DB.
    init_session_factory(test_db["engine"])

    # Provide a simple get_session replacement that returns a fresh session
    def test_get_session():
        return SessionLocal()

    # Patch the production get_session to use test session
    monkeypatch.setattr("backend.utils.db.get_session", test_get_session)


@pytest.fixture
def db_session(test_db):
    """
    Provide a database session for individual tests.
    """
    SessionLocal = test_db["SessionLocal"]
    session = SessionLocal()
    try:
        yield session
    finally:
        try:
            session.close()
        except Exception:
            pass


@pytest.fixture
def db_session_factory(test_db):
    """
    Provide a session factory for tests that need multiple sessions.
    """
    return test_db["SessionLocal"]


@pytest.fixture
def client(test_db, monkeypatch):
    """
    Provide a Flask test client for testing routes.

    Creates the app after the test engine and session factory are ready,
    and passes the test engine into create_app so the app does not attempt
    to initialize the production DB.
    """
    # Ensure backend.utils.db.get_session is patched (setup_test_session already does this)
    # Import create_app only after test DB is ready
    from backend.app import create_app

    # Create app with injected test engine
    app = create_app(test_engine=test_db["engine"])
    app.config['TESTING'] = True

    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def seed_data(db_session):
    """
    Seed test database with sample data for integration tests.

    Creates:
    - Hospital id=1
    - Doctor id=1
    - Patient id=11
    - DoctorAvailability for ALL 7 DAYS of the week (9 AM to 5 PM)
    
    This ensures tests that query availability for any day will find data.
    
    Days: 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday
    """
    from backend.models import Hospital, Doctor, Patient, DoctorAvailability

    # Create hospital
    hospital = Hospital(
        id=1,
        name="Test Hospital",
        city="Test City",
        state="TS",
        address="123 Test St",
        zip_code="12345",
        phone="+1234567890",
        email="hospital@test.com"
    )
    db_session.add(hospital)
    db_session.flush()

    # Create doctor
    doctor = Doctor(
        id=1,
        first_name="Test",
        last_name="Doctor",
        hospital_id=hospital.id,
        consultation_duration=30
    )
    db_session.add(doctor)
    db_session.flush()

    # Create patient
    patient = Patient(
        id=11,
        first_name="Test",
        last_name="Patient",
        date_of_birth=date(1990, 1, 15),
        email="patient@test.com",
        phone="+1234567890"
    )
    db_session.add(patient)
    db_session.flush()

    # ✅ CREATE AVAILABILITY FOR ALL 7 DAYS OF THE WEEK
    # This is critical for tests that query availability for different days
    # test_optimize_slots_smoke will query for tomorrow's availability
    # By creating all 7 days, we ensure it will always find data regardless of which day is queried
    # 
    # Days: 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday
    for day_of_week in range(7):
        availability = DoctorAvailability(
            doctor_id=doctor.id,
            day_of_week=day_of_week,
            start_time=time(9, 0),
            end_time=time(17, 0),
            is_available=True
        )
        db_session.add(availability)
    
    db_session.commit()

    return db_session