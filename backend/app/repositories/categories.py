"""카테고리(메뉴) 조회."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category


def list_active_categories(db: Session) -> list[Category]:
    stmt = (
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.display_order)
    )
    return list(db.scalars(stmt))


def get_category_by_slug(db: Session, slug: str) -> Category | None:
    return db.scalars(select(Category).where(Category.slug == slug)).first()
