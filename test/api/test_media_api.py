"""미디어 서빙·복구 API — /api/media 는 settings.media_dir 에서 서빙되고 복구 엔드포인트가 있다."""
from pathlib import Path

from app.services.image_store import save_article_image

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def test_media_mount_serves_files_written_under_media_dir(client, _isolated_media):
    url = save_article_image(PNG, "image/png")
    assert (Path(_isolated_media) / url.removeprefix("/api/media/")).exists()
    res = client.get(url)
    assert res.status_code == 200
    assert res.content == PNG
    assert "sandbox" in res.headers["content-security-policy"]


def test_internal_media_backfill_endpoint(client, seed, _isolated_media):
    seed(client)
    res = client.post("/api/internal/media/backfill")
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert set(data) == {"checked", "restored", "failed"}
