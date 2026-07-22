"""`courses` 테이블을 갱신하는 모든 수집기의 공용 직렬화 락."""
from contextlib import contextmanager
import threading

from sqlalchemy import text
from sqlalchemy.orm import Session

_COURSE_COLLECT_LOCK = threading.Lock()
_PG_ADVISORY_LOCK_ID = 336_131_872_083


@contextmanager
def course_collection_lock(db: Session):
    """프로세스 및 PostgreSQL 트랜잭션 범위에서 클래스 수집을 직렬화한다."""
    with _COURSE_COLLECT_LOCK:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": _PG_ADVISORY_LOCK_ID},
            )
        yield
