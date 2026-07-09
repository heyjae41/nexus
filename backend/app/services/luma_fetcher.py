"""luma.com 밋업 수집 — 카테고리(AI/TECH)별 '근처(서울) 이벤트' 를 가져온다.

공개 API: GET https://api.lu.ma/discover/get-paginated-events
  ?discover_category_api_id=cat-ai&discover_place_api_id=discplace-...&pagination_limit=N
- 서울 place ID 를 명시해 서버 IP 위치와 무관하게 '근처 이벤트' 를 결정적으로 조회한다.
- 응답은 시작시간 오름차순 → 윈도우(오늘~+N일)를 벗어나면 페이지네이션을 중단한다.
- luma 는 가격 정보를 내려주지 않으므로 무료로 단정하지 않고 미상(None) 처리한다.
"""
import logging
from datetime import datetime, time, timedelta

import httpx

from app.services.meetup_fetcher import KST, FETCH_HEADERS, MeetupCandidate

logger = logging.getLogger(__name__)

LUMA_API_URL = "https://api.lu.ma/discover/get-paginated-events"
LUMA_EVENT_BASE = "https://lu.ma"
SEOUL_PLACE_API_ID = "discplace-eQieweHXBFCWbCj"
PAGE_LIMIT = 25
MAX_PAGES = 20


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_luma_entries(entries: list[dict], category_label: str) -> list[MeetupCandidate]:
    candidates = []
    for item in entries:
        event = item.get("event") or {}
        api_id, name, slug = event.get("api_id"), event.get("name"), event.get("url")
        if not (api_id and name and slug):
            continue
        geo = event.get("geo_address_info") or {}
        candidates.append(
            MeetupCandidate(
                source_id=f"luma-{api_id}",
                title=name.strip(),
                host_name=None,  # 목록 API 에 호스트 정보 없음
                source_url=f"{LUMA_EVENT_BASE}/{slug}",
                event_start=_parse_dt(event.get("start_at")),
                event_end=_parse_dt(event.get("end_at")),
                place=geo.get("sublocality"),
                area=geo.get("city_state"),
                address=None,
                price_min=None,  # 가격 미상 (무료 단정 금지)
                is_free=None,
                view_count=0,
                event_system_type=event.get("location_type"),
                category=category_label,
                cover_image_url=event.get("cover_url"),
            )
        )
    return candidates


def _filter_window(
    candidates: list[MeetupCandidate],
    now: datetime,
    window_end: datetime,
    seen: set[str],
) -> tuple[list[MeetupCandidate], bool]:
    """윈도우 내 신규 후보만 남긴다. (kept, 윈도우 초과 항목 존재 여부)"""
    kept, beyond_window = [], False
    for candidate in candidates:
        if candidate.event_start is None or candidate.event_start < now:
            continue  # 일정 미상/이미 시작된 이벤트 제외
        if candidate.event_start > window_end:
            beyond_window = True
            continue
        if candidate.source_url not in seen:
            seen.add(candidate.source_url)
            kept.append(candidate)
    return kept, beyond_window


def _fetch_page(http: httpx.Client, params: dict) -> dict | None:
    try:
        res = http.get(LUMA_API_URL, params=params)
        res.raise_for_status()
        return res.json()
    except httpx.HTTPError:
        return None


def fetch_luma_candidates(
    category_api_id: str,
    category_label: str,
    window_days: int,
    place_api_id: str = SEOUL_PLACE_API_ID,
    client: httpx.Client | None = None,
) -> list[MeetupCandidate]:
    """윈도우(오늘~+window_days일) 내 이벤트를 커서 페이지네이션으로 수집한다."""
    now = datetime.now(KST)
    window_end = datetime.combine(
        now.date() + timedelta(days=window_days), time(23, 59, 59), tzinfo=KST
    )
    own_client = client is None
    http = client or httpx.Client(timeout=15, headers=FETCH_HEADERS)
    results: list[MeetupCandidate] = []
    seen: set[str] = set()
    cursor = None
    try:
        for _ in range(MAX_PAGES):
            params = {
                "discover_category_api_id": category_api_id,
                "discover_place_api_id": place_api_id,
                "pagination_limit": PAGE_LIMIT,
            }
            if cursor:
                params["pagination_cursor"] = cursor
            data = _fetch_page(http, params)
            if data is None:
                # 중간 페이지 실패 시 이미 수집한 결과는 유실하지 않는다
                logger.warning(
                    "luma(%s) 조회 실패 — 수집된 %d건만 반환", category_api_id, len(results)
                )
                break
            candidates = parse_luma_entries(data.get("entries", []), category_label)
            kept, beyond_window = _filter_window(candidates, now, window_end, seen)
            results.extend(kept)
            cursor = data.get("next_cursor")
            if beyond_window or not data.get("has_more") or not cursor:
                break
    finally:
        if own_client:
            http.close()
    logger.info("luma(%s) 후보 %d건 수집", category_api_id, len(results))
    return results
