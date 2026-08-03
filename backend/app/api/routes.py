"""공개 API 라우터."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.common import PageQuery, cached_page_response, page_query
from app.cache import VersionedCache
from app.db import get_db
from app.repositories.articles import (
    get_article,
    increment_like,
    increment_view,
    latest_articles_per_type,
    list_articles,
    list_articles_by_category,
)
from app.repositories.categories import list_active_categories
from app.serializers import (
    api_response,
    serialize_article_card,
    serialize_article_detail,
    serialize_category,
    serialize_course_card,
    serialize_event_card,
)

router = APIRouter(prefix="/api")

HOME_SECTION_SIZE = 6
# 홈 큐레이션 섹션 노출 순서 — 포맷별 최신 1건씩
HOME_CURATION_FORMATS = ("column", "newsletter", "guide")
EventCategory = Literal["IT/프로그래밍", "AI", "경제/금융"]
ClassCategory = Literal["DATASCIENCEDL", "AICREATIVE", "BIZ", "DAKER", "DACON"]


def get_cache(request: Request) -> VersionedCache:
    return request.app.state.cache


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/categories")
def categories(db: Session = Depends(get_db), cache: VersionedCache = Depends(get_cache)):
    data = cache.get_or_set(
        "categories",
        lambda: [serialize_category(c) for c in list_active_categories(db)],
    )
    return api_response(data)


@router.get("/home")
def home(db: Session = Depends(get_db), cache: VersionedCache = Depends(get_cache)):
    def load():
        # 카테고리 수와 무관하게 고정 쿼리 수로 로드 — N+1형 방지
        # (카테고리 목록 + 섹션 윈도우 + 큐레이션 포맷별 윈도우 1회)
        cats = list_active_categories(db)
        by_cat = list_articles_by_category(db, [c.id for c in cats], HOME_SECTION_SIZE)
        sections = []
        for cat in cats:
            items, total = by_cat.get(cat.id, ([], 0))
            if cat.slug == "curation":
                # 홈 큐레이션 섹션은 포맷별(컬럼→뉴스레터→가이드) 최신 1건씩 —
                # 건수 많은 컬럼이 독점하지 않게 한다. 목록 페이지는 시간순 그대로.
                items = latest_articles_per_type(db, cat.id, HOME_CURATION_FORMATS)
            sections.append(
                {
                    "category": serialize_category(cat),
                    "articles": [serialize_article_card(a) for a in items],
                    "total": total,
                }
            )
        return {"sections": sections}

    return api_response(cache.get_or_set("home", load))


@router.get("/articles")
def articles(
    category: str | None = Query(default=None, max_length=50),
    type: str | None = Query(default=None, max_length=20),
    paging: PageQuery = page_query(12),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    key = f"articles:list:{category}:{type}:{paging.page}:{paging.size}"
    return cached_page_response(
        cache, key,
        lambda: list_articles(
            db, category_slug=category, article_type=type, page=paging.page, size=paging.size
        ),
        serialize_article_card,
    )


@router.get("/classes")
def classes(
    category: ClassCategory | None = Query(default=None),
    paging: PageQuery = page_query(),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    from app.repositories.courses import list_courses

    key = f"classes:list:{category or 'all'}:{paging.page}:{paging.size}"
    return cached_page_response(
        cache, key,
        lambda: list_courses(db, category=category, page=paging.page, size=paging.size),
        serialize_course_card,
    )


@router.get("/events")
def events(
    category: EventCategory | None = Query(default=None),
    paging: PageQuery = page_query(12),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    from app.repositories.events import list_upcoming_events

    key = f"events:list:{category or 'all'}:{paging.page}:{paging.size}"
    return cached_page_response(
        cache, key,
        lambda: list_upcoming_events(db, category=category, page=paging.page, size=paging.size),
        serialize_event_card,
    )


@router.get("/card-benefits")
def card_benefits(
    company: str | None = Query(default=None),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    """Card.Pick — 카드사 해외여행 혜택 목록.

    응답 키는 DB 필수 컬럼명(snake_case) 그대로 — 다른 채널이 그대로 소비한다."""
    from app.repositories.card_benefits import list_active_benefits
    from app.serializers import serialize_card_benefit

    key = f"card_benefits:list:{company or 'all'}"
    data = cache.get_or_set(
        key,
        lambda: [serialize_card_benefit(b) for b in list_active_benefits(db, company=company)],
    )
    return api_response(data, meta={"total": len(data)})


@router.get("/articles/{article_id}")
def article_detail(article_id: int, db: Session = Depends(get_db)):
    article = get_article(db, article_id)
    if article is None or article.status != "published":
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다")
    increment_view(db, article_id)
    db.refresh(article)
    return api_response(serialize_article_detail(article))


@router.post("/articles/{article_id}/like")
def article_like(
    article_id: int,
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    likes = increment_like(db, article_id)
    if likes is None:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다")
    cache.bump_version()  # DB 반영사항은 목록/홈에 즉시 반영한다 (캐시 정책)
    return api_response({"id": article_id, "likesCount": likes})
