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
        # rank 우선: 각 소스 카테고리의 상위권이 섞여 노출된다 (rank 는 카테고리별 1부터).
        # 홈 '지금 뜨는 클래스'가 한 카테고리로 고정되지 않게 하는 기준 — 동률은 카테고리 우선순위.
        # 0 이하 rank(비정상 데이터)는 상단 장악을 막기 위해 맨 뒤로 보낸다.
        .order_by(
            case((Course.source_rank <= 0, 1), else_=0),
            Course.source_rank,
            category_order,
            Course.id,
        )
        .offset((page - 1) * size)
        .limit(size)
    ))
    return CoursePage(items, total, page, size)
