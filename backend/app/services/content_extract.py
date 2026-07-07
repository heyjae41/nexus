"""인제스트 html 에서 본문/키비주얼/메타를 추출한다."""
from dataclasses import dataclass

from bs4 import BeautifulSoup

SUMMARY_MAX = 200


@dataclass(frozen=True)
class ExtractedContent:
    title: str | None
    summary: str | None
    body_html: str | None
    key_visual_html: str | None
    author: str | None
    read_minutes: int | None


def _pop_key_visual(soup: BeautifulSoup) -> str | None:
    element = soup.select_one(".key-visual, [data-key-visual]")
    if element is None:
        return None
    html = element.decode()
    element.extract()
    return html


def _meta_content(soup: BeautifulSoup, name: str) -> str | None:
    element = soup.select_one(f'meta[name="{name}"]')
    return element["content"] if element else None


def _extract_title(soup: BeautifulSoup) -> str | None:
    element = soup.select_one("h1, [data-title]")
    return element.get_text(strip=True) if element else None


def extract_content(html: str) -> ExtractedContent:
    soup = BeautifulSoup(html, "html.parser")
    key_visual_html = _pop_key_visual(soup)

    article = soup.find("article") or soup.body or soup
    body_html = article.decode_contents().strip() if article else None
    text = article.get_text(" ", strip=True) if article else ""
    read_minutes = _meta_content(soup, "read-minutes")

    return ExtractedContent(
        title=_extract_title(soup),
        summary=text[:SUMMARY_MAX] or None,
        body_html=body_html,
        key_visual_html=key_visual_html,
        author=_meta_content(soup, "author"),
        read_minutes=int(read_minutes) if read_minutes else None,
    )
