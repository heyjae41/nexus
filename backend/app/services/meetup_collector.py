"""밋업 수집기 — 검색 결과 전체를 meet.pl(meetup_events)에 반영한다.

브런치 수집기와 같은 패턴: source_url 기준 중복 제거, 신규 반영 시 캐시 무효화,
수집 이력 기록. 브런치와 달리 '전체' 후보를 저장한다 (1건 선정이 아님).
"""
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import VersionedCache
from app.models import MeetupCollectRun, MeetupEvent
from app.services.collect_batch import apply_collect_batch
from app.services.meetup_fetcher import MeetupCandidate

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MeetupCollectResult:
    candidates: int
    added: int


def _existing_keys(db: Session, candidates: list[MeetupCandidate]) -> tuple[set[str], set[str]]:
    """기존 이벤트의 (source_url, source_id) 집합 — 둘 다 UNIQUE 제약이 있다."""
    if not candidates:
        return set(), set()
    urls = [c.source_url for c in candidates]
    ids = [c.source_id for c in candidates]
    existing_urls = set(
        db.scalars(select(MeetupEvent.source_url).where(MeetupEvent.source_url.in_(urls)))
    )
    existing_ids = set(
        db.scalars(select(MeetupEvent.source_id).where(MeetupEvent.source_id.in_(ids)))
    )
    return existing_urls, existing_ids


def _event_row(c: MeetupCandidate) -> MeetupEvent:
    return MeetupEvent(
        source_id=c.source_id,
        title=c.title,
        host_name=c.host_name,
        source_url=c.source_url,
        event_start=c.event_start,
        event_end=c.event_end,
        place=c.place,
        area=c.area,
        address=c.address,
        price_min=c.price_min,
        is_free=c.is_free,
        view_count=c.view_count,
        event_system_type=c.event_system_type,
        category=c.category,
        cover_image_url=c.cover_image_url,
    )


def collect_meetups(
    db: Session,
    cache: VersionedCache,
    *,
    candidates: list[MeetupCandidate],
) -> MeetupCollectResult:
    existing_urls, existing_ids = _existing_keys(db, candidates)
    # 배치 내 중복(luma AI/TECH 양쪽에 잡힌 이벤트 등)도 함께 제거한다
    fresh: list[MeetupCandidate] = []
    for c in candidates:
        if c.source_url in existing_urls or c.source_id in existing_ids:
            continue
        existing_urls.add(c.source_url)
        existing_ids.add(c.source_id)
        fresh.append(c)

    added = apply_collect_batch(
        db,
        rows=((c.source_url, _event_row(c)) for c in fresh),
        run_model=MeetupCollectRun,
        candidates_count=len(candidates),
        label="밋업",
    )
    if added:
        cache.bump_version()
        logger.info("밋업 %d건 신규 반영 → 캐시 무효화", added)
    return MeetupCollectResult(candidates=len(candidates), added=added)
