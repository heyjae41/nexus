"""DAKER 공개 API에서 모집중·진행중 해커톤을 수집한다."""
from datetime import datetime, timezone
import logging

import httpx

from app.services.class_opportunities import ClassOpportunityCandidate

BASE_URL = "https://daker.ai"
LIST_URL = f"{BASE_URL}/api/hackathons/public-list"
CATEGORY_URL = f"{BASE_URL}/public/hackathons"
FETCH_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NexusBot/1.0)"}
logger = logging.getLogger(__name__)


def _datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("DAKER 날짜에 시간대 정보가 없습니다")
    return parsed


def _integer(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _text(item: dict, key: str) -> str | None:
    value = str(item.get(key) or "").strip()
    return value or None


def _required_text(item: dict, key: str) -> str:
    value = _text(item, key)
    if value is None:
        raise ValueError("DAKER 해커톤 필수 필드 누락")
    return value


def _absolute_image(value: str | None) -> str | None:
    if value and value.startswith("/"):
        return f"{BASE_URL}{value}"
    return value


def _active(item: dict, now: datetime) -> bool:
    end = _datetime(item.get("lastStageEndDate") or item.get("endDate"))
    return (
        item.get("status") == "published"
        and item.get("isPracticeMode") is not True
        and end is not None
        and end >= now
    )


def _status_label(item: dict, now: datetime) -> str:
    deadline = _datetime(item.get("registrationDeadline"))
    return "모집중" if deadline is not None and deadline >= now else "진행중"


def _candidate(item: dict, rank: int, now: datetime) -> ClassOpportunityCandidate:
    source_id = _required_text(item, "id")
    title = _required_text(item, "title")
    slug = _required_text(item, "slug")
    label = _status_label(item, now)
    return ClassOpportunityCandidate(
        source_type="daker",
        source_id=f"daker:{source_id}",
        source_category_code="DAKER",
        source_category_name="해커톤",
        source_category_url=CATEGORY_URL,
        source_rank=rank,
        title=title,
        summary=_text(item, "tagline"),
        source_url=f"{CATEGORY_URL}/{slug}",
        thumbnail_url=_absolute_image(item.get("headerImageUrl")),
        sub_category_name=_text(item, "organizerName"),
        format_name=label,
        qualification=None,
        running_time_minutes=None,
        sale_price=_integer(item.get("totalPrize")),
        list_price=None,
        badges=(label,),
    )


def _validate_payload(payload) -> list[dict]:
    if not isinstance(payload, list):
        raise ValueError("DAKER 해커톤 응답 형식 오류")
    if not payload:
        raise ValueError("DAKER 해커톤 원본 빈 응답")
    for item in payload:
        if not isinstance(item, dict) or "status" not in item:
            raise ValueError("DAKER 해커톤 상태 필드 누락")
        if item["status"] == "published" and _datetime(
            item.get("lastStageEndDate") or item.get("endDate")
        ) is None:
            raise ValueError("DAKER 공개 해커톤 종료일 필드 누락")
    return payload


def _active_candidates(payload: list[dict], now: datetime):
    return [
        _candidate(item, rank, now)
        for rank, item in enumerate(payload, start=1)
        if _active(item, now)
    ]


def fetch_daker_candidates(
    *, client: httpx.Client | None = None, now: datetime | None = None
) -> list[ClassOpportunityCandidate]:
    own_client = client is None
    http = client or httpx.Client(timeout=30, headers=FETCH_HEADERS, follow_redirects=True)
    current = now or datetime.now(timezone.utc)
    try:
        response = http.get(LIST_URL)
        response.raise_for_status()
        payload = _validate_payload(response.json())
        result = _active_candidates(payload, current)
        logger.info("DAKER 모집중·진행중 해커톤 %d건 수집", len(result))
        return result
    finally:
        if own_client:
            http.close()
