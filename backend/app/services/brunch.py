"""브런치(brunch.co.kr) AI 컨텐츠 수집기.

12시간 주기로 실행되어 기간 내 AI 관련 글 중
'댓글수 + 좋아요수' 가 가장 큰 글 1건을 선정해 목록에 노출한다.
"""
import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import VersionedCache
from app.models import Article, BrunchCollectRun
from app.services.publish import publish_article

logger = logging.getLogger(__name__)

AI_KEYWORDS = (
    "ai", "인공지능", "머신러닝", "딥러닝", "생성형", "gpt", "llm",
    "챗봇", "프롬프트", "클로드", "제미나이", "copilot", "코파일럿", "에이전트",
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


def is_ai_related(candidate: BrunchCandidate) -> bool:
    text = f"{candidate.title} {candidate.summary}".lower()
    return any(keyword in text for keyword in AI_KEYWORDS)


def pick_top(candidates: list[BrunchCandidate]) -> BrunchCandidate | None:
    if not candidates:
        return None
    return max(candidates, key=lambda c: c.likes + c.comments)


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

    article = None
    try:
        if top is not None:
            article = publish_article(
                db, cache,
                category_slug=BRUNCH_CATEGORY_SLUG,
                article_type="brunch",
                title=top.title,
                summary=top.summary or None,
                author_name=top.author,
                source_type="brunch",
                source_url=top.url,
                likes_count=top.likes,
                comments_count=top.comments,
                published_at=window_end,
            )
            run.picked_article_id = article.id
            logger.info("브런치 선정: %s (%d)", top.title, top.likes + top.comments)
    except Exception as exc:
        db.rollback()
        run.status = "failed"
        run.error_message = str(exc)
        db.add(run)
        db.commit()
        raise

    db.add(run)
    db.commit()
    return article
