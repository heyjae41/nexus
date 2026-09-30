"""영구 미디어 저장소(/app/media, S3 마운트) 회귀 가드.

사고(2026-09): 파드 재기동 시 에디터로 올린 이미지가 사라졌다. 컨테이너 파일시스템은
휘발성이고, 코드의 media_dir 기본값이 상대경로(./media)라 실행 위치에 따라 저장 위치가
달라졌다. 인프라가 /app/media 에 S3 를 마운트했으므로 백엔드 이미지는 그 경로를
명시적으로 고정하고, 모든 영구 미디어(에디터 이미지·인제스트 썸네일)는 그 아래로만 쓴다."""
import re
from pathlib import Path

from app.config import Settings
from app.services.image_store import save_article_image
from app.services.thumbnails import save_key_visual_thumbnail

REPO = Path(__file__).resolve().parents[2]
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def test_backend_image_pins_media_dir_to_s3_mount():
    dockerfile = (REPO / "docker" / "backend.Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^ENV\s+MEDIA_DIR=/app/media\s*$", dockerfile, re.M), (
        "backend.Dockerfile 은 MEDIA_DIR=/app/media 를 고정해야 한다 — "
        "파드에는 .env 가 없고 ExternalSecret 은 매핑된 키만 주입한다"
    )


def test_settings_media_dir_from_env_is_absolute(monkeypatch):
    monkeypatch.setenv("MEDIA_DIR", "/app/media")
    assert Settings(_env_file=None).media_dir == "/app/media"


def test_settings_media_dir_relative_default_resolves_to_absolute(monkeypatch, tmp_path):
    monkeypatch.delenv("MEDIA_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    media_dir = Settings(_env_file=None).media_dir
    assert Path(media_dir).is_absolute()
    assert Path(media_dir) == (tmp_path / "media").resolve()


def test_editor_image_is_written_under_media_dir(_isolated_media):
    url = save_article_image(PNG, "image/png")
    assert url.startswith("/api/media/authored/")
    stored = Path(_isolated_media) / url.removeprefix("/api/media/")
    assert stored.read_bytes() == PNG


def test_ingest_thumbnail_is_written_under_media_dir(_isolated_media):
    html = '<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
    url = save_key_visual_thumbnail(html, _isolated_media)
    assert url.startswith("/api/media/thumbnails/")
    assert (Path(_isolated_media) / url.removeprefix("/api/media/")).exists()


def test_media_write_never_overwrites_existing_object(_isolated_media):
    """S3 마운트(mountpoint-s3)는 기존 객체 덮어쓰기를 거부한다 — 같은 내용은 재사용."""
    html = '<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
    first = save_key_visual_thumbnail(html, _isolated_media)
    path = Path(_isolated_media) / first.removeprefix("/api/media/")
    path.chmod(0o444)  # 덮어쓰기 시도 시 PermissionError — S3 마운트와 같은 거동
    second = save_key_visual_thumbnail(html, _isolated_media)
    assert first == second


def test_thumbnail_race_with_another_writer_is_not_an_error(_isolated_media, monkeypatch):
    """두 프로세스(스케줄러·즉시 인제스트·CronJob)가 같은 썸네일을 동시에 쓰면
    S3 마운트는 두 번째 open 을 거부한다 — 이미 생긴 파일을 재사용하고 조용히 넘어간다."""
    from app.services import thumbnails

    html = '<svg xmlns="http://www.w3.org/2000/svg"><circle/></svg>'
    real_open = Path.open

    def racing_open(self, mode="r", *args, **kwargs):
        if "x" in mode:
            real_open(self, "wb").write(b"<svg/>")  # 다른 프로세스가 먼저 씀
            raise FileExistsError(str(self))
        return real_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(thumbnails.Path, "open", racing_open)
    url = save_key_visual_thumbnail(html, _isolated_media)
    assert url.startswith("/api/media/thumbnails/")


def test_settings_rejects_blank_media_dir(monkeypatch):
    """빈 MEDIA_DIR 은 cwd(/app) 전체를 /api/media 로 노출한다 — 기동 자체를 막는다."""
    import pytest

    monkeypatch.setenv("MEDIA_DIR", "  ")
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_backend_image_requires_media_mount():
    dockerfile = (REPO / "docker" / "backend.Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^ENV\s+MEDIA_REQUIRE_MOUNT=true\s*$", dockerfile, re.M)


def test_ensure_media_storage_fails_fast_when_mount_missing(tmp_path):
    """마운트가 빠진 채 기동하면 mkdir 이 휘발성 디렉터리를 조용히 만들어 사고가 재발한다."""
    import pytest

    from app.services.media_storage import ensure_media_storage

    with pytest.raises(RuntimeError, match="/app/media|마운트"):
        ensure_media_storage(str(tmp_path / "media"), require_mount=True)


def test_ensure_media_storage_creates_dir_and_reports_status(tmp_path):
    from app.services.media_storage import ensure_media_storage

    media = tmp_path / "media"
    status = ensure_media_storage(str(media), require_mount=False)
    assert media.is_dir()
    assert str(media) in status and "mount=no" in status


def test_backfill_recreates_missing_thumbnails(db, _isolated_media):
    """마운트 이전에 인제스트된 글의 썸네일 파일은 사라졌지만 key_visual_html 은 DB 에 있다 —
    내용 해시 이름이라 같은 URL 로 재생성된다."""
    from app.models import Category
    from app.repositories.articles import create_article
    from app.services.media_storage import backfill_thumbnails
    from datetime import datetime, timezone

    cat = Category(slug="curation", name="큐레이션", display_order=1)
    db.add(cat)
    db.commit()
    html = '<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'
    url = save_key_visual_thumbnail(html, _isolated_media)
    path = Path(_isolated_media) / url.removeprefix("/api/media/")
    create_article(
        db, category_id=cat.id, article_type="guide", title="t", source_type="internal",
        key_visual_html=html, thumbnail_url=url,
        published_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    create_article(
        db, category_id=cat.id, article_type="column", title="brunch", source_type="brunch",
        source_url="https://brunch.co.kr/@x/1", thumbnail_url="https://t1.kakaocdn.net/c.png",
        published_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
    )
    path.unlink()  # 파드 재기동으로 사라진 상황

    result = backfill_thumbnails(db, _isolated_media)
    assert result.restored == 1 and result.checked == 1
    assert path.read_bytes()
    assert backfill_thumbnails(db, _isolated_media).restored == 0
