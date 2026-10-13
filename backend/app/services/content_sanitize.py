"""인제스트(텔레그램 발행) 글의 본문·키비주얼 정화.

본문·키비주얼은 LLM 이 생성하므로 프롬프트 인젝션으로 <svg onload> 같은 핸들러가 섞일 수
있다(보안 점검 2026-10 HIGH 3). 저장 전에 허용 목록으로 거른다. 키비주얼은 SMIL 애니메이션
SVG 를 그대로 살려야 하므로 SVG 전용 허용 목록을 쓴다.
"""
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import VersionedCache
from app.models import Article
from app.services.html_sanitize import (
    DROP_TAGS,
    Profile,
    is_data_image,
    link_attrs,
    safe_class,
    sanitize_article_html,
    sanitize_html,
)

INGEST_TAGS = frozenset({
    "h1", "h2", "h3", "h4", "p", "br", "hr", "strong", "em", "b", "i", "s", "u", "sup", "sub",
    "ul", "ol", "li", "blockquote", "pre", "code", "a", "img", "figure", "figcaption",
    "table", "thead", "tbody", "tr", "th", "td", "div", "span", "small",
})
KEY_VISUAL_TAGS = frozenset({
    "div", "span", "img", "svg", "g", "path", "rect", "circle", "ellipse", "line", "polyline",
    "polygon", "text", "tspan", "defs", "lineargradient", "radialgradient", "stop", "clippath",
    "mask", "use", "symbol", "pattern", "marker", "animate", "animatetransform", "animatemotion",
    "set", "mpath", "filter", "fegaussianblur", "feoffset", "femerge", "femergenode", "feblend",
    "fecolormatrix", "feflood", "fecomposite", "fedropshadow", "title", "desc", "style",
})
KEY_VISUAL_DROP = frozenset(DROP_TAGS - {"style"} | {"foreignobject", "image", "a", "script"})
_ATTR_NAME_RE = re.compile(r"^[a-z][a-z0-9:_-]*$")
# CSS 는 페이지 전체에 적용될 수 있다 — 외부 요청(url/@import/image-set), 이스케이프(\\),
# 전체 화면 오버레이(position:fixed/sticky) 를 막는다. svg 안 애니메이션·색상 규칙은 통과.
_CSS_DANGER_RE = re.compile(
    r"url\s*\(|@import|@font-face|@namespace|image-set|image\s*\(|expression\s*\(|javascript:"
    r"|behavior\s*:|-moz-binding|position\s*:\s*(fixed|sticky)|\\|<",
    re.I,
)
_NUMERIC_RE = re.compile(r"^\d{1,5}$")
_HREF_ATTRS = ("href", "xlink:href")
_LOCAL_URL_REF_RE = re.compile(r"^url\(\s*#[\w:.-]+\s*\)$", re.I)
_CONTROL_RE = re.compile(r"[\x00-\x20]")


def sanitize_ingest_html(raw: str) -> str:
    return sanitize_html(raw, INGEST_PROFILE)


def sanitize_key_visual_html(raw: str | None) -> str | None:
    if not raw:
        return raw
    return sanitize_html(raw, KEY_VISUAL_PROFILE) or None


# --- 인제스트 본문 ---

def _ingest_img_src(value) -> str | None:
    src = str(value or "").strip()
    if src.startswith("/api/media/") and ".." not in src and "\\" not in src:
        return src
    if src.lower().startswith(("http://", "https://")) or is_data_image(src):
        return src
    return None


def _ingest_img_attrs(tag) -> dict:
    src = _ingest_img_src(tag.get("src"))
    if src is None:
        return {}
    attrs = {"src": src}
    alt = str(tag.get("alt") or "").strip()
    if alt:
        attrs["alt"] = alt[:200]
    for name in ("width", "height"):
        if _NUMERIC_RE.match(str(tag.get(name) or "")):
            attrs[name] = str(tag.get(name))
    if str(tag.get("loading") or "") in ("lazy", "eager"):
        attrs["loading"] = str(tag.get("loading"))
    return attrs


def _ingest_attrs(tag) -> dict:
    attrs: dict = {}
    cls = safe_class(tag.get("class"))
    if cls:
        attrs["class"] = cls
    if tag.name == "a":
        attrs.update(link_attrs(tag))
    elif tag.name == "img":
        attrs.update(_ingest_img_attrs(tag))
    return attrs


INGEST_PROFILE = Profile(
    allowed_tags=INGEST_TAGS,
    attrs=_ingest_attrs,
    keep=lambda tag: tag.name != "img" or "src" in tag.attrs,
)


# --- 키비주얼(SVG) ---

def _unsafe_value(value: str) -> bool:
    compact = _CONTROL_RE.sub("", value).lower()  # java\tscript: 같은 제어문자 삽입 무력화
    return "javascript:" in compact or "<" in compact


def _unsafe_attribute_target(value: str) -> bool:
    """SMIL attributeName 이 href 계열·style 이면 링크 주입/CSS 주입 벡터다."""
    target = value.strip().lower()
    return target in _HREF_ATTRS or target.endswith(":href") or target == "style"


def _presentation_value(value: str) -> str | None:
    """fill/filter/mask 등의 url() 은 문서 내부 참조(#id)만 허용한다."""
    if "url(" in value.lower() and not _LOCAL_URL_REF_RE.match(value.strip()):
        return None
    return value


def _kv_href(tag, name: str, value: str) -> str | None:
    if tag.name == "img" and name == "src":
        return _ingest_img_src(value)
    return value if value.startswith("#") else None


# 이름별 특수 처리 — 그 외 속성(프레젠테이션·SMIL 타이밍 등)은 값 검사만 거쳐 그대로 둔다
_KV_SPECIAL_ATTRS = {
    "href": lambda tag, v: _kv_href(tag, "href", v.strip()),
    "xlink:href": lambda tag, v: _kv_href(tag, "xlink:href", v.strip()),
    "src": lambda tag, v: _kv_href(tag, "src", v.strip()),
    # <animate attributeName="href|x:href|style" ...> 차단
    "attributename": lambda tag, v: None if _unsafe_attribute_target(v) else v,
    "style": lambda tag, v: None if _CSS_DANGER_RE.search(v) else v,
    "class": lambda tag, v: safe_class(v),
}


def _kv_attr_value(tag, name: str, value: str) -> str | None:
    """키비주얼 속성 하나의 안전한 값. None 이면 버린다."""
    if name.startswith("on") or not _ATTR_NAME_RE.match(name) or _unsafe_value(value):
        return None
    special = _KV_SPECIAL_ATTRS.get(name)
    return special(tag, value) if special else _presentation_value(value)


def _kv_attrs(tag) -> dict:
    attrs: dict = {}
    for raw_name, raw in tag.attrs.items():
        name = raw_name.lower()
        value = " ".join(raw) if isinstance(raw, list) else str(raw or "")
        safe = _kv_attr_value(tag, name, value)
        if safe is not None:
            attrs[name] = safe
    return attrs


def _kv_keep(tag) -> bool:
    if tag.name == "style":
        # svg 밖의 <style> 은 SPA 전체에 적용된다 — svg 안에서만, 위험 CSS 없이
        return tag.find_parent("svg") is not None and not _CSS_DANGER_RE.search(tag.get_text())
    if tag.name in ("animate", "set", "animatetransform", "animatemotion"):
        return "attributename" in tag.attrs or tag.name != "animate"
    if tag.name == "img":
        return "src" in tag.attrs
    return True


KEY_VISUAL_PROFILE = Profile(
    allowed_tags=KEY_VISUAL_TAGS,
    drop_tags=KEY_VISUAL_DROP,
    attrs=_kv_attrs,
    keep=_kv_keep,
)


# --- 기존 저장분 재정화 (이번 정화 도입 이전에 저장된 글은 인제스트가 재처리하지 않는다) ---

@dataclass(frozen=True)
class ResanitizeResult:
    checked: int
    changed: int


def _resanitized(article: Article) -> tuple[str | None, str | None]:
    body = article.body_html or ""
    if article.source_type == "authored":
        body = sanitize_article_html(body)
    else:
        body = sanitize_ingest_html(body)
    return (body or None), sanitize_key_visual_html(article.key_visual_html)


def resanitize_stored_articles(db: Session, cache: VersionedCache) -> ResanitizeResult:
    """internal(인제스트)·authored 글의 본문·키비주얼을 현재 정책으로 다시 거른다. 바뀐 글만 갱신."""
    stmt = select(Article).where(Article.source_type.in_(("internal", "authored")))
    checked = changed = 0
    for article in db.scalars(stmt):
        checked += 1
        body, key_visual = _resanitized(article)
        if body == article.body_html and key_visual == article.key_visual_html:
            continue
        article.body_html = body
        article.key_visual_html = key_visual
        changed += 1
    if changed:
        db.commit()
        cache.bump_version()
    return ResanitizeResult(checked=checked, changed=changed)
