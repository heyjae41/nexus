"""어드민 본문 이미지를 media 디렉터리에 저장한다."""
import secrets
from pathlib import Path

from app.config import get_settings

MAX_IMAGE_BYTES = 5 * 1024 * 1024
_SIGNATURES = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/gif": (b"GIF87a", b"GIF89a"),
    "image/webp": (b"RIFF",),
}
_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp"}


def save_article_image(data: bytes, content_type: str | None) -> str:
    kind = _validated_type(data, content_type)
    root = Path(get_settings().media_dir) / "authored"
    root.mkdir(parents=True, exist_ok=True)
    name = f"{secrets.token_hex(16)}.{_EXT[kind]}"
    (root / name).write_bytes(data)
    return f"/api/media/authored/{name}"


def _validated_type(data: bytes, content_type: str | None) -> str:
    if not data:
        raise ValueError("이미지 파일을 선택해 주세요")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("이미지는 5MB 이하여야 합니다")
    kind = (content_type or "").split(";", 1)[0].strip().lower()
    if kind not in _SIGNATURES or not _matches(data, kind):
        raise ValueError("png, jpg, gif, webp 이미지만 올릴 수 있습니다")
    return kind


def _matches(data: bytes, kind: str) -> bool:
    if kind == "image/webp":
        return data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    return any(data.startswith(sig) for sig in _SIGNATURES[kind])
