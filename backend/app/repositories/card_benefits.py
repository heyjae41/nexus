"""Card.Pick 카드 혜택 리포지토리."""
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import CardBenefit


def list_active_benefits(
    db: Session,
    company: str | None = None,
) -> list[CardBenefit]:
    """진행 중(시작일 도래 & 종료일 미도래) 혜택을 최신 시작일 순으로 반환한다.

    수집기가 날짜 미상 이벤트에 기본값(수집일~당해 12/31)을 채우므로 신규 행은
    항상 날짜를 갖는다 — NULL 허용 분기는 과거 행 호환용이다."""
    today = date.today()
    stmt = select(CardBenefit).where(
        CardBenefit.status == "published",
        or_(
            CardBenefit.event_start_date.is_(None),
            CardBenefit.event_start_date <= today,
        ),
        or_(CardBenefit.event_end_date.is_(None), CardBenefit.event_end_date >= today),
    )
    if company:
        stmt = stmt.where(CardBenefit.card_company == company)
    stmt = stmt.order_by(
        CardBenefit.event_start_date.desc().nulls_last(), CardBenefit.id.desc()
    )
    return list(db.scalars(stmt))
