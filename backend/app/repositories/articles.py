"""글 리포지토리."""
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, aliased

from app.models import Article, Category


@dataclass(frozen=True)
class Page:
    items: list[Article]
    total: int
    page: int
    size: int


def create_article(db: Session, **fields) -> Article:
    article = Article(**fields)
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def get_article(db: Session, article_id: int) -> Article | None:
    return db.get(Article, article_id)


def list_articles(
    db: Session,
    category_slug: str | None = None,
    article_type: str | None = None,
    page: int = 1,
    size: int = 12,
) -> Page:
    conditions = [Article.status == "published"]
    if category_slug is not None:
        conditions.append(Category.slug == category_slug)
    if article_type is not None:
        conditions.append(Article.article_type == article_type)

    base = select(Article).join(Category).where(*conditions)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = list(
        db.scalars(
            base.order_by(Article.published_at.desc(), Article.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    )
    return Page(items=items, total=total, page=page, size=size)


def list_articles_by_category(
    db: Session, category_ids: list[int], size: int
) -> dict[int, tuple[list[Article], int]]:
    """카테고리별 최신 글 top-N 과 총 개수를 단일 쿼리(윈도우 함수)로 로드.

    홈 화면이 캐시 미스 시 카테고리 수만큼 COUNT+SELECT 를 반복(N+1형)하지 않도록 한다.
    반환: {category_id: ([Article...], total)}
    """
    if not category_ids:
        return {}
    rn = (
        func.row_number()
        .over(
            partition_by=Article.category_id,
            order_by=(Article.published_at.desc(), Article.id.desc()),
        )
        .label("rn")
    )
    total = func.count().over(partition_by=Article.category_id).label("total")
    sub = (
        select(Article, rn, total)
        .where(Article.status == "published", Article.category_id.in_(category_ids))
        .subquery()
    )
    ranked = aliased(Article, sub)
    rows = db.execute(
        select(ranked, sub.c.total)
        .where(sub.c.rn <= size)
        .order_by(sub.c.category_id, sub.c.rn)
    ).all()

    result: dict[int, tuple[list[Article], int]] = {}
    for article, cat_total in rows:
        items, _ = result.setdefault(article.category_id, ([], cat_total))
        items.append(article)
    return result


def increment_view(db: Session, article_id: int) -> None:
    db.execute(
        update(Article)
        .where(Article.id == article_id)
        .values(view_count=Article.view_count + 1)
    )
    db.commit()


def increment_like(db: Session, article_id: int) -> int | None:
    article = db.get(Article, article_id)
    if article is None:
        return None
    db.execute(
        update(Article)
        .where(Article.id == article_id)
        .values(likes_count=Article.likes_count + 1)
    )
    db.commit()
    db.refresh(article)
    return article.likes_count
