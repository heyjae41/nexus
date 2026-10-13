"""HTML 허용 목록 새니타이저 — 스크립트·이벤트 핸들러는 저장 전에 제거한다.

프로필(허용 태그·속성 정책)을 바꿔 어드민 본문, 인제스트 본문, 키비주얼에 같은 엔진을 쓴다.
보안 점검(2026-10) 회귀 2종: (1) 출력 조립을 str() 로 하면 최상위 텍스트의 이스케이프가
풀린다 → decode_contents 로 재이스케이프. (2) CDATA·선언·PI 노드는 원문 그대로 나간다 → 제거.
"""
import re
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urlparse

from bs4 import BeautifulSoup, CData, Comment, Declaration, Doctype, ProcessingInstruction

ALLOWED_TAGS = frozenset({
    "p", "br", "h2", "h3", "strong", "em", "s", "u",
    "ul", "ol", "li", "blockquote", "pre", "code", "a", "img", "hr",
})
DROP_TAGS = frozenset({"script", "style", "iframe", "object", "embed", "form", "input", "textarea"})
_RAW_NODE_TYPES = (Comment, CData, Declaration, Doctype, ProcessingInstruction)
_CLASS_RE = re.compile(r"^[\w\- ]{1,120}$")
_DATA_IMAGE_RE = re.compile(r"^data:image/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/=\s]+$", re.I)


@dataclass(frozen=True)
class Profile:
    """허용 태그 / 통째로 버릴 태그 / 태그별 안전 속성 계산 / 태그 유지 여부(내용 검사)."""

    allowed_tags: frozenset[str]
    drop_tags: frozenset[str] = DROP_TAGS
    attrs: Callable = field(default=lambda tag: {})
    keep: Callable = field(default=lambda tag: True)


def sanitize_html(raw: str, profile: "Profile") -> str:
    soup = BeautifulSoup(raw or "", "html.parser")
    _strip_raw_nodes(soup)
    for tag in list(soup.find_all(True)):
        _clean_tag(tag, profile)
    return _fragment(soup)


def sanitize_article_html(raw: str) -> str:
    """어드민 에디터 본문 — 업로드한 이미지(/api/media)만 허용하는 가장 좁은 프로필."""
    return sanitize_html(raw, ADMIN_PROFILE)


def _strip_raw_nodes(soup) -> None:
    for node in soup.find_all(string=lambda text: isinstance(text, _RAW_NODE_TYPES)):
        node.extract()


def _clean_tag(tag, profile: Profile) -> None:
    if _detached(tag):
        return
    if tag.name in profile.drop_tags:
        tag.decompose()
        return
    if tag.name not in profile.allowed_tags:
        tag.unwrap()
        return
    tag.attrs = profile.attrs(tag)
    if not profile.keep(tag):
        tag.decompose()


def _detached(tag) -> bool:
    return getattr(tag, "decomposed", False) or tag.parent is None


def _fragment(soup) -> str:
    root = soup.body or soup
    return root.decode_contents().strip()


def plain_text(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def first_media_src(html: str) -> str | None:
    image = BeautifulSoup(html or "", "html.parser").find("img")
    if image is None:
        return None
    return image.get("src") or None


# --- 속성 정책 ---

def safe_href(value) -> str | None:
    href = str(value or "").strip()
    lowered = href.lower()
    if lowered.startswith(("javascript:", "data:")):
        return None
    if href.startswith("/") or lowered.startswith(("https://", "http://")):
        return href
    return None


def link_attrs(tag) -> dict:
    href = safe_href(tag.get("href"))
    if href is None:
        return {}
    attrs = {"href": href, "rel": "noopener noreferrer"}
    if href.lower().startswith("http"):
        attrs["target"] = "_blank"
    return attrs


def safe_class(value) -> str | None:
    cls = " ".join(value) if isinstance(value, list) else str(value or "")
    cls = cls.strip()
    return cls if cls and _CLASS_RE.match(cls) else None


def is_data_image(src: str) -> bool:
    return bool(_DATA_IMAGE_RE.match(src))


def _admin_attrs(tag) -> dict:
    if tag.name == "a":
        return link_attrs(tag)
    if tag.name == "img":
        src = _safe_img_src(tag.get("src"))
        if src is None:
            return {}
        alt = str(tag.get("alt") or "").strip()
        return {"src": src, "alt": alt[:200]} if alt else {"src": src}
    return {}


def _safe_img_src(value) -> str | None:
    path = _media_path(str(value or "").strip())
    if path is None or ".." in path or "\\" in path:
        return None
    return path


def _media_path(src: str) -> str | None:
    if src.startswith("/api/media/"):
        return src.split("?", 1)[0].split("#", 1)[0]
    if not src.lower().startswith(("http://", "https://")):
        return None
    path = urlparse(src).path
    if path.startswith("/api/media/"):
        return path
    return None


ADMIN_PROFILE = Profile(
    allowed_tags=ALLOWED_TAGS,
    attrs=_admin_attrs,
    keep=lambda tag: tag.name != "img" or "src" in tag.attrs,
)
