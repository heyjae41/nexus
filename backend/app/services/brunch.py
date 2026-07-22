"""브런치(brunch.co.kr) AI 콘텐츠 수집기.

12시간 주기로 키워드 페이지별 기간 내 AI 관련 글 중
'댓글수 + 좋아요수'가 가장 큰 글을 최대 1건씩 선정해 목록에 노출한다.
"""
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.cache import VersionedCache
from app.db import is_unique_violation
from app.models import Article, BrunchCollectRun
from app.services.publish import publish_article

logger = logging.getLogger(__name__)

AI_KEYWORDS = (
    "ai", "인공지능", "머신러닝", "딥러닝", "생성형", "gpt", "llm",
    "챗봇", "프롬프트", "클로드", "제미나이", "copilot", "코파일럿", "에이전트",
    "데이터과학",
)
BRUNCH_CATEGORY_SLUG = "curation"


@dataclass(frozen=True)
class BrunchCandidate:
    title: str
    url: str
    author: str
    likes: int
    comments: int
    summary: str = ""
    published_at: datetime | None = None
    thumbnail_url: str | None = None


def is_ai_related(candidate: BrunchCandidate) -> bool:
    text = f"{candidate.title} {candidate.summary}".lower()
    return any(keyword in text for keyword in AI_KEYWORDS)


def pick_top(candidates: list[BrunchCandidate]) -> BrunchCandidate | None:
    if not candidates:
        return None
    return max(candidates, key=lambda c: c.likes + c.comments)


def _record_run(
    db: Session,
    run: BrunchCollectRun,
    *,
    status: str | None = None,
    error: str | None = None,
) -> None:
    if status is not None:
        run.status = status
        run.error_message = error
    db.add(run)
    db.commit()


def _saved_urls(db: Session, urls: list[str]) -> set[str]:
    if not urls:
        return set()
    stmt = select(Article.source_url).where(Article.source_url.in_(urls))
    return set(db.scalars(stmt))


def collect_and_pick(
    db: Session,
    cache: VersionedCache,
    *,
    candidates: list[BrunchCandidate],
    window_start: datetime,
    window_end: datetime,
) -> Article | None:
    """후보 중 AI 관련·미저장 글에서 최고 인기글 1건을 저장하고 수집 이력을 남긴다."""
    ai_candidates = [c for c in candidates if is_ai_related(c)]
    saved = _saved_urls(db, [c.url for c in ai_candidates])
    fresh = [c for c in ai_candidates if c.url not in saved]
    top = pick_top(fresh)

    run = BrunchCollectRun(
        window_start=window_start,
        window_end=window_end,
        status="empty" if top is None else "success",
        candidates_count=len(candidates),
    )

    if top is None:
        _record_run(db, run)
        return None
    return _publish_top(db, cache, run=run, top=top, published_at=window_end)


def _publish_top(
    db: Session,
    cache: VersionedCache,
    *,
    run: BrunchCollectRun,
    top: BrunchCandidate,
    published_at: datetime,
) -> Article | None:
    """선정 글을 저장하고 이력을 남긴다 — 동시 수집 중복이면 None."""
    try:
        article = publish_article(
            db, cache,
            category_slug=BRUNCH_CATEGORY_SLUG,
            # 브런치는 수집 출처(source_type)이고, 독자가 보는 글 포맷은 컬럼이다.
            article_type="column",
            title=top.title,
            summary=top.summary or None,
            author_name=top.author,
            source_type="brunch",
            source_url=top.url,
            thumbnail_url=top.thumbnail_url,
            likes_count=top.likes,
            comments_count=top.comments,
            published_at=published_at,
        )
    except IntegrityError as exc:
        db.rollback()
        if not is_unique_violation(exc):
            _record_run(db, run, status="failed", error=str(exc))
            raise
        # 동시 수집 레이스: 스케줄러/수동 트리거가 같은 글(source_url)을 먼저 저장.
        # ingest.py 의 동시 인제스트 처리와 동일하게 실패가 아닌 중복으로 기록한다.
        _record_run(db, run, status="duplicate", error="동시 수집 감지 — 이미 저장된 글")
        logger.info("브런치 동시 수집 감지: %s", top.url)
        return None
    except Exception as exc:
        db.rollback()
        _record_run(db, run, status="failed", error=str(exc))
        raise

    run.picked_article_id = article.id
    logger.info("브런치 선정: %s (%d)", top.title, top.likes + top.comments)
    _record_run(db, run)
    return article
