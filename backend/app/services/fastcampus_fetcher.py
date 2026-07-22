"""패스트캠퍼스 공개 카테고리 API 클래스 수집기.

사용자 지정 목록의 마지막 과정 그리드는 category/best/latest/products 공개 JSON으로
렌더링된다. CSS module 해시나 추천 섹션 수에 의존하지 않고 동일 데이터 원천을 읽는다.
"""
import logging
from dataclasses import dataclass

import httpx

from app.services.course_candidate import CourseCandidate

logger = logging.getLogger(__name__)
BASE_URL = "https://fastcampus.co.kr"
TARGET_BADGES = ("얼리버드", "인기 급상승", "BEST", "NEW")
EXPECTED_CATEGORY_IDS = {"DATASCIENCEDL": 39, "AICREATIVE": 921, "BIZ": 1}
FETCH_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NexusBot/1.0)", "Accept": "application/json"}


@dataclass(frozen=True)
class FastCampusSource:
    page_url: str
    code: str
    label: str


DEFAULT_SOURCES = (
    FastCampusSource(f"{BASE_URL}/category_online_datasciencedl", "DATASCIENCEDL", "AI TECH"),
    FastCampusSource(f"{BASE_URL}/category_online_aicreative", "AICREATIVE", "AI CREATIVE"),
    FastCampusSource(f"{BASE_URL}/category_online_biz", "BIZ", "AI/업무생산성"),
)


FastCampusCandidate = CourseCandidate


@dataclass(frozen=True)
class _SelectedCourse:
    source: FastCampusSource
    rank: int
    course: dict
    badges: tuple[str, ...]


def _minutes(value: str | None) -> int | None:
    if not value:
        return None
    try:
        hours, minutes = value.split(":", 1)
        return int(hours) * 60 + int(minutes)
    except (TypeError, ValueError):
        return None


def _ids(data: dict, category_id: int, label: str) -> set[int]:
    mapping = data.get("data")
    values = mapping.get(str(category_id)) if isinstance(mapping, dict) else None
    if not isinstance(values, list):
        raise ValueError(f"패스트캠퍼스 {label} 응답에 카테고리가 없습니다")
    try:
        return {int(value) for value in values}
    except (TypeError, ValueError) as exc:
        raise ValueError(f"패스트캠퍼스 {label} 과정 ID 형식 오류") from exc


def _pick_product(products: list[dict]) -> dict:
    return next(
        (p for p in products if p.get("state") == "NORMAL" and p.get("isPurchasable") is not False),
        products[0] if products else {},
    )


def _fetch_json(client, url: str, params: dict | None = None) -> dict:
    response = client.get(url, params=params) if params is not None else client.get(url)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or "data" not in data:
        raise ValueError(f"패스트캠퍼스 응답 형식 오류: {url}")
    return data


def _course_badges(course_id: int, course: dict, best_ids: set[int], latest_ids: set[int]) -> tuple[str, ...]:
    badges = []
    if course_id in best_ids:
        badges.append("BEST")
    if course_id in latest_ids:
        badges.append("NEW")
    highlight = (course.get("cardInfo") or {}).get("highlightBadgeTitle")
    if highlight in TARGET_BADGES and highlight not in badges:
        badges.append(highlight)
    return tuple(badges)


def _category_courses(source: FastCampusSource, payload: dict) -> tuple[int, list[dict]]:
    category_data = payload.get("data")
    if not isinstance(category_data, dict):
        raise ValueError(f"패스트캠퍼스 {source.code} 카테고리 응답 형식 오류")
    try:
        category_id = int(category_data["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"패스트캠퍼스 {source.code} 카테고리 ID 형식 오류") from exc
    if category_id != EXPECTED_CATEGORY_IDS.get(source.code):
        raise ValueError(f"패스트캠퍼스 {source.code} 카테고리 ID 불일치")
    courses = category_data.get("courses")
    if not isinstance(courses, list) or not courses:
        raise ValueError(f"패스트캠퍼스 {source.code} 과정 목록이 비어 있습니다")
    return category_id, courses


def _course_id(source: FastCampusSource, course: dict) -> int:
    if not isinstance(course, dict):
        raise ValueError(f"패스트캠퍼스 {source.code} 과정 응답 형식 오류")
    try:
        value = int(course.get("id") or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"패스트캠퍼스 {source.code} 과정 ID 형식 오류") from exc
    if not value or not course.get("slug") or not course.get("publicTitle"):
        raise ValueError(f"패스트캠퍼스 {source.code} 과정 필수 필드 누락")
    return value


def _select_source_courses(
    source: FastCampusSource,
    courses: list[dict],
    best_ids: set[int],
    latest_ids: set[int],
    seen: set[int],
) -> list[_SelectedCourse]:
    selected = []
    for rank, course in enumerate(courses, start=1):
        course_id = _course_id(source, course)
        if course_id in seen:
            continue
        badges = _course_badges(course_id, course, best_ids, latest_ids)
        if badges:
            seen.add(course_id)
            selected.append(_SelectedCourse(source, rank, course, badges))
    if not selected:
        raise ValueError(f"패스트캠퍼스 {source.code} 대상 배지 과정이 없습니다")
    return selected


def _select_courses(http, sources, best_data: dict, latest_data: dict) -> list[_SelectedCourse]:
    selected = []
    seen: set[int] = set()
    for source in sources:
        payload = _fetch_json(http, f"{BASE_URL}/.api/categories/{source.code}")
        category_id, courses = _category_courses(source, payload)
        best_ids = _ids(best_data, category_id, "BEST")
        latest_ids = _ids(latest_data, category_id, "NEW")
        selected.extend(_select_source_courses(source, courses, best_ids, latest_ids, seen))
    return selected


def _fetch_products(http, selected: list[_SelectedCourse]) -> dict[str, list[dict]]:
    product_map = {}
    ids = [str(item.course["id"]) for item in selected]
    for start in range(0, len(ids), 100):
        chunk = ids[start:start + 100]
        payload = _fetch_json(
            http, f"{BASE_URL}/.api/courses/products", params={"id": ",".join(chunk)}
        )
        mapping = payload["data"]
        if not isinstance(mapping, dict) or any(not isinstance(value, list) for value in mapping.values()):
            raise ValueError("패스트캠퍼스 상품 응답 형식 오류")
        product_map.update(mapping)
    return product_map


def _to_candidate(item: _SelectedCourse, product_map: dict[str, list[dict]]) -> FastCampusCandidate:
    course = item.course
    course_id = str(course["id"])
    product = _pick_product(product_map.get(course_id, []))
    return FastCampusCandidate(
        source_id=course_id,
        source_category_code=item.source.code,
        source_category_name=item.source.label,
        source_category_url=item.source.page_url,
        source_rank=item.rank,
        title=(course.get("publicTitle") or "").strip(),
        summary=(course.get("publicDescription") or "").strip() or None,
        source_url=f"{BASE_URL}/{course['slug']}",
        thumbnail_url=course.get("desktopCardAsset"),
        sub_category_name=(course.get("subCategory") or {}).get("title"),
        format_name=(course.get("format") or {}).get("title"),
        qualification=course.get("qualification"),
        running_time_minutes=_minutes(course.get("runningTime")),
        sale_price=product.get("salePrice"),
        list_price=product.get("listPrice"),
        badges=item.badges,
    )


def fetch_fastcampus_candidates(
    *,
    sources: list[FastCampusSource] | tuple[FastCampusSource, ...] = DEFAULT_SOURCES,
    client: httpx.Client | None = None,
) -> list[FastCampusCandidate]:
    """세 대상 카테고리에서 지정 배지가 있는 과정만 반환한다.

    어느 카테고리/API든 실패하면 예외를 전파해 기존 공개 과정을 잘못 숨기지 않는다.
    """
    own_client = client is None
    http = client or httpx.Client(timeout=30, headers=FETCH_HEADERS, follow_redirects=True)
    try:
        best_data = _fetch_json(http, f"{BASE_URL}/.api/courses/recommended/best")
        latest_data = _fetch_json(http, f"{BASE_URL}/.api/courses/marketing/latest")
        selected = _select_courses(http, sources, best_data, latest_data)
        product_map = _fetch_products(http, selected)
        result = [_to_candidate(item, product_map) for item in selected]
        logger.info("패스트캠퍼스 대상 클래스 %d건 수집", len(result))
        return result
    except (KeyError, TypeError, AttributeError) as exc:
        # 외부 JSON 스키마 오류는 내부 API가 일관되게 502로 변환할 수 있도록 정규화한다.
        raise ValueError("패스트캠퍼스 응답 스키마 오류") from exc
    finally:
        if own_client:
            http.close()
