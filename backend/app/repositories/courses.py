"""수집형 클래스 목록 조회."""
from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Course


@dataclass(frozen=True)
class CoursePage:
    items: list[Course]
    total: int
    page: int
    size: int


def list_courses(
    db: Session,
    *,
    category: str | None = None,
    page: int = 1,
    size: int = 20,
) -> CoursePage:
    conditions = [Course.status == "published"]
    if category:
        conditions.append(Course.source_category_code == category)
    total = db.scalar(select(func.count(Course.id)).where(*conditions)) or 0
    category_order = case(
        (Course.source_category_code == "DATASCIENCEDL", 1),
        (Course.source_category_code == "AICREATIVE", 2),
        (Course.source_category_code == "BIZ", 3),
        (Course.source_category_code == "DAKER", 4),
        (Course.source_category_code == "DACON", 5),
        else_=9,
    )
    items = list(db.scalars(
        select(Course)
        .where(*conditions)
        .order_by(category_order, Course.source_rank, Course.id)
        .offset((page - 1) * size)
        .limit(size)
    ))
    return CoursePage(items, total, page, size)
