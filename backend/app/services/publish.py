"""글 발행 서비스 — DB 반영과 캐시 무효화를 한 경로로 묶는다.

인제스트/브런치 수집 등 '신규 글 등록'은 반드시 이 함수를 거쳐
캐시 버전을 올려(즉시 무효화) 다음 조회가 항상 최신을 가져오게 한다.
"""
from sqlalchemy.orm import Session

from app.cache import VersionedCache
from app.models import Article
from app.repositories.articles import create_article
from app.repositories.categories import get_category_by_slug


def publish_article(
    db: Session,
    cache: VersionedCache,
    *,
    category_slug: str,
    **fields,
) -> Article:
    category = get_category_by_slug(db, category_slug)
    if category is None:
        raise ValueError(f"존재하지 않는 카테고리: {category_slug}")
    article = create_article(db, category_id=category.id, **fields)
    cache.bump_version()
    return article
