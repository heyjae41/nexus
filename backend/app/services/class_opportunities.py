"""클래스 화면에 노출할 외부 해커톤·경진대회 후보와 동기화 로직."""
from collections import Counter
from dataclasses import dataclass
import logging
import unicodedata
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import VersionedCache
from app.models import Course
from app.services.course_collection_lock import course_collection_lock

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClassOpportunityCandidate:
    source_type: str
    source_id: str
    source_category_code: str
    source_category_name: str
    source_category_url: str
    source_rank: int
    title: str
    summary: str | None
    source_url: str
    thumbnail_url: str | None
    sub_category_name: str | None
    format_name: str | None
    qualification: str | None
    running_time_minutes: int | None
    sale_price: int | None
    list_price: int | None
    badges: tuple[str, ...]


@dataclass(frozen=True)
class ClassOpportunityCollectResult:
    candidates: int
    added: int
    updated: int
    hidden: int
    skipped: int


def _title_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _url_key(value: str) -> str:
    parts = urlsplit(value)
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def _values(candidate: ClassOpportunityCandidate) -> dict:
    return {
        "source_type": candidate.source_type,
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


def _duplicate_keys(all_courses: list[Course]) -> tuple[Counter, Counter]:
    published_titles = Counter(
        _title_key(course.title) for course in all_courses if course.status == "published"
    )
    all_urls = Counter(_url_key(course.source_url) for course in all_courses)
    return published_titles, all_urls


def _update_course(course: Course, values: dict) -> bool:
    changes = {key: value for key, value in values.items() if getattr(course, key) != value}
    for key, value in changes.items():
        setattr(course, key, value)
    return bool(changes)


def _is_duplicate(
    course: Course | None,
    candidate: ClassOpportunityCandidate,
    published_titles: Counter,
    all_urls: Counter,
) -> bool:
    title_key = _title_key(candidate.title)
    url_key = _url_key(candidate.source_url)
    title_count = published_titles[title_key]
    url_count = all_urls[url_key]
    if course is not None:
        title_count -= course.status == "published" and _title_key(course.title) == title_key
        url_count -= _url_key(course.source_url) == url_key
    return title_count > 0 or url_count > 0


def _track_update(
    course: Course,
    candidate: ClassOpportunityCandidate,
    values: dict,
    published_titles: Counter,
    all_urls: Counter,
) -> bool:
    if course.status == "published":
        published_titles[_title_key(course.title)] -= 1
    all_urls[_url_key(course.source_url)] -= 1
    changed = _update_course(course, values)
    published_titles[_title_key(candidate.title)] += 1
    all_urls[_url_key(candidate.source_url)] += 1
    return changed


def _upsert_candidates(
    db: Session,
    own: dict[str, Course],
    candidates: list[ClassOpportunityCandidate],
    published_titles: Counter,
    all_urls: Counter,
) -> tuple[int, int, int, set[str]]:
    added = updated = skipped = 0
    accepted_ids = set()
    for candidate in candidates:
        if candidate.source_id in accepted_ids:
            skipped += 1
            continue
        values = _values(candidate)
        course = own.get(candidate.source_id)
        if _is_duplicate(course, candidate, published_titles, all_urls):
            skipped += 1
            continue
        if course is not None:
            updated += _track_update(
                course, candidate, values, published_titles, all_urls
            )
            accepted_ids.add(candidate.source_id)
            continue
        db.add(Course(source_id=candidate.source_id, **values))
        published_titles[_title_key(candidate.title)] += 1
        all_urls[_url_key(candidate.source_url)] += 1
        accepted_ids.add(candidate.source_id)
        added += 1
    return added, updated, skipped, accepted_ids


def _hide_missing(own: dict[str, Course], incoming_ids: set[str]) -> int:
    hidden = 0
    for source_id, course in own.items():
        if source_id not in incoming_ids and course.status == "published":
            course.status = "hidden"
            hidden += 1
    return hidden


def _sync(
    db: Session,
    *,
    source_type: str,
    candidates: list[ClassOpportunityCandidate],
) -> ClassOpportunityCollectResult:
    if any(candidate.source_type != source_type for candidate in candidates):
        raise ValueError("클래스 기회 후보의 source_type이 일치하지 않습니다")
    all_courses = list(db.scalars(select(Course)))
    own = {course.source_id: course for course in all_courses if course.source_type == source_type}
    published_titles, all_urls = _duplicate_keys(all_courses)
    added, updated, skipped, accepted_ids = _upsert_candidates(
        db, own, candidates, published_titles, all_urls
    )
    hidden = _hide_missing(own, accepted_ids)
    db.commit()
    return ClassOpportunityCollectResult(len(candidates), added, updated, hidden, skipped)


def collect_class_opportunities(
    db: Session,
    cache: VersionedCache,
    *,
    source_type: str,
    candidates: list[ClassOpportunityCandidate],
) -> ClassOpportunityCollectResult:
    with course_collection_lock(db):
        try:
            result = _sync(db, source_type=source_type, candidates=candidates)
        except Exception:
            db.rollback()
            raise
    if result.added or result.updated or result.hidden:
        cache.bump_version()
        logger.info(
            "%s 클래스 기회 반영: 신규 %d, 갱신 %d, 숨김 %d, 중복 %d",
            source_type,
            result.added,
            result.updated,
            result.hidden,
            result.skipped,
        )
    return result
