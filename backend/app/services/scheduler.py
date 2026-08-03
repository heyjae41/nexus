"""백그라운드 스케줄러: 인제스트(1분) + 브런치 수집(12시간)."""
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.cache import VersionedCache
from app.config import get_settings
from app.db import get_engine
from app.services.brunch import collect_and_pick
from app.services.brunch_fetcher import DEFAULT_KEYWORDS, fetch_candidates, filter_by_window
from app.services.ingest import scan_contents_dir

logger = logging.getLogger(__name__)


def _session():
    from sqlalchemy.orm import Session

    return Session(bind=get_engine(), expire_on_commit=False)


def run_ingest_job(cache: VersionedCache) -> None:
    settings = get_settings()
    with _session() as db:
        try:
            result = scan_contents_dir(db, cache, settings.contents_dir)
            if result.ingested:
                logger.info("인제스트: %d건 등록", result.ingested)
        except Exception:
            logger.exception("인제스트 작업 실패")


def run_brunch_job(cache: VersionedCache) -> None:
    settings = get_settings()
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(hours=settings.brunch_collect_interval_hours)
    with _session() as db:
        try:
            for keyword in DEFAULT_KEYWORDS:
                candidates = fetch_candidates(
                    base_url=settings.brunch_base_url,
                    keywords=(keyword,),
                )
                # 선정 규칙: 키워드별로 해당 기간(12시간)에 발행된 글 1건
                windowed = filter_by_window(candidates, window_start, window_end)
                collect_and_pick(
                    db, cache,
                    candidates=windowed,
                    window_start=window_start, window_end=window_end,
                )
        except Exception:
            logger.exception("브런치 수집 작업 실패")


def run_newsletter_job(cache: VersionedCache) -> None:
    from app.services.newsletter_collector import collect_recent_newsletters

    with _session() as db:
        try:
            collect_recent_newsletters(db, cache)
        except Exception:
            logger.exception("뉴스레터 수집 작업 실패")


def run_meetup_job(cache: VersionedCache) -> None:
    from app.services.meetup_collector import collect_meetups
    from app.services.meetup_fetcher import fetch_meetup_candidates

    settings = get_settings()
    with _session() as db:
        try:
            candidates = fetch_meetup_candidates(
                query=settings.meetup_query,
                categories=settings.meetup_category_list,
                window_days=settings.meetup_window_days,
            )
            collect_meetups(db, cache, candidates=candidates)
        except Exception:
            logger.exception("밋업(event-us) 수집 작업 실패")


def run_luma_job(cache: VersionedCache, category_api_id: str, label: str) -> None:
    from app.services.luma_fetcher import fetch_luma_candidates
    from app.services.meetup_collector import collect_meetups

    settings = get_settings()
    with _session() as db:
        try:
            candidates = fetch_luma_candidates(
                category_api_id, label, window_days=settings.meetup_window_days
            )
            collect_meetups(db, cache, candidates=candidates)
        except Exception:
            logger.exception("luma(%s) 수집 작업 실패", category_api_id)


def run_fastcampus_job(cache: VersionedCache) -> None:
    from app.services.fastcampus_collector import collect_fastcampus_courses
    from app.services.fastcampus_fetcher import fetch_fastcampus_candidates

    with _session() as db:
        try:
            candidates = fetch_fastcampus_candidates()
            collect_fastcampus_courses(db, cache, candidates=candidates)
        except Exception:
            logger.exception("패스트캠퍼스 클래스 수집 작업 실패")


def run_daker_job(cache: VersionedCache) -> None:
    from app.services.class_opportunities import collect_class_opportunities
    from app.services.daker_fetcher import fetch_daker_candidates

    with _session() as db:
        try:
            candidates = fetch_daker_candidates()
            collect_class_opportunities(db, cache, source_type="daker", candidates=candidates)
        except Exception:
            logger.exception("DAKER 해커톤 수집 작업 실패")


def run_dacon_job(cache: VersionedCache) -> None:
    from app.services.class_opportunities import collect_class_opportunities
    from app.services.dacon_fetcher import fetch_dacon_candidates

    with _session() as db:
        try:
            candidates = fetch_dacon_candidates()
            collect_class_opportunities(db, cache, source_type="dacon", candidates=candidates)
        except Exception:
            logger.exception("DACON 경진대회 수집 작업 실패")


def run_card_benefit_job(cache: VersionedCache) -> None:
    from app.services.card_benefit_collector import collect_card_benefits
    from app.services.card_benefit_fetcher import ISSUER_FETCHERS

    with _session() as db:
        # 한 카드사 실패가 다른 카드사 수집을 막지 않도록 분리 실행한다
        for name, fetch in ISSUER_FETCHERS.items():
            try:
                collect_card_benefits(db, cache, candidates=fetch())
            except Exception:
                logger.exception("Card.Pick %s 수집 작업 실패", name)


def run_collect_chain_job(cache: VersionedCache) -> None:
    """12시간 주기 수집 체인 — 브런치부터 순차 실행, 한 단계 실패해도 다음 단계 진행."""
    settings = get_settings()
    steps = [
        ("brunch", lambda: run_brunch_job(cache)),
        ("newsletter", lambda: run_newsletter_job(cache)),
        ("event-us", lambda: run_meetup_job(cache)),
    ]
    steps += [
        (f"luma:{label}", lambda cid=cid, label=label: run_luma_job(cache, cid, label))
        for cid, label in settings.luma_category_pairs
    ]
    steps.extend([
        ("fastcampus", lambda: run_fastcampus_job(cache)),
        ("daker", lambda: run_daker_job(cache)),
        ("dacon", lambda: run_dacon_job(cache)),
        ("cardpick", lambda: run_card_benefit_job(cache)),
    ])
    for name, step in steps:
        try:
            step()
        except Exception:
            logger.exception("수집 체인 단계 실패: %s (다음 단계 계속)", name)


def build_scheduler(cache: VersionedCache) -> BackgroundScheduler:
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_ingest_job,
        "interval",
        seconds=settings.ingest_interval_seconds,
        id="ingest_contents",
        args=[cache],
    )
    scheduler.add_job(
        run_collect_chain_job,
        "interval",
        hours=settings.collect_chain_interval_hours,
        id="collect_chain",
        args=[cache],
    )
    return scheduler
