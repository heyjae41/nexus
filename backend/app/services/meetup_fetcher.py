"""event-us.kr 밋업 검색 API 클라이언트/파서.

수집 조건 (요구사항): 검색어 'ai ax', 카테고리 IT/프로그래밍·경제/금융,
참여방법/가격 전체, 기간 = 오늘 ~ 오늘+20일. 모든 페이지를 수집한다.
"""
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

SEARCH_API_URL = "https://api.event-us.kr/api/v1/engine/search"
EVENT_BASE_URL = "https://event-us.kr"
PAGE_SIZE = 12
MAX_PAGES = 30  # 폭주 방지 상한
KST = timezone(timedelta(hours=9))
FETCH_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NexusBot/1.0)"}

# 사이트 검색과 동일한 가중치 (없으면 400 응답)
SEARCH_BOOSTS = {
    "complate_score": {"type": "functional", "function": "linear", "operation": "add", "factor": 0.3},
    "popular_score": {"type": "functional", "function": "linear", "operation": "add", "factor": 0.2},
}


@dataclass(frozen=True)
class MeetupCandidate:
    source_id: str
    title: str
    host_name: str | None
    source_url: str
    event_start: datetime | None
    event_end: datetime | None
    place: str | None
    area: str | None
    address: str | None
    price_min: int
    is_free: bool
    view_count: int
    event_system_type: str | None
    category: str | None
    cover_image_url: str | None


def build_search_body(
    query: str,
    categories: list[str],
    window_start: date,
    window_days: int,
    page: int = 1,
) -> dict:
    window_end = window_start + timedelta(days=window_days)
    start_from = datetime.combine(window_start, time.min, tzinfo=KST)
    start_to = datetime.combine(window_end, time(23, 59, 59), tzinfo=KST)
    return {
        "query": query,
        "page": {"current": page, "size": PAGE_SIZE},
        "filters": {
            "all": [
                {"state": "Start"},
                {"disclosure_status": "open"},
                {"is_ignore": "false"},
                {"category": categories},
                {"start_date": {"from": start_from.isoformat(), "to": start_to.isoformat()}},
            ]
        },
        "boosts": SEARCH_BOOSTS,
        "sort": [{"_score": "desc"}, {"id": "desc"}],
    }


def _raw(item: dict, key: str):
    value = item.get(key)
    return value.get("raw") if isinstance(value, dict) else value


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _to_candidate(item: dict) -> MeetupCandidate | None:
    source_id = _raw(item, "id")
    title = (_raw(item, "title") or "").strip()
    subdomain = _raw(item, "subdomain")
    if not (source_id and title and subdomain):
        return None
    price_min = int(float(_raw(item, "min_money") or 0))
    # 방어적 무료 판정: payway 필드가 없거나 값이 애매해도 금액이 있으면 유료로 본다
    is_free = str(_raw(item, "payway")).lower() != "true" and price_min == 0
    cover = _raw(item, "cover_image_url")
    return MeetupCandidate(
        source_id=str(source_id),
        title=title,
        host_name=_raw(item, "fullname"),
        source_url=f"{EVENT_BASE_URL}/{subdomain}/event/{source_id}",
        event_start=_parse_dt(_raw(item, "start_date")),
        event_end=_parse_dt(_raw(item, "close_date")),
        place=_raw(item, "place"),
        area=_raw(item, "area"),
        address=_raw(item, "address"),
        price_min=price_min,
        is_free=is_free,
        view_count=int(float(_raw(item, "view_count") or 0)),
        event_system_type=_raw(item, "event_system_type"),
        category=_raw(item, "category"),
        cover_image_url=f"{EVENT_BASE_URL}{cover}" if cover and cover.startswith("/") else cover,
    )


def parse_search_response(data: dict) -> tuple[int, list[MeetupCandidate]]:
    total_pages = int((data.get("meta", {}).get("page", {}) or {}).get("total_pages") or 0)
    candidates = [
        c for c in (_to_candidate(item) for item in data.get("results", [])) if c is not None
    ]
    return total_pages, candidates


def fetch_meetup_candidates(
    query: str,
    categories: list[str],
    window_days: int,
    client: httpx.Client | None = None,
) -> list[MeetupCandidate]:
    """모든 페이지를 순회하며 후보를 수집한다 (source_url 기준 중복 제거)."""
    own_client = client is None
    http = client or httpx.Client(timeout=15, headers=FETCH_HEADERS)
    today = datetime.now(KST).date()
    seen: set[str] = set()
    results: list[MeetupCandidate] = []
    try:
        page = 1
        while page <= MAX_PAGES:
            body = build_search_body(query, categories, today, window_days, page=page)
            try:
                res = http.post(SEARCH_API_URL, json=body)
                res.raise_for_status()
            except httpx.HTTPError:
                # 중간 페이지 실패 시 이미 수집한 결과는 유실하지 않는다
                logger.warning(
                    "밋업 검색 %d페이지 실패 — 수집된 %d건만 반환", page, len(results)
                )
                break
            total_pages, candidates = parse_search_response(res.json())
            for candidate in candidates:
                if candidate.source_url not in seen:
                    seen.add(candidate.source_url)
                    results.append(candidate)
            if page >= total_pages:
                break
            page += 1
    finally:
        if own_client:
            http.close()
    logger.info("밋업 후보 %d건 수집 (%d페이지)", len(results), page)
    return results
