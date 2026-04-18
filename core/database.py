# core/database.py
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


def get_session() -> Session:
    return _SessionLocal()
