"""브런치 키워드 페이지에서 글 후보를 추출한다.

키워드 페이지(https://brunch.co.kr/keyword/{키워드})는 서버렌더링 스크립트에
`var articleList = [...]` JSON 을 포함한다. 이를 파싱해 BrunchCandidate 로 변환한다.
"""
import json
import logging
import re
from datetime import datetime, timezone

import httpx

from app.services.brunch import BrunchCandidate

logger = logging.getLogger(__name__)

ARTICLE_LIST_RE = re.compile(r"var articleList = (\[[\s\S]*?\]);")
DEFAULT_KEYWORDS = ("인공지능",)
FETCH_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NexusBot/1.0)"}


def parse_keyword_page(html: str) -> list[BrunchCandidate]:
    match = ARTICLE_LIST_RE.search(html)
    if match is None:
        return []
    try:
        raw = json.loads(match.group(1))
    except json.JSONDecodeError:
        logger.warning("브런치 articleList JSON 파싱 실패")
        return []
    return [c for c in (_to_candidate(item) for item in raw) if c is not None]


def _to_candidate(item: dict) -> BrunchCandidate | None:
    article = item.get("article") or {}
    profile = article.get("profileId")
    no = article.get("no")
    title = article.get("title")
    if not (profile and no and title):
        return None
    publish_ms = article.get("publishTime")
    published_at = (
        datetime.fromtimestamp(publish_ms / 1000, tz=timezone.utc)
        if publish_ms
        else None
    )
    return BrunchCandidate(
        title=title,
        url=f"https://brunch.co.kr/@{profile}/{no}",
        author=article.get("userName") or profile,
        likes=int(article.get("likeCount") or 0),
        comments=int(article.get("commentCount") or 0),
        summary=article.get("contentSummary") or "",
        published_at=published_at,
    )


def filter_by_window(
    candidates: list[BrunchCandidate],
    window_start: datetime,
    window_end: datetime,
) -> list[BrunchCandidate]:
    return [
        c
        for c in candidates
        if c.published_at is not None and window_start <= c.published_at < window_end
    ]


def fetch_candidates(
    base_url: str = "https://brunch.co.kr",
    keywords: tuple[str, ...] = DEFAULT_KEYWORDS,
    client: httpx.Client | None = None,
) -> list[BrunchCandidate]:
    """키워드 페이지들을 조회해 후보를 수집한다 (URL 기준 중복 제거)."""
    own_client = client is None
    http = client or httpx.Client(timeout=10, headers=FETCH_HEADERS, follow_redirects=True)
    seen: set[str] = set()
    results: list[BrunchCandidate] = []
    try:
        for keyword in keywords:
            try:
                res = http.get(f"{base_url}/keyword/{keyword}")
                res.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("브런치 키워드 페이지 조회 실패(%s): %s", keyword, exc)
                continue
            for candidate in parse_keyword_page(res.text):
                if candidate.url not in seen:
                    seen.add(candidate.url)
                    results.append(candidate)
    finally:
        if own_client:
            http.close()
    return results
