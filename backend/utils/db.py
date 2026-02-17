# backend/utils/db.py

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base

DATABASE_URL_DEFAULT = os.getenv("DATABASE_URL", "sqlite:///./dev_db.sqlite3")

_engine = None
_SessionFactory = None

Base = declarative_base()


def init_engine(database_url: str | None = None, echo: bool = False):
    """
    Initialize the SQLAlchemy engine and session factory.
    Call this in tests or app startup to configure the DB URL.
    """
    global _engine, _SessionFactory

    if database_url is None:
        database_url = DATABASE_URL_DEFAULT

    connect_args = (
        {"check_same_thread": False}
        if database_url.startswith("sqlite")
        else {}
    )

    _engine = create_engine(
        database_url,
        echo=echo,
        future=True,
        connect_args=connect_args,
    )

    _SessionFactory = scoped_session(
        sessionmaker(
            bind=_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,  # 🔥 critical fix
        )
    )


def get_engine():
    return _engine


def get_session_factory():
    return _SessionFactory


@contextmanager
def get_session():
    """
    Context manager yielding a Session.
    Automatically commits or rolls back.
    """
    global _engine, _SessionFactory

    if _SessionFactory is None:
        init_engine()

    session = _SessionFactory()

    try:
        yield session
        session.commit()  # ✅ commit on success
    except Exception:
        session.rollback()  # ✅ rollback on error
        raise
    finally:
        session.close()
