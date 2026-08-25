"""Card.Pick 카드 혜택 리포지토리."""
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import CardBenefit


def list_active_benefits(
    db: Session,
    company: str | None = None,
    country: str | None = None,
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
    rows = list(db.scalars(stmt))
    if country:
        rows = _filter_by_country(rows, country)
    return rows


def _filter_by_country(rows: list[CardBenefit], country: str) -> list[CardBenefit]:
    """선택 국가와 해외공통 혜택을 반환하고 지정 국가를 먼저 정렬한다."""
    from app.services.card_benefit_geo import (
        expand_country_filter, match_rank, normalize_country_codes,
    )

    allowed = expand_country_filter(country)
    picked = [
        (match_rank(normalize_country_codes(r.countries), country), i, r)
        for i, r in enumerate(rows)
        if allowed.intersection(normalize_country_codes(r.countries))
    ]
    picked.sort(key=lambda item: (item[0], item[1]))  # 명시 우선, 기존 정렬 유지
    return [r for _, _, r in picked]
