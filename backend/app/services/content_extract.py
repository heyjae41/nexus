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


def extract_content(html: str) -> ExtractedContent:
    soup = BeautifulSoup(html, "html.parser")

    key_visual = soup.select_one(".key-visual, [data-key-visual]")
    key_visual_html = key_visual.decode() if key_visual else None
    if key_visual:
        key_visual.extract()

    article = soup.find("article") or soup.body or soup
    body_html = article.decode_contents().strip() if article else None

    title_el = soup.select_one("h1, [data-title]")
    meta_author = soup.select_one('meta[name="author"]')
    meta_minutes = soup.select_one('meta[name="read-minutes"]')

    text = article.get_text(" ", strip=True) if article else ""
    summary = text[:SUMMARY_MAX] or None

    return ExtractedContent(
        title=title_el.get_text(strip=True) if title_el else None,
        summary=summary,
        body_html=body_html,
        key_visual_html=key_visual_html,
        author=meta_author["content"] if meta_author else None,
        read_minutes=int(meta_minutes["content"]) if meta_minutes else None,
    )
