"""key-visual 대표 이미지를 정적 파일로 추출해 목록 카드 썸네일 URL 을 만든다.

인제스트 글의 대표 이미지는 key_visual_html 안에 base64 data-URI(<img>) 또는
인라인 <svg> 로만 존재해, 목록/홈 카드가 쓰는 thumbnail_url 에는 노출되지 않는다.
이 모듈이 그 이미지를 media_dir/thumbnails 아래 파일로 저장하고
공개 URL(/api/media/thumbnails/<내용해시>.<ext>)을 돌려준다.

- data-URI 이미지: 디코드해 파일로 저장 → 로컬 URL 반환
- 인라인 svg: 키비주얼 허용목록 새니타이저(content_sanitize.sanitize_key_visual_html)를 거쳐 .svg 저장
  (xmlns 보강해 독립 렌더 가능). /api/media 응답 CSP 하드닝(main.py)과 함께 이중 방어.
- 외부 URL 이미지: 저장하지 않고 그 URL 을 그대로 반환
- 이미지 없음/디코드 실패/용량 초과: None
"""
import base64
import binascii
import hashlib
import re
from pathlib import Path

from bs4 import BeautifulSoup

from app.services.content_sanitize import sanitize_key_visual_html

MEDIA_URL_PREFIX = "/api/media"
THUMBNAIL_SUBDIR = "thumbnails"
# 대표 이미지 최대 크기(디스크필 방지). 콘텐츠 파일은 신뢰되지만 상한을 둔다.
MAX_THUMBNAIL_BYTES = 10 * 1024 * 1024
_SVG_XMLNS = "http://www.w3.org/2000/svg"

_DATA_URI_RE = re.compile(
    r"^data:(?P<mime>image/[\w.+-]+);base64,(?P<data>.+)$", re.DOTALL
)
_MIME_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/svg+xml": "svg",
}


def save_key_visual_thumbnail(key_visual_html: str | None, media_dir: str) -> str | None:
    """key_visual_html 의 대표 이미지를 저장하고 카드용 썸네일 URL 을 반환한다.

    동일 이미지는 내용 해시 파일명으로 한 번만 저장(멱등)한다. 이미지가 없으면 None.
    """
    if not key_visual_html:
        return None
    soup = BeautifulSoup(key_visual_html, "html.parser")

    img = soup.find("img")
    if img is not None:
        src = (img.get("src") or "").strip()
        if src:
            url = _from_img_src(src, media_dir)
            if url is not None:
                return url

    svg = soup.find("svg")
    if svg is not None:
        data = _sanitized_svg_bytes(str(svg))
        if data is None or len(data) > MAX_THUMBNAIL_BYTES:
            return None
        return _store(data, "svg", media_dir)

    return None


def _from_img_src(src: str, media_dir: str) -> str | None:
    match = _DATA_URI_RE.match(src)
    if not match:
        # data-URI 가 아니면 이미 접근 가능한 URL — 그대로 사용
        return src
    ext = _MIME_EXT.get(match.group("mime").lower())
    if ext is None:
        return None
    payload = re.sub(r"\s+", "", match.group("data"))
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return None
    if not data or len(data) > MAX_THUMBNAIL_BYTES:
        return None
    if ext == "svg":
        # data-URI 로 실려온 svg 도 인라인 svg 와 동일하게 위생처리한다
        cleaned = _sanitized_svg_bytes(data.decode("utf-8", errors="replace"))
        return None if cleaned is None else _store(cleaned, "svg", media_dir)
    return _store(data, ext, media_dir)


def _sanitized_svg_bytes(markup: str) -> bytes | None:
    """키비주얼 허용목록(SMIL 애니메이션 허용, script·image·외부 url·이벤트 속성 제거)을 거친 svg 바이트.

    블록리스트는 animate href·<style> url()·entity 인코딩 같은 틈새를 놓친다 — 저장 정책과 같은
    허용목록을 쓴다. svg 가 남지 않으면 None."""
    cleaned = sanitize_key_visual_html(markup)
    svg = BeautifulSoup(cleaned or "", "html.parser").find("svg")
    if svg is None:
        return None
    if not svg.get("xmlns"):
        svg["xmlns"] = _SVG_XMLNS
    return svg.encode()


def _store(data: bytes, ext: str, media_dir: str) -> str:
    digest = hashlib.sha256(data).hexdigest()[:16]
    filename = f"{digest}.{ext}"
    thumb_dir = Path(media_dir) / THUMBNAIL_SUBDIR
    thumb_dir.mkdir(parents=True, exist_ok=True)
    path = thumb_dir / filename
    if not path.exists():
        _write_once(path, data)
    return f"{MEDIA_URL_PREFIX}/{THUMBNAIL_SUBDIR}/{filename}"


def _write_once(path: Path, data: bytes) -> None:
    """새 파일로만 쓴다 — S3 마운트는 rename·덮어쓰기를 거부하므로 exists 검사와 쓰기 사이에
    다른 프로세스(스케줄러·즉시 인제스트·CronJob)가 먼저 썼다면 그 파일을 그대로 쓴다."""
    try:
        with path.open("xb") as fh:
            fh.write(data)
    except FileExistsError:
        return
    except OSError:
        if not path.exists():
            raise
