"""Card.Pick 수집기 — 카드사 여행 혜택 후보를 card_benefits 에 반영한다.

밋업 수집기와 같은 패턴(source_id/detail_url 중복 제거, 신규 시 캐시 무효화,
수집 이력 기록)에 더해, 진행 중 이벤트의 기간/이미지/대상카드 변경을 갱신한다.
"""
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import VersionedCache
from app.models import CardBenefit, CardBenefitCollectRun
from app.services.card_benefit_fetcher import CardBenefitCandidate
from app.services.collect_batch import apply_collect_batch

logger = logging.getLogger(__name__)

# 변경 감지·갱신 대상 필드 (후보 → DB 행 동일 이름)
_UPDATABLE_FIELDS = (
    "title", "event_period", "event_start_date", "event_end_date",
    "target_cards", "benefit_tags", "image_url",
)


@dataclass(frozen=True)
class CardBenefitCollectResult:
    candidates: int
    added: int
    updated: int


def _row(c: CardBenefitCandidate) -> CardBenefit:
    return CardBenefit(
        source_id=c.source_id,
        card_company=c.card_company,
        title=c.title,
        event_period=c.event_period,
        event_start_date=c.event_start_date,
        event_end_date=c.event_end_date,
        target_cards=c.target_cards,
        benefit_tags=c.benefit_tags,
        detail_url=c.detail_url,
        image_url=c.image_url,
    )


def _apply_updates(existing: CardBenefit, c: CardBenefitCandidate) -> bool:
    changed = False
    for field in _UPDATABLE_FIELDS:
        new = getattr(c, field)
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


def collect_card_benefits(
    db: Session,
    cache: VersionedCache,
    *,
    candidates: list[CardBenefitCandidate],
) -> CardBenefitCollectResult:
    existing_by_id, existing_urls = _load_existing(db, candidates)
    fresh, updated = _split_fresh_and_update(candidates, existing_by_id, existing_urls)

    if updated:
        db.commit()

    added = apply_collect_batch(
        db,
        rows=((c.detail_url, _row(c)) for c in fresh),
        run_model=CardBenefitCollectRun,
        candidates_count=len(candidates),
        label="Card.Pick",
    )

    if added or updated:
        cache.bump_version()
        logger.info("Card.Pick 반영: 신규 %d건, 갱신 %d건 → 캐시 무효화", added, updated)
    return CardBenefitCollectResult(
        candidates=len(candidates), added=added, updated=updated
    )
