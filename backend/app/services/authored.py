"""어드민이 직접 작성한 큐레이션 글을 발행한다."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.cache import VersionedCache
from app.models import Article, Member
from app.repositories.articles import AUTHORED_SOURCE, create_article
from app.repositories.categories import get_category_by_slug
from app.services.html_sanitize import first_media_src, plain_text, sanitize_article_html

ARTICLE_TYPES = ("newsletter", "column", "guide")
CURATION_SLUG = "curation"


def publish_authored_article(
    db: Session,
    cache: VersionedCache,
    member: Member,
    *,
    article_type: str,
    title: str,
    summary: str | None,
    body_html: str,
) -> Article:
    clean_title = _title(title)
    clean_type = _article_type(article_type)
    html = sanitize_article_html(body_html)
    text = plain_text(html)
    if not text and first_media_src(html) is None:
        raise ValueError("본문을 입력해 주세요")
    category = get_category_by_slug(db, CURATION_SLUG)
    if category is None:
        raise ValueError("큐레이션 카테고리가 없습니다")
    article = create_article(
        db,
        category_id=category.id,
        article_type=clean_type,
        title=clean_title,
        summary=_summary(summary, text, clean_title),
        body_html=html,
        author_name=member.nickname,
        source_type=AUTHORED_SOURCE,
        thumbnail_url=first_media_src(html),
        read_minutes=_read_minutes(text),
        published_at=datetime.now(timezone.utc),
    )
    cache.bump_version()
    return article


def _article_type(value: str) -> str:
    if value not in ARTICLE_TYPES:
        raise ValueError("카테고리는 뉴스레터, 컬럼, 가이드 중 하나여야 합니다")
    return value


def _title(value: str) -> str:
    title = (value or "").strip()
    if not title or len(title) > 300:
        raise ValueError("제목은 1~300자여야 합니다")
    return title


def _summary(summary: str | None, text: str, title: str) -> str:
    chosen = (summary or "").strip() or text or title
    return chosen[:500]


def _read_minutes(text: str) -> int:
    if not text:
        return 1
    return max(1, min(60, (len(text) + 499) // 500))
