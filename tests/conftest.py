# tests/conftest.py

import os
import tempfile
import shutil
import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base
from backend.utils.db import init_engine


# --------------------------------------------------
# Temporary SQLite DB file (per test session)
# --------------------------------------------------

@pytest.fixture(scope="session")
def tmp_db_path():
    tmp_dir = tempfile.mkdtemp(prefix="ai_sched_test_")
    db_file = Path(tmp_dir) / "test_db.sqlite3"
    yield str(db_file)
    shutil.rmtree(tmp_dir, ignore_errors=True)


# --------------------------------------------------
# Force SQLite instead of MySQL during tests
# --------------------------------------------------

@pytest.fixture(scope="session")
def db_url(tmp_db_path):
    url = f"sqlite:///{tmp_db_path}"
    os.environ["DATABASE_URL"] = url  # 🔥 override MySQL
    return url


# --------------------------------------------------
# Create tables using SQLAlchemy models
# --------------------------------------------------

@pytest.fixture(scope="session")
def engine(db_url):
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False}
    )

    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# --------------------------------------------------
# Session factory fixture
# --------------------------------------------------

@pytest.fixture(scope="session")
def db_session_factory(engine):
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False
    )

    def factory():
        return SessionLocal()

    return factory


# --------------------------------------------------
# Per-test DB session
# --------------------------------------------------

@pytest.fixture(scope="function")
def db_session(db_session_factory):
    session = db_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# --------------------------------------------------
# Seed minimal data required by tests
# --------------------------------------------------

@pytest.fixture(scope="function")
def seed_data(db_session):
    """
    Provide minimal seed objects required for tests.
    Clears existing data before inserting to avoid UNIQUE constraint violations.
    """

    from backend.models import Hospital, Doctor, Patient

    # Clear existing data before inserting new records (order matters due to foreign keys)
    db_session.query(Patient).delete()
    db_session.query(Doctor).delete()
    db_session.query(Hospital).delete()
    db_session.commit()

    hospital = Hospital(
        id=1,
        name="Test Hospital",
        city="Test City"
    )

    doctor = Doctor(
        id=1,
        hospital_id=1,
        first_name="John",
        last_name="Doe",
        consultation_duration=30
    )

    patient = Patient(
        id=1,
        first_name="Jane",
        last_name="Smith",
        date_of_birth=datetime.date(1990, 1, 1)
    )

    db_session.add_all([hospital, doctor, patient])
    db_session.commit()

    return SimpleNamespace(
        query_date=datetime.date.today(),
        db_url=os.environ["DATABASE_URL"]
    )