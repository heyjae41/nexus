"""luma.com 밋업 수집 파서/페이지네이션 테스트 (실제 API 응답 픽스처 사용)."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.luma_fetcher import fetch_luma_candidates, parse_luma_entries

FIXTURE = Path(__file__).parent.parent / "fixtures" / "luma_events_page1.json"
KST = timezone(timedelta(hours=9))


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parse_luma_entries_maps_fields():
    candidates = parse_luma_entries(load_fixture()["entries"], category_label="AI")
    assert len(candidates) == 3
    c = candidates[0]
    assert c.source_id == "luma-evt-DxWdwvbMtWw9CHI"
    assert c.title.startswith("NUS x Jane Street Summit")
    assert c.source_url == "https://lu.ma/rzkweojj"
    assert c.event_start == datetime.fromisoformat("2026-07-09T05:30:00.000+00:00")
    assert c.area == "Seoul, South Korea"
    assert c.event_system_type == "offline"
    assert c.category == "AI"
    # luma 는 가격 정보를 제공하지 않는다 → 미상(None) 처리, 무료로 단정하지 않음
    assert c.is_free is None
    assert c.price_min is None
    assert c.cover_image_url.startswith("https://images.lumacdn.com/")


def test_parse_luma_entries_skips_items_without_url():
    entries = load_fixture()["entries"]
    entries.append({"event": {"api_id": "evt-x", "name": "url 없음"}})
    assert len(parse_luma_entries(entries, category_label="AI")) == 3


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, responses):
        self.responses = responses  # cursor(None 포함) → payload
        self.calls = []

    def get(self, url, params=None):
        cursor = (params or {}).get("pagination_cursor")
        self.calls.append(cursor)
        return FakeResponse(self.responses[cursor])


def entry(api_id, start_at, url="slug"):
    return {
        "event": {
            "api_id": api_id, "name": f"이벤트 {api_id}", "url": f"{url}-{api_id}",
            "start_at": start_at, "location_type": "offline",
            "geo_address_info": {"city_state": "Seoul, South Korea"},
        }
    }


def in_days(days):
    return (datetime.now(KST) + timedelta(days=days)).isoformat()


def test_fetch_paginates_until_window_end():
    """시작시간 오름차순 응답에서 윈도우(+14일)를 벗어나면 페이지네이션을 중단한다."""
    client = FakeClient({
        None: {"entries": [entry("1", in_days(1)), entry("2", in_days(5))],
               "has_more": True, "next_cursor": "c2"},
        "c2": {"entries": [entry("3", in_days(13)), entry("4", in_days(30))],
               "has_more": True, "next_cursor": "c3"},
        # c3 은 호출되지 않아야 한다 (4번이 윈도우 밖)
    })
    result = fetch_luma_candidates("cat-ai", "AI", window_days=14, client=client)
    assert [c.source_id for c in result] == ["luma-1", "luma-2", "luma-3"]
    assert client.calls == [None, "c2"]


def test_fetch_stops_when_no_more():
    client = FakeClient({
        None: {"entries": [entry("1", in_days(2))], "has_more": False, "next_cursor": None},
    })
    result = fetch_luma_candidates("cat-ai", "AI", window_days=14, client=client)
    assert len(result) == 1


def test_fetch_stops_when_has_more_but_cursor_missing():
    """has_more=True 인데 커서가 없으면 무한 루프 없이 종료한다."""
    client = FakeClient({
        None: {"entries": [entry("1", in_days(2))], "has_more": True, "next_cursor": None},
    })
    result = fetch_luma_candidates("cat-ai", "AI", window_days=14, client=client)
    assert [c.source_id for c in result] == ["luma-1"]
    assert client.calls == [None]


def test_fetch_excludes_past_and_beyond_window():
    client = FakeClient({
        None: {"entries": [entry("old", in_days(-2)), entry("ok", in_days(3)),
                           entry("far", in_days(20))],
               "has_more": False, "next_cursor": None},
    })
    result = fetch_luma_candidates("cat-ai", "AI", window_days=14, client=client)
    assert [c.source_id for c in result] == ["luma-ok"]
