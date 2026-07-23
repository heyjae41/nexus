"""뉴스레터 수집기 — 신규 발행분을 큐레이션 글(article_type=newsletter)로 반영한다.

후보 전체를 저장한다 (브런치처럼 1건 선정이 아님). source_url 기준 중복 제거,
신규 반영 시 캐시 무효화, 수집 이력 기록은 collect_batch 공통 경로를 쓴다.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import VersionedCache
from app.config import get_settings
from app.models import Article, NewsletterCollectRun
from app.repositories.categories import get_category_by_slug
from app.services import newsletter_fetcher
from app.services.collect_batch import apply_collect_batch
from app.services.newsletter_fetcher import NewsletterCandidate

logger = logging.getLogger(__name__)

NEWSLETTER_CATEGORY_SLUG = "curation"


@dataclass(frozen=True)
class NewsletterCollectResult:
    candidates: int
    added: int


def _existing_urls(db: Session, candidates: list[NewsletterCandidate]) -> set[str]:
    if not candidates:
        return set()
    urls = [c.url for c in candidates]
    return set(db.scalars(select(Article.source_url).where(Article.source_url.in_(urls))))


def _fresh_only(db: Session, candidates: list[NewsletterCandidate]) -> list[NewsletterCandidate]:
    """기존 저장분·배치 내 중복·발행일 없는 후보를 제외한다."""
    seen = _existing_urls(db, candidates)
    fresh: list[NewsletterCandidate] = []
    for c in candidates:
        if c.url in seen:
            continue
        if c.published_at is None:
            logger.warning("발행일 없는 뉴스레터 후보 건너뜀: %s", c.url)
            continue
        seen.add(c.url)
        fresh.append(c)
    return fresh


def _article_row(c: NewsletterCandidate, category_id: int) -> Article:
    # PG VARCHAR 길이 제약에 맞춰 자른다 (SQLite 테스트 DB 는 강제하지 않음)
    return Article(
        category_id=category_id,
        article_type="newsletter",
        title=c.title[:300],
        summary=c.summary[:500] or None,
        author_name=c.publisher,
        source_type=c.source_type,
        source_url=c.url,
        thumbnail_url=c.thumbnail_url,
        published_at=c.published_at,
    )


def collect_newsletters(
    db: Session,
    cache: VersionedCache,
    *,
    candidates: list[NewsletterCandidate],
) -> NewsletterCollectResult:
    category = get_category_by_slug(db, NEWSLETTER_CATEGORY_SLUG)
    if category is None:
        raise ValueError(f"존재하지 않는 카테고리: {NEWSLETTER_CATEGORY_SLUG}")

    fresh = _fresh_only(db, candidates)
    added = apply_collect_batch(
        db,
        rows=((c.url, _article_row(c, category.id)) for c in fresh),
        run_model=NewsletterCollectRun,
        candidates_count=len(candidates),
        label="뉴스레터",
    )
    if added:
        cache.bump_version()
        logger.info("뉴스레터 %d건 신규 반영 → 캐시 무효화", added)
    return NewsletterCollectResult(candidates=len(candidates), added=added)


def collect_recent_newsletters(db: Session, cache: VersionedCache) -> NewsletterCollectResult:
    """설정된 전체 소스에서 최근 발행분을 수집한다 — 스케줄러/수동 트리거 공용 경로."""
    settings = get_settings()
    candidates = newsletter_fetcher.fetch_newsletter_candidates(
        stibee_pairs=settings.newsletter_stibee_pairs,
        stibee_base_url=settings.stibee_page_base_url,
        kma_base_url=settings.newsletter_kma_base_url,
    )
    recent = newsletter_fetcher.filter_recent(
        candidates,
        now=datetime.now(timezone.utc),
        days=settings.newsletter_window_days,
    )
    return collect_newsletters(db, cache, candidates=recent)
