"""수집 배치 공통 반영 로직 — SAVEPOINT 단위 삽입과 수집 이력 기록.

밋업/뉴스레터처럼 '후보 전체를 저장'하는 수집기가 공유한다.
"""
import logging
from typing import Iterable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import is_unique_violation

logger = logging.getLogger(__name__)


def apply_collect_batch(
    db: Session,
    *,
    rows: Iterable[tuple[str, object]],
    run_model: type,
    candidates_count: int,
    label: str,
) -> int:
    """신규 행 (식별 URL, ORM 행) 목록을 SAVEPOINT 로 추가하고 수집 이력을 남긴다.

    동시 수집 레이스로 일부가 UNIQUE 충돌해도 나머지 신규 행은 유실하지 않으며,
    NOT NULL/FK 등 실제 결함은 failed 이력을 남기고 전파한다.
    """
    added = 0
    try:
        for url, row in rows:
            try:
                with db.begin_nested():
                    db.add(row)
                    db.flush()
                added += 1
            except IntegrityError as exc:
                if not is_unique_violation(exc):
                    raise
                logger.info("%s 동시 수집 감지 — 건너뜀: %s", label, url)
        db.add(
            run_model(
                status="empty" if not candidates_count else "success",
                candidates_count=candidates_count,
                added_count=added,
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        db.add(
            run_model(
                status="failed",
                candidates_count=candidates_count,
                error_message=str(exc),
            )
        )
        db.commit()
        raise
    return added
