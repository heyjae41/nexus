"""DB 엔진/세션 관리."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
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


def is_unique_violation(exc: IntegrityError) -> bool:
    """UNIQUE 위반(동시 쓰기 레이스)인지 판별 — NOT NULL/FK 위반 등 실제 결함과 구분한다.

    PG 는 'duplicate key value violates unique constraint',
    SQLite 는 'UNIQUE constraint failed' 메시지를 담는다.
    """
    detail = str(exc.orig or exc).lower()
    return "unique" in detail or "duplicate" in detail


def get_db() -> Generator[Session, None, None]:
    """FastAPI 의존성 — 요청 단위 세션."""
    get_engine()
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()
