"""DB 엔진/세션 관리."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine = None
_session_factory = None


def get_engine():
    global _engine, _session_factory
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_db() -> Generator[Session, None, None]:
    """FastAPI 의존성 — 요청 단위 세션."""
    get_engine()
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()
