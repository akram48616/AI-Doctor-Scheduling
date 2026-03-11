# backend/utils/db.py

import os
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base, Session

DATABASE_URL_DEFAULT = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:root@localhost/ai_doctor_db"
)

_engine = None  # type: Optional[object]
_SessionFactory = None  # type: Optional[scoped_session]

# Shared declarative base for all models
Base = declarative_base()


def init_engine(database_url: Optional[str] = None, echo: bool = False):
    """
    Initialize and return an SQLAlchemy Engine. Also sets up a default
    scoped session factory stored in module state.
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

    # Create a scoped session factory bound to the engine
    _SessionFactory = scoped_session(
        sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False, future=True)
    )

    return _engine


def init_session_factory(engine):
    """
    Initialize the session factory from an existing engine.
    Useful when tests create the engine first and then want to wire sessions.
    """
    global _engine, _SessionFactory
    _engine = engine
    _SessionFactory = scoped_session(
        sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False, future=True)
    )


def get_engine():
    """Return the initialized engine or None."""
    return _engine


def get_session_factory():
    """Return the scoped session factory (callable) or None."""
    return _SessionFactory


def get_session() -> Session:
    """
    Return a new Session instance from the configured session factory.
    Raises RuntimeError if the session factory is not initialized.
    """
    if _SessionFactory is None:
        raise RuntimeError("Session factory not initialized. Call init_engine() or init_session_factory().")
    return _SessionFactory()


@contextmanager
def session_scope():
    """
    Context manager for a transactional session scope.
    Usage:
        with session_scope() as session:
            ...
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()