"""DACON 공개 API에서 참가신청중 경진대회를 수집한다."""
from datetime import datetime, timedelta, timezone
import logging

import httpx

from app.services.class_opportunities import ClassOpportunityCandidate

API_URL = "https://app.dacon.io/api/v1/competition/list"
BASE_URL = "https://dacon.io"
CATEGORY_URL = f"{BASE_URL}/competitions"
IMAGE_BASE_URL = "https://dacon.s3.ap-northeast-2.amazonaws.com"
PAGE_SIZE = 15
FETCH_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NexusBot/1.0)"}
logger = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))


def _integer(value, *, multiplier: int = 1) -> int | None:
    try:
        return int(value) * multiplier if value is not None else None
    except (TypeError, ValueError):
        return None


def _text(item: dict, key: str) -> str | None:
    value = str(item.get(key) or "").strip()
    return value or None


def _period_start(value) -> datetime:
    if not isinstance(value, str):
        raise ValueError("DACON 경진대회 시작일 값 형식 오류")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("DACON 경진대회 시작일 값 형식 오류") from exc
    return parsed.replace(tzinfo=KST) if parsed.tzinfo is None else parsed


def _registration_open(item: dict, now: datetime) -> bool:
    dday = _integer(item.get("period_dday"))
    return (
        item.get("practice") == 1
        and dday is not None
        and (now < _period_start(item.get("period_start")) or dday >= 0)
    )


def _competition_identity(item: dict) -> tuple[int, str]:
    try:
        competition_id = int(item["cpt_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("DACON 경진대회 필수 필드 누락") from exc
    title = _text(item, "name")
    if competition_id <= 0 or title is None:
        raise ValueError("DACON 경진대회 필수 필드 누락")
    return competition_id, title


def _logo_url(item: dict, competition_id: int) -> str | None:
    if not item.get("logo_cpt"):
        return None
    return f"{IMAGE_BASE_URL}/competition/{competition_id}/logo_cpt.jpeg"


def _candidate(item: dict, rank: int) -> ClassOpportunityCandidate:
    competition_id, title = _competition_identity(item)
    return ClassOpportunityCandidate(
        source_type="dacon",
        source_id=f"dacon:{competition_id}",
        source_category_code="DACON",
        source_category_name="경진대회",
        source_category_url=CATEGORY_URL,
        source_rank=rank,
        title=title,
        summary=_text(item, "keyword"),
        source_url=f"{CATEGORY_URL}/official/{competition_id}/overview/",
        thumbnail_url=_logo_url(item, competition_id),
        sub_category_name="DACON",
        format_name="참가신청중",
        qualification=None,
        running_time_minutes=None,
        sale_price=_integer(item.get("prize"), multiplier=10_000),
        list_price=None,
        badges=("참가신청중",),
    )


def _validate_items(payload) -> list[dict]:
    items = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise ValueError("DACON 경진대회 응답 형식 오류")
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("DACON 경진대회 항목 형식 오류")
        if not {"practice", "period_dday", "period_start"}.issubset(item):
            raise ValueError("DACON 경진대회 상태 필드 누락")
        if item["practice"] not in (0, 1) or _integer(item["period_dday"]) is None:
            raise ValueError("DACON 경진대회 상태 값 형식 오류")
        _period_start(item["period_start"])
    return items


def _fetch_page(http: httpx.Client, page: int) -> list[dict]:
    response = http.get(API_URL, params={"offset": page, "range": ""})
    response.raise_for_status()
    return _validate_items(response.json())


def _page_candidates(items: list[dict], page: int, now: datetime):
    return [
        _candidate(item, page * PAGE_SIZE + index)
        for index, item in enumerate(items, start=1)
        if _registration_open(item, now)
    ]


def _fetch_all(http: httpx.Client, max_pages: int, now: datetime):
    result = []
    for page in range(max_pages):
        items = _fetch_page(http, page)
        if page == 0 and not items:
            raise ValueError("DACON 경진대회 첫 페이지 빈 응답")
        result.extend(_page_candidates(items, page, now))
        if len(items) < PAGE_SIZE:
            return result
    raise ValueError("DACON 경진대회 페이지 수가 안전 한도를 초과했습니다")


def fetch_dacon_candidates(
    *,
    client: httpx.Client | None = None,
    max_pages: int = 50,
    now: datetime | None = None,
) -> list[ClassOpportunityCandidate]:
    own_client = client is None
    http = client or httpx.Client(timeout=30, headers=FETCH_HEADERS, follow_redirects=True)
    try:
        result = _fetch_all(http, max_pages, now or datetime.now(timezone.utc))
        logger.info("DACON 참가신청중 경진대회 %d건 수집", len(result))
        return result
    finally:
        if own_client:
            http.close()
