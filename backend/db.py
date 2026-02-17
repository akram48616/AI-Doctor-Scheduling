# backend/db.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from contextlib import contextmanager

# 🔹 MySQL connection
DATABASE_URL = "mysql+pymysql://root:root@localhost:3306/ai_doctor_scheduling"

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # prevents MySQL timeout issues
    echo=False
)

# Session factory
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False)
)

# Base class for models
Base = declarative_base()


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
