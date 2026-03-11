"""
Pytest configuration and fixtures for AI Doctor Scheduling System tests.

This file sets up test database with file-backed SQLite for proper concurrent testing.
"""
import pytest
import tempfile
import os
from datetime import datetime, timezone, time, timedelta, date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import Base


@pytest.fixture(scope="function")
def test_db():
    """
    Create a file-backed SQLite database for each test.
    
    File-backed SQLite handles concurrent writes better than :memory: SQLite.
    :memory: databases are not shared across threads, making concurrent tests unreliable.
    
    Yields:
        Dict with:
        - engine: SQLAlchemy engine
        - SessionLocal: sessionmaker factory
        - db_path: path to temporary database file
    """
    # Create temporary file for database
    fd, db_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    
    # Create engine with concurrent access enabled
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},  # Allow concurrent access from multiple threads
        poolclass=None  # Disable connection pooling for test isolation
    )
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session factory
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    
    yield {
        "engine": engine,
        "SessionLocal": SessionLocal,
        "db_path": db_path
    }
    
    # Cleanup
    engine.dispose()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture(autouse=True)
def setup_test_session(test_db, monkeypatch):
    """
    Automatically patch get_session() to use test database.
    
    This fixture patches the production get_session() function
    to use the test database instead. It runs for every test automatically.
    
    Args:
        test_db: The test_db fixture
        monkeypatch: pytest's monkeypatch fixture
    """
    SessionLocal = test_db["SessionLocal"]
    
    def test_get_session():
        """Return a new session connected to the test database"""
        return SessionLocal()
    
    # Patch the production get_session to use test session
    monkeypatch.setattr(
        "backend.utils.db.get_session",
        test_get_session
    )


@pytest.fixture
def db_session(test_db):
    """
    Provide a database session for individual tests.
    
    This fixture can be used in tests that need direct database access.
    The session is automatically cleaned up after each test.
    
    Args:
        test_db: The test_db fixture
    
    Yields:
        SQLAlchemy session
    """
    SessionLocal = test_db["SessionLocal"]
    session = SessionLocal()
    
    yield session
    
    # Cleanup
    try:
        session.close()
    except Exception:
        pass


@pytest.fixture
def db_session_factory(test_db):
    """
    Provide a session factory for tests that need multiple sessions.
    
    Useful for tests that need to create multiple sessions
    (e.g., concurrent tests, tests that test multiple connections).
    
    Args:
        test_db: The test_db fixture
    
    Returns:
        sessionmaker factory that creates new sessions
    """
    SessionLocal = test_db["SessionLocal"]
    return SessionLocal


@pytest.fixture
def seed_data(db_session):
    """
    Seed test database with sample data for integration tests.
    
    Creates standard test entities:
    - Hospital with id=1
    - Doctor with id=1
    - Patient with id=11
    - DoctorAvailability for tomorrow (9 AM to 5 PM)
    
    This ensures tests have consistent data to work with.
    Used by: test_optimize_slots_smoke, test_utilization_report_smoke
    
    Args:
        db_session: The db_session fixture
    
    Returns:
        db_session: The session with seeded data
    """
    from backend.models import Hospital, Doctor, Patient, DoctorAvailability
    
    # Create hospital with all fields
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
    
    # Create doctor with correct field names
    doctor = Doctor(
        id=1,
        first_name="Test",
        last_name="Doctor",
        hospital_id=hospital.id,
        consultation_duration=30
    )
    db_session.add(doctor)
    db_session.flush()
    
    # Create patient with correct field names and DATE object (not string!)
    patient = Patient(
        id=11,
        first_name="Test",
        last_name="Patient",
        date_of_birth=date(1990, 1, 15),  # Use date object, NOT string!
        email="patient@test.com",
        phone="+1234567890"
    )
    db_session.add(patient)
    db_session.flush()
    
    # Create availability for tomorrow from 9 AM to 5 PM
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()
    availability = DoctorAvailability(
        doctor_id=doctor.id,
        day_of_week=tomorrow.weekday(),
        start_time=time(9, 0),   # 9 AM
        end_time=time(17, 0),    # 5 PM
        is_available=True
    )
    db_session.add(availability)
    db_session.commit()
    
    # Return session for use in tests
    # Tests can now use patient_id=11, doctor_id=1, hospital_id=1
    return db_session