"""내부 실행 API — 스케줄러와 동일 코드 경로의 수동 트리거 (운영/테스트용)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.routes import get_cache
from app.cache import VersionedCache
from app.config import get_settings
from app.db import get_db
from app.serializers import api_response, serialize_article_card
from app.services.brunch import collect_and_pick
from app.services.brunch_fetcher import fetch_candidates, filter_by_window
from app.services.ingest import scan_contents_dir

router = APIRouter(prefix="/api/internal")


@router.post("/ingest/run")
def ingest_run(
    db: Session = Depends(get_db), cache: VersionedCache = Depends(get_cache)
):
    settings = get_settings()
    result = scan_contents_dir(db, cache, settings.contents_dir)
    return api_response(
        {"ingested": result.ingested, "already": result.already, "skipped": result.skipped}
    )


@router.post("/brunch/run")
def brunch_run(
    db: Session = Depends(get_db), cache: VersionedCache = Depends(get_cache)
):
    settings = get_settings()
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(hours=settings.brunch_collect_interval_hours)
    candidates = fetch_candidates(base_url=settings.brunch_base_url)
    windowed = filter_by_window(candidates, window_start, window_end)
    picked = collect_and_pick(
        db, cache,
        candidates=windowed or candidates,
        window_start=window_start, window_end=window_end,
    )
    return api_response(
        {
            "candidates": len(candidates),
            "picked": serialize_article_card(picked) if picked else None,
        }
    )
