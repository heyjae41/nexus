"""글 리포지토리."""
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

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
