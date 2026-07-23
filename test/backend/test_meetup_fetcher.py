"""event-us.kr 밋업 검색 API 파서/요청 빌더 테스트 (실제 응답 픽스처 사용)."""
import json
from datetime import date, datetime
from pathlib import Path

from app.services.meetup_fetcher import (
    MeetupCandidate,
    build_search_body,
    parse_search_response,
)

FIXTURE = Path(__file__).parent.parent / "fixtures" / "eventus_search_page1.json"


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_build_search_body_conditions():
    body = build_search_body(
        query="ai ax",
        categories=["IT/프로그래밍", "경제/금융"],
        window_start=date(2026, 7, 9),
        window_days=20,
        page=3,
    )
    assert body["query"] == "ai ax"
    assert body["page"] == {"current": 3, "size": 12}
    filters = body["filters"]["all"]
    assert {"category": ["IT/프로그래밍", "경제/금융"]} in filters
    # 기간: 오늘 ~ 오늘+20일
    start_date = next(f["start_date"] for f in filters if "start_date" in f)
    assert start_date["from"].startswith("2026-07-09T00:00:00")
    assert start_date["to"].startswith("2026-07-29T23:59:59")
    # 기본 상태 필터 (공개/진행 행사만)
    assert {"state": "Start"} in filters
    assert {"disclosure_status": "open"} in filters


def test_parse_search_response_maps_fields():
    total_pages, candidates = parse_search_response(load_fixture())
    assert total_pages == 11
    assert len(candidates) == 3
    c = candidates[0]
    assert isinstance(c, MeetupCandidate)
    assert c.source_id == "129202"
    assert c.title == "월간 AX: 7월"
    assert c.host_name == "한빛앤"
    assert c.source_url == "https://event-us.kr/FKH3nHkjmPGh/event/129202"
    assert c.place == "한빛미디어 리더스홀 (B동 1층)"
    assert c.area == "서울/경기/인천"
    assert c.is_free is True
    assert c.price_min == 0
    assert c.view_count == 536
    assert c.event_system_type == "offline"
    assert c.category == "IT/프로그래밍"
    assert isinstance(c.event_start, datetime)
    assert c.event_start.tzinfo is not None
    assert c.cover_image_url == (
        "https://event-us.kr/Image/FKH3nHkjmPGh/129202/ProjectInfo/Cover/"
        "0cfbb008f1cf4fe495644265fc63dc56.jpg"
    )


def test_parse_search_response_paid_event():
    _, candidates = parse_search_response(load_fixture())
    paid = candidates[1]
    assert paid.is_free is False
    assert paid.price_min == 1000000


def test_parse_search_response_skips_broken_items():
    data = load_fixture()
    data["results"].append({"title": {"raw": "id 없음"}})
    _, candidates = parse_search_response(data)
    assert len(candidates) == 3  # 필수 필드 없는 항목은 건너뜀


from shared import FakeResponse  # noqa: E402 — fetcher 테스트 공용 스텁


class FakeClient:
    """페이지 번호별 응답을 흉내내는 검색 API 스텁."""

    def __init__(self, pages):
        self.pages = pages  # {page_number: FakeResponse}

    def post(self, url, json):
        return self.pages[json["page"]["current"]]


def page_payload(total_pages, ids):
    return {
        "meta": {"page": {"total_pages": total_pages}},
        "results": [
            {
                "id": {"raw": i},
                "title": {"raw": f"밋업 {i}"},
                "subdomain": {"raw": "ch"},
                "min_money": {"raw": 0},
                "payway": {"raw": "false"},
                "view_count": {"raw": 1},
            }
            for i in ids
        ],
    }


def test_fetch_all_pages_and_dedup():
    from app.services.meetup_fetcher import fetch_meetup_candidates

    client = FakeClient({
        1: FakeResponse(page_payload(2, ["1", "2"])),
        2: FakeResponse(page_payload(2, ["2", "3"])),  # 2는 페이지 간 중복
    })
    result = fetch_meetup_candidates("ai ax", ["IT/프로그래밍"], 20, client=client)
    assert [c.source_id for c in result] == ["1", "2", "3"]


def test_fetch_returns_partial_results_on_mid_page_error():
    """페이지네이션 중간 실패 시 이미 수집한 결과는 유실하지 않는다."""
    from app.services.meetup_fetcher import fetch_meetup_candidates

    client = FakeClient({
        1: FakeResponse(page_payload(3, ["1", "2"])),
        2: FakeResponse(None, fail=True),
    })
    result = fetch_meetup_candidates("ai ax", ["IT/프로그래밍"], 20, client=client)
    assert [c.source_id for c in result] == ["1", "2"]


def test_fetch_handles_empty_first_page():
    from app.services.meetup_fetcher import fetch_meetup_candidates

    client = FakeClient({1: FakeResponse(page_payload(0, []))})
    assert fetch_meetup_candidates("ai ax", ["IT/프로그래밍"], 20, client=client) == []


def test_paid_detection_defensive():
    """payway 가 없어도 유료 금액이 있으면 무료로 분류하지 않는다."""
    payload = page_payload(1, ["1"])
    payload["results"][0]["min_money"] = {"raw": 50000.0}
    payload["results"][0].pop("payway")
    _, candidates = parse_search_response(payload)
    assert candidates[0].is_free is False
    assert candidates[0].price_min == 50000


def test_parse_search_response_empty():
    total_pages, candidates = parse_search_response({"meta": {"page": {"total_pages": 0}}, "results": []})
    assert total_pages == 0
    assert candidates == []
