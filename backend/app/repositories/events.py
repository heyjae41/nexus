"""밋업 이벤트 리포지토리."""
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import MeetupEvent


@dataclass(frozen=True)
class EventPage:
    items: list[MeetupEvent]
    total: int
    page: int
    size: int


def list_upcoming_events(
    db: Session,
    category: str | None = None,
    page: int = 1,
    size: int = 12,
) -> EventPage:
    """다가오는 밋업을 가까운 일정 순으로 반환한다.

    지난 행사와 일정 미정(event_start IS NULL) 행사는 의도적으로 제외한다 —
    meet.pl 은 '가야할' 일정이 확정된 밋업만 보여준다.
    """
    now = datetime.now(timezone.utc)
    base = select(MeetupEvent).where(
        MeetupEvent.status == "published",
        MeetupEvent.event_start >= now,
    )
    if category:
        base = base.where(MeetupEvent.category == category)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = list(
        db.scalars(
            base.order_by(MeetupEvent.event_start.asc(), MeetupEvent.id.asc())
            .offset((page - 1) * size)
            .limit(size)
        )
    )
    return EventPage(items=items, total=total, page=page, size=size)
