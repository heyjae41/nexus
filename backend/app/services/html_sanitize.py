"""직접 작성 글 HTML 허용 목록. 스크립트·이벤트 핸들러는 저장 전에 제거한다."""
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Comment

ALLOWED_TAGS = {
    "p", "br", "h2", "h3", "strong", "em", "s", "u",
    "ul", "ol", "li", "blockquote", "pre", "code", "a", "img", "hr",
}
DROP_TAGS = {"script", "style", "iframe", "object", "embed", "form", "input", "textarea"}


def sanitize_article_html(raw: str) -> str:
    soup = BeautifulSoup(raw or "", "html.parser")
    _strip_comments(soup)
    for tag in list(soup.find_all(True)):
        _clean_tag(tag)
    return _fragment(soup)


def _strip_comments(soup) -> None:
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()


def _clean_tag(tag) -> None:
    if _detached(tag):
        return
    if tag.name in DROP_TAGS:
        tag.decompose()
        return
    if tag.name not in ALLOWED_TAGS:
        tag.unwrap()
        return
    tag.attrs = _safe_attrs(tag)
    if tag.name == "img" and "src" not in tag.attrs:
        tag.decompose()


def _detached(tag) -> bool:
    return getattr(tag, "decomposed", False) or tag.parent is None


def _fragment(soup) -> str:
    root = soup.body or soup
    return "".join(str(node) for node in root.children).strip()


def plain_text(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def first_media_src(html: str) -> str | None:
    image = BeautifulSoup(html or "", "html.parser").find("img")
    if image is None:
        return None
    return image.get("src") or None


def _safe_attrs(tag) -> dict:
    if tag.name == "a":
        href = _safe_href(tag.get("href"))
        if href is None:
            return {}
        attrs = {"href": href, "rel": "noopener noreferrer"}
        if href.lower().startswith("http"):
            attrs["target"] = "_blank"
        return attrs
    if tag.name == "img":
        src = _safe_img_src(tag.get("src"))
        if src is None:
            return {}
        alt = str(tag.get("alt") or "").strip()
        return {"src": src, "alt": alt[:200]} if alt else {"src": src}
    return {}


def _safe_href(value) -> str | None:
    href = str(value or "").strip()
    lowered = href.lower()
    if lowered.startswith(("javascript:", "data:")):
        return None
    if href.startswith("/") or lowered.startswith(("https://", "http://")):
        return href
    return None


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
