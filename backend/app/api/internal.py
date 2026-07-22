"""내부 실행 API — 스케줄러와 동일 코드 경로의 수동 트리거 (운영/테스트용)."""
from datetime import datetime, timedelta, timezone

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.routes import get_cache
from app.cache import VersionedCache
from app.config import get_settings
from app.db import get_db
from app.serializers import api_response, serialize_article_card
from app.services.brunch import collect_and_pick
from app.services.brunch_fetcher import fetch_candidates, filter_by_window
from app.services.ingest import scan_contents_dir

logger = logging.getLogger(__name__)

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


@router.post("/meetup/run")
def meetup_run(
    db: Session = Depends(get_db), cache: VersionedCache = Depends(get_cache)
):
    from app.services.meetup_collector import collect_meetups
    from app.services.meetup_fetcher import fetch_meetup_candidates

    settings = get_settings()
    try:
        candidates = fetch_meetup_candidates(
            query=settings.meetup_query,
            categories=settings.meetup_category_list,
            window_days=settings.meetup_window_days,
        )
        # luma (AI/TECH) 도 함께 수집한다 — 스케줄 체인과 동일 범위
        from app.services.luma_fetcher import fetch_luma_candidates

        for category_api_id, label in settings.luma_category_pairs:
            candidates += fetch_luma_candidates(
                category_api_id, label, window_days=settings.meetup_window_days
            )
        result = collect_meetups(db, cache, candidates=candidates)
    except IntegrityError:
        # 스케줄러와 동시 실행 경합 — 상대편이 이미 반영했으므로 정상 종료
        logger.info("밋업 동시 수집 감지 — 스케줄러 반영분과 중복")
        return api_response({"candidates": 0, "added": 0, "note": "동시 수집 감지"})
    except (httpx.HTTPError, ValueError) as exc:
        logger.exception("밋업 수동 수집 실패")
        raise HTTPException(status_code=502, detail="밋업 수집에 실패했습니다") from exc
    return api_response({"candidates": result.candidates, "added": result.added})


@router.post("/classes/run")
def classes_run(
    db: Session = Depends(get_db), cache: VersionedCache = Depends(get_cache)
):
    from app.services.fastcampus_collector import collect_fastcampus_courses
    from app.services.fastcampus_fetcher import fetch_fastcampus_candidates

    try:
        candidates = fetch_fastcampus_candidates()
        result = collect_fastcampus_courses(db, cache, candidates=candidates)
    except (httpx.HTTPError, ValueError) as exc:
        logger.exception("패스트캠퍼스 클래스 수동 수집 실패")
        raise HTTPException(status_code=502, detail="클래스 수집에 실패했습니다") from exc
    return api_response({
        "candidates": result.candidates,
        "added": result.added,
        "updated": result.updated,
        "hidden": result.hidden,
    })


@router.post("/brunch/run")
def brunch_run(
    db: Session = Depends(get_db), cache: VersionedCache = Depends(get_cache)
):
    settings = get_settings()
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(hours=settings.brunch_collect_interval_hours)
    try:
        candidates = fetch_candidates(base_url=settings.brunch_base_url)
        # 선정 규칙: '해당 기간(12시간) 동안' 발행된 글만 대상으로 한다
        windowed = filter_by_window(candidates, window_start, window_end)
        picked = collect_and_pick(
            db, cache,
            candidates=windowed,
            window_start=window_start, window_end=window_end,
        )
    except (httpx.HTTPError, ValueError) as exc:
        logger.exception("브런치 수동 수집 실패")
        raise HTTPException(status_code=502, detail="브런치 수집에 실패했습니다") from exc
    return api_response(
        {
            "candidates": len(candidates),
            "picked": serialize_article_card(picked) if picked else None,
        }
    )
