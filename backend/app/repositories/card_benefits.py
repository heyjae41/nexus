"""Card.Pick 카드 혜택 리포지토리."""
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import CardBenefit


def list_active_benefits(
    db: Session,
    company: str | None = None,
) -> list[CardBenefit]:
    """진행 중(종료일 미도래 또는 미상) 혜택을 최신 시작일 순으로 반환한다."""
    today = date.today()
    stmt = select(CardBenefit).where(
        CardBenefit.status == "published",
        or_(CardBenefit.event_end_date.is_(None), CardBenefit.event_end_date >= today),
    )
    if company:
        stmt = stmt.where(CardBenefit.card_company == company)
    stmt = stmt.order_by(
        CardBenefit.event_start_date.desc().nulls_last(), CardBenefit.id.desc()
    )
    return list(db.scalars(stmt))
