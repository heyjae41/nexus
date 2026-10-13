"""영구 미디어 저장소(settings.media_dir) 기동 검증과 복구.

배포 파드는 /app/media 에 S3 를 마운트하고 컨테이너는 비루트 계정으로 돈다. 마운트가 빠진 채 기동하면 mkdir 이
휘발성 디렉터리를 조용히 만들어 "재기동 후 이미지 소실" 사고가 재발하므로,
MEDIA_REQUIRE_MOUNT=true 환경에서는 마운트가 없거나 실행 계정이 쓸 수 없으면 기동을 거부한다.
"""
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Article
from app.services.image_store import AUTHORED_SUBDIR
from app.services.thumbnails import MEDIA_URL_PREFIX, THUMBNAIL_SUBDIR, save_key_visual_thumbnail

logger = logging.getLogger(__name__)
_THUMBNAIL_URL_PREFIX = f"{MEDIA_URL_PREFIX}/{THUMBNAIL_SUBDIR}/"


def _is_mount(path: Path) -> bool:
    return os.path.ismount(path)


def _unwritable(root: Path) -> list[Path]:
    """실행 계정이 쓸 수 없는 경로 — 루트와, 이미 있는 하위 저장 디렉터리."""
    candidates = [root, *(root / sub for sub in (AUTHORED_SUBDIR, THUMBNAIL_SUBDIR))]
    return [path for path in candidates if path.is_dir() and not os.access(path, os.W_OK)]


def ensure_media_storage(media_dir: str, require_mount: bool) -> str:
    """미디어 루트를 준비하고 상태 한 줄을 돌려준다. 마운트 필수인데 없거나 쓸 수 없으면 RuntimeError."""
    root = Path(media_dir)
    mounted = _is_mount(root)
    if require_mount and not mounted:
        raise RuntimeError(
            f"미디어 저장소 {root} 가 마운트되어 있지 않습니다 — 영구 볼륨(S3) 마운트를 확인하거나 "
            "MEDIA_REQUIRE_MOUNT=false 로 기동하세요"
        )
    root.mkdir(parents=True, exist_ok=True)
    blocked = _unwritable(root)
    if require_mount and blocked:
        raise RuntimeError(
            f"미디어 저장소 {', '.join(map(str, blocked))} 에 쓰기 권한이 없습니다 (uid={os.geteuid()}) — "
            "마운트 옵션의 uid/gid 가 컨테이너 실행 계정과 맞는지 확인하세요 "
            "(backend.Dockerfile 의 USER 와 PV mountOptions, 로컬은 chown -R)"
        )
    if blocked:
        logger.warning(
            "미디어 저장소 %s 에 쓰기 권한이 없습니다 (uid=%s) — 업로드가 실패합니다",
            ", ".join(map(str, blocked)), os.geteuid(),
        )
    writable = "no" if blocked else "yes"
    status = f"[media] dir={root} mount={'yes' if mounted else 'no'} writable={writable}"
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
