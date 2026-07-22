"""수집형 클래스 후보의 공통 필드와 DB 매핑."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CourseCandidate:
    source_id: str
    source_category_code: str
    source_category_name: str
    source_category_url: str
    source_rank: int
    title: str
    summary: str | None
    source_url: str
    thumbnail_url: str | None
    sub_category_name: str | None
    format_name: str | None
    qualification: str | None
    running_time_minutes: int | None
    sale_price: int | None
    list_price: int | None
    badges: tuple[str, ...]


def course_values(candidate: CourseCandidate, *, source_type: str) -> dict:
    return {
        "source_type": source_type,
        "source_category_code": candidate.source_category_code,
        "source_category_name": candidate.source_category_name,
        "source_category_url": candidate.source_category_url,
        "source_rank": candidate.source_rank,
        "title": candidate.title,
        "summary": candidate.summary,
        "source_url": candidate.source_url,
        "thumbnail_url": candidate.thumbnail_url,
        "sub_category_name": candidate.sub_category_name,
        "format_name": candidate.format_name,
        "qualification": candidate.qualification,
        "running_time_minutes": candidate.running_time_minutes,
        "sale_price": candidate.sale_price,
        "list_price": candidate.list_price,
        "badges": "|".join(candidate.badges),
        "status": "published",
    }
