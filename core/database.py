# core/database.py
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

_engine = None
_SessionLocal = None


def init_db(database_url: str) -> None:
    global _engine, _SessionLocal
    _engine = create_engine(database_url, echo=False)
    _SessionLocal = sessionmaker(bind=_engine)


def get_engine():
    return _engine


@contextmanager
def get_session():
    """Context manager for database sessions.
    Usage: with get_session() as session: ...
    Rolls back on exception, always closes."""
    session = _SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
