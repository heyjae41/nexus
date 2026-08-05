"""Card.Pick 수집기 — 카드사 여행 혜택 후보를 card_benefits 에 반영한다.

밋업 수집기와 같은 패턴(source_id/detail_url 중복 제거, 신규 시 캐시 무효화,
수집 이력 기록)에 더해, 진행 중 이벤트의 기간/이미지/대상카드 변경을 갱신한다.
"""
import logging
from dataclasses import dataclass, replace
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import VersionedCache
from app.models import CardBenefit, CardBenefitCollectRun
from app.services.card_benefit_fetcher import CardBenefitCandidate
from app.services.card_benefit_geo import extract_countries
from app.services.collect_batch import apply_collect_batch

logger = logging.getLogger(__name__)

# 변경 감지·갱신 대상 필드 (후보 → DB 행 동일 이름)
_UPDATABLE_FIELDS = (
    "title", "event_period", "event_start_date", "event_end_date",
    "target_cards", "benefit_summary", "benefit_tags", "image_url", "countries",
)

# 외부 사이트 값이 컬럼 길이를 넘겨 배치 전체가 실패하지 않도록 절단한다
_FIELD_LIMITS = {
    "card_company": 50, "title": 300, "event_period": 100,
    "target_cards": 500, "benefit_summary": 500, "benefit_tags": 200,
    "countries": 200,
    "detail_url": 1000, "image_url": 1000,
}


def _clip(c: CardBenefitCandidate, field: str) -> str | None:
    value = getattr(c, field)
    if value is None:
        return None
    return str(value)[: _FIELD_LIMITS[field]]


@dataclass(frozen=True)
class CardBenefitCollectResult:
    candidates: int
    added: int
    updated: int


def _row(c: CardBenefitCandidate) -> CardBenefit:
    return CardBenefit(
        source_id=c.source_id,
        card_company=_clip(c, "card_company"),
        title=_clip(c, "title"),
        event_period=_clip(c, "event_period"),
        event_start_date=c.event_start_date,
        event_end_date=c.event_end_date,
        target_cards=_clip(c, "target_cards"),
        benefit_summary=_clip(c, "benefit_summary"),
        benefit_tags=_clip(c, "benefit_tags"),
        countries=_clip(c, "countries"),
        detail_url=_clip(c, "detail_url"),
        image_url=_clip(c, "image_url"),
    )


def _apply_updates(existing: CardBenefit, c: CardBenefitCandidate) -> bool:
    changed = False
    for field in _UPDATABLE_FIELDS:
        new = _clip(c, field) if field in _FIELD_LIMITS else getattr(c, field)
        if new is not None and getattr(existing, field) != new:
            setattr(existing, field, new)
            changed = True
    return changed


def _load_existing(db: Session, candidates: list[CardBenefitCandidate]):
    ids = [c.source_id for c in candidates]
    urls = [c.detail_url for c in candidates]
    if not ids:
        return {}, set()
    by_id = {
        b.source_id: b
        for b in db.scalars(select(CardBenefit).where(CardBenefit.source_id.in_(ids)))
    }
    url_set = set(
        db.scalars(select(CardBenefit.detail_url).where(CardBenefit.detail_url.in_(urls)))
    )
    return by_id, url_set


def _split_fresh_and_update(
    candidates: list[CardBenefitCandidate], existing_by_id: dict, existing_urls: set[str]
) -> tuple[list[CardBenefitCandidate], int]:
    fresh: list[CardBenefitCandidate] = []
    updated = 0
    seen_ids: set[str] = set()
    for c in candidates:
        if c.source_id in seen_ids:
            continue
        seen_ids.add(c.source_id)
        existing = existing_by_id.get(c.source_id)
        if existing is not None:
            updated += _apply_updates(existing, c)
            continue
        if c.detail_url in existing_urls:
            continue
        existing_urls.add(c.detail_url)
        fresh.append(c)
    return fresh, updated


def _with_default_dates(c: CardBenefitCandidate) -> CardBenefitCandidate:
    """날짜 정보가 없으면 시작=수집일, 종료=당해년도 12/31 로 채운다.

    '진행 중만 노출' 조회가 날짜 미상 이벤트를 놓치지 않게 하기 위한 규칙."""
    if c.event_start_date and c.event_end_date:
        return c
    today = date.today()
    start = c.event_start_date or today
    end = c.event_end_date or date(today.year, 12, 31)
    period = c.event_period or " ~ ".join(
        d.strftime("%Y.%m.%d") for d in (start, end)
    )
    return replace(
        c, event_start_date=start, event_end_date=end, event_period=period
    )


def _with_countries(c: CardBenefitCandidate) -> CardBenefitCandidate:
    """제목·요약·대상 텍스트에서 대상 지역을 분류해 채운다 (국가별 필터용)."""
    blob = " ".join(
        filter(None, (c.title, c.benefit_summary, c.target_cards, c.geo_text))
    )
    return replace(c, countries=",".join(extract_countries(blob)))


def collect_card_benefits(
    db: Session,
    cache: VersionedCache,
    *,
    candidates: list[CardBenefitCandidate],
) -> CardBenefitCollectResult:
    candidates = [_with_countries(_with_default_dates(c)) for c in candidates]
    existing_by_id, existing_urls = _load_existing(db, candidates)
    fresh, updated = _split_fresh_and_update(candidates, existing_by_id, existing_urls)

    if updated:
        db.commit()

    added = 0
    try:
        added = apply_collect_batch(
            db,
            rows=((c.detail_url, _row(c)) for c in fresh),
            run_model=CardBenefitCollectRun,
            candidates_count=len(candidates),
            label="Card.Pick",
        )
    finally:
        # 갱신분은 이미 커밋됐으므로 배치가 실패해도 캐시는 반드시 무효화한다 (불변식 #1)
        if added or updated:
            cache.bump_version()
            logger.info(
                "Card.Pick 반영: 신규 %d건, 갱신 %d건 → 캐시 무효화", added, updated
            )
    return CardBenefitCollectResult(
        candidates=len(candidates), added=added, updated=updated
    )
