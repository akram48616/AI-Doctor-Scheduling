"""Database connection and session management utilities."""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

DATABASE_URL_DEFAULT = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:root@localhost/ai_doctor_db"
)

_engine = None
_SessionFactory = None

Base = declarative_base()


def init_engine(database_url: str | None = None, echo: bool = False):
    """Initialize the database engine.
    
    Args:
        database_url: Database URL (defaults to DATABASE_URL env var or MySQL)
        echo: Whether to echo SQL statements
        
    Returns:
        SQLAlchemy engine instance
    """
    global _engine, _SessionFactory

    if database_url is None:
        database_url = DATABASE_URL_DEFAULT

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}

    _engine = create_engine(
        database_url,
        echo=echo,
        future=True,
        connect_args=connect_args
    )

    _SessionFactory = scoped_session(
        sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    )
    
    return _engine


def get_engine():
    """Get the current database engine."""
    global _engine
    if _engine is None:
        init_engine()
    return _engine


def get_session_factory():
    """Get the current session factory."""
    global _SessionFactory
    if _SessionFactory is None:
        init_engine()
    return _SessionFactory


@contextmanager
def get_session():
    """Get a database session context manager.
    
    Usage:
        with get_session() as session:
            # Use session
            pass
    """
    global _SessionFactory

    if _SessionFactory is None:
        init_engine()

    session = _SessionFactory()

    try:
        yield session
    finally:
        session.close()