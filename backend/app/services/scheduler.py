"""백그라운드 스케줄러: 인제스트(1분) + 브런치 수집(12시간)."""
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.cache import VersionedCache
from app.config import get_settings
from app.db import get_engine
from app.services.brunch import collect_and_pick
from app.services.brunch_fetcher import fetch_candidates, filter_by_window
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
            candidates = fetch_candidates(base_url=settings.brunch_base_url)
            # 선정 규칙: '해당 기간(12시간) 동안' 발행된 글만 대상으로 한다
            windowed = filter_by_window(candidates, window_start, window_end)
            collect_and_pick(
                db, cache,
                candidates=windowed,
                window_start=window_start, window_end=window_end,
            )
        except Exception:
            logger.exception("브런치 수집 작업 실패")


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
        run_brunch_job,
        "interval",
        hours=settings.brunch_collect_interval_hours,
        id="brunch_collect",
        args=[cache],
    )
    return scheduler
