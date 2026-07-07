"""공개 API 라우터."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.cache import VersionedCache
from app.db import get_db
from app.repositories.articles import (
    get_article,
    increment_like,
    increment_view,
    list_articles,
)
from app.repositories.categories import list_active_categories
from app.serializers import (
    api_response,
    serialize_article_card,
    serialize_article_detail,
    serialize_category,
)

router = APIRouter(prefix="/api")

HOME_SECTION_SIZE = 6


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
        sections = []
        for cat in list_active_categories(db):
            page = list_articles(db, category_slug=cat.slug, page=1, size=HOME_SECTION_SIZE)
            sections.append(
                {
                    "category": serialize_category(cat),
                    "articles": [serialize_article_card(a) for a in page.items],
                    "total": page.total,
                }
            )
        return {"sections": sections}

    return api_response(cache.get_or_set("home", load))


@router.get("/articles")
def articles(
    category: str | None = Query(default=None, max_length=50),
    type: str | None = Query(default=None, max_length=20),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    key = f"articles:list:{category}:{type}:{page}:{size}"

    def load():
        result = list_articles(db, category_slug=category, article_type=type, page=page, size=size)
        return {
            "items": [serialize_article_card(a) for a in result.items],
            "meta": {"total": result.total, "page": result.page, "limit": result.size},
        }

    loaded = cache.get_or_set(key, load)
    return api_response(loaded["items"], meta=loaded["meta"])


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
