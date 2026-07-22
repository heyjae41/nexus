"""패스트캠퍼스 과정 upsert 및 대상 태그 이탈 과정 숨김 처리."""
from dataclasses import dataclass
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import VersionedCache
from app.models import Course, FastCampusCollectRun
from app.services.course_collection_lock import course_collection_lock
from app.services.fastcampus_fetcher import FastCampusCandidate

logger = logging.getLogger(__name__)


class CollectionSafetyError(ValueError):
    """불완전한 외부 응답으로 기존 과정을 대량 숨기는 것을 차단한다."""


@dataclass(frozen=True)
class FastCampusCollectResult:
    candidates: int
    added: int
    updated: int
    hidden: int


def _values(candidate: FastCampusCandidate) -> dict:
    return {
        "source_type": "fastcampus",
        "source_category_code": candidate.source_category_code,
        "source_category_name": candidate.source_category_name,
        "source_category_url": candidate.source_category_url,
        "source_rank": candidate.source_rank,
        "title": candidate.title,
        "summary": candidate.summary,
        "source_url": candidate.source_url,
        "thumbnail_url": candidate.thumbnail_url,
        "sub_category_name": candidate.sub_category_name,
        "format_name": candidate.format_name,
        "qualification": candidate.qualification,
        "running_time_minutes": candidate.running_time_minutes,
        "sale_price": candidate.sale_price,
        "list_price": candidate.list_price,
        "badges": "|".join(candidate.badges),
        "status": "published",
    }


def _upsert_courses(db: Session, existing: dict[str, Course], candidates) -> tuple[int, int]:
    added = updated = 0
    for candidate in candidates:
        course = existing.get(candidate.source_id)
        values = _values(candidate)
        if course is None:
            db.add(Course(source_id=candidate.source_id, **values))
            added += 1
            continue
        changes = {key: value for key, value in values.items() if getattr(course, key) != value}
        for key, value in changes.items():
            setattr(course, key, value)
        updated += bool(changes)
    return added, updated


def _hide_missing(
    existing: dict[str, Course], incoming_ids: set[str], completed_categories: set[str]
) -> int:
    hidden = 0
    for source_id, course in existing.items():
        if (
            course.source_category_code in completed_categories
            and source_id not in incoming_ids
            and course.status == "published"
        ):
            course.status = "hidden"
            hidden += 1
    return hidden


def _validate_batch(
    existing: dict[str, Course],
    candidates: list[FastCampusCandidate],
    completed_categories: set[str],
) -> None:
    if not candidates or not completed_categories:
        raise CollectionSafetyError("패스트캠퍼스 수집 후보가 비어 있어 반영을 중단합니다")
    incoming_categories = {candidate.source_category_code for candidate in candidates}
    if not incoming_categories.issubset(completed_categories):
        raise CollectionSafetyError("완료되지 않은 카테고리의 후보가 포함됐습니다")
    for category in completed_categories:
        _validate_category_volume(existing, candidates, category)


def _validate_category_volume(
    existing: dict[str, Course], candidates: list[FastCampusCandidate], category: str
) -> None:
    incoming = sum(c.source_category_code == category for c in candidates)
    if incoming == 0:
        raise CollectionSafetyError(f"{category} 수집 후보가 비어 있습니다")
    current = sum(
        course.source_category_code == category and course.status == "published"
        for course in existing.values()
    )
    if current >= 4 and incoming * 2 < current:
        raise CollectionSafetyError(
            f"{category} 후보가 {current}건에서 {incoming}건으로 급감해 반영을 중단합니다"
        )


def _collect_locked(
    db: Session,
    cache: VersionedCache,
    *,
    candidates: list[FastCampusCandidate],
    completed_categories: set[str],
) -> FastCampusCollectResult:
    try:
        existing = {
            course.source_id: course
            for course in db.scalars(select(Course).where(Course.source_type == "fastcampus"))
        }
        _validate_batch(existing, candidates, completed_categories)
        incoming_ids = {candidate.source_id for candidate in candidates}
        added, updated = _upsert_courses(db, existing, candidates)
        hidden = _hide_missing(existing, incoming_ids, completed_categories)

        db.add(FastCampusCollectRun(
            status="empty" if not candidates else "success",
            candidates_count=len(candidates),
            added_count=added,
            updated_count=updated,
            hidden_count=hidden,
        ))
        db.commit()
    except Exception as exc:
        db.rollback()
        db.add(FastCampusCollectRun(
            status="failed",
            candidates_count=len(candidates),
            error_message=str(exc),
        ))
        db.commit()
        raise

    if added or updated or hidden:
        cache.bump_version()
        logger.info(
            "패스트캠퍼스 클래스 반영: 신규 %d, 갱신 %d, 숨김 %d",
            added, updated, hidden,
        )
    return FastCampusCollectResult(len(candidates), added, updated, hidden)


def collect_fastcampus_courses(
    db: Session,
    cache: VersionedCache,
    *,
    candidates: list[FastCampusCandidate],
    completed_categories: set[str] | None = None,
) -> FastCampusCollectResult:
    categories = completed_categories or {
        candidate.source_category_code for candidate in candidates
    }
    with course_collection_lock(db):
        return _collect_locked(
            db, cache, candidates=candidates, completed_categories=set(categories)
        )
