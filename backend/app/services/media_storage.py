"""영구 미디어 저장소(settings.media_dir) 기동 검증과 복구.

배포 파드는 /app/media 에 S3 를 마운트한다. 마운트가 빠진 채 기동하면 mkdir 이
휘발성 디렉터리를 조용히 만들어 "재기동 후 이미지 소실" 사고가 재발하므로,
MEDIA_REQUIRE_MOUNT=true 환경에서는 마운트가 없으면 기동을 거부한다.
"""
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Article
from app.services.thumbnails import MEDIA_URL_PREFIX, THUMBNAIL_SUBDIR, save_key_visual_thumbnail

logger = logging.getLogger(__name__)
_THUMBNAIL_URL_PREFIX = f"{MEDIA_URL_PREFIX}/{THUMBNAIL_SUBDIR}/"


def ensure_media_storage(media_dir: str, require_mount: bool) -> str:
    """미디어 루트를 준비하고 상태 한 줄을 돌려준다. 마운트 필수인데 없으면 RuntimeError."""
    root = Path(media_dir)
    mounted = os.path.ismount(root)
    if require_mount and not mounted:
        raise RuntimeError(
            f"미디어 저장소 {root} 가 마운트되어 있지 않습니다 — 영구 볼륨(S3) 마운트를 확인하거나 "
            "MEDIA_REQUIRE_MOUNT=false 로 기동하세요"
        )
    root.mkdir(parents=True, exist_ok=True)
    status = f"[media] dir={root} mount={'yes' if mounted else 'no'}"
    logger.info(status)
    return status


@dataclass(frozen=True)
class BackfillResult:
    checked: int
    restored: int
    failed: int


def backfill_thumbnails(db: Session, media_dir: str) -> BackfillResult:
    """마운트 이전에 인제스트돼 파일이 사라진 썸네일을 DB 의 key_visual_html 로 재생성한다.

    파일명이 내용 해시라 URL 이 그대로이므로 DB·캐시는 바뀌지 않는다."""
    stmt = select(Article).where(
        Article.key_visual_html.is_not(None),
        Article.thumbnail_url.like(f"{_THUMBNAIL_URL_PREFIX}%"),
    )
    checked = restored = failed = 0
    for article in db.scalars(stmt):
        checked += 1
        path = Path(media_dir) / article.thumbnail_url.removeprefix(f"{MEDIA_URL_PREFIX}/")
        if path.exists():
            continue
        try:
            url = save_key_visual_thumbnail(article.key_visual_html, media_dir)
        except OSError:
            logger.exception("썸네일 복구 실패: article=%s", article.id)
            failed += 1
            continue
        if url == article.thumbnail_url:
            restored += 1
        else:
            logger.warning("썸네일 복구 결과 URL 불일치: article=%s %s → %s", article.id, article.thumbnail_url, url)
            failed += 1
    return BackfillResult(checked=checked, restored=restored, failed=failed)
