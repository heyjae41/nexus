"""DACON 참가신청중 경진대회 수집 테스트."""
from datetime import datetime, timezone

import pytest

from app.services.dacon_fetcher import fetch_dacon_candidates


class Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


class Client:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url, params):
        page = params["offset"]
        self.calls.append((url, params))
        return Response({"status": 1, "data": self.pages.get(page, [])})


def item(
    source_id, *, practice=1, dday: object = 3,
    start="2026-07-01 10:00:00",
):
    return {
        "cpt_id": source_id,
        "name": f"경진대회 {source_id}",
        "keyword": "알고리즘 | AI",
        "prize": "2000",
        "prize_info": "2,000만 원",
        "practice": practice,
        "period_dday": dday,
        "period_start": start,
        "logo_cpt": 1,
    }


def test_fetch_dacon_keeps_only_registration_open_across_pages():
    first_page = [item(number, practice=0, dday=-1) for number in range(1, 16)]
    client = Client({
        0: first_page,
        1: [item(236727), item(236730, practice=0, dday=2), item(236722, dday=-1)],
    })

    result = fetch_dacon_candidates(client=client)

    assert [candidate.source_id for candidate in result] == ["dacon:236727"]
    assert result[0].source_category_code == "DACON"
    assert result[0].format_name == "참가신청중"
    assert result[0].source_url == "https://dacon.io/competitions/official/236727/overview/"
    assert result[0].thumbnail_url.endswith("/competition/236727/logo_cpt.jpeg")
    assert result[0].sale_price == 20_000_000
    assert result[0].badges == ("참가신청중",)
    assert [params["offset"] for _, params in client.calls] == [0, 1]


def test_fetch_dacon_rejects_missing_status_fields():
    broken = item(236727)
    broken.pop("period_dday")

    with pytest.raises(ValueError, match="상태 필드"):
        fetch_dacon_candidates(client=Client({0: [broken]}))


def test_fetch_dacon_rejects_unparseable_status_value():
    broken = item(236727, dday="open")

    with pytest.raises(ValueError, match="상태 값"):
        fetch_dacon_candidates(client=Client({0: [broken]}))


def test_fetch_dacon_keeps_future_registration_before_start():
    result = fetch_dacon_candidates(
        client=Client({0: [item(236800, dday=-1, start="2026-08-01 10:00:00")]}),
        now=datetime(2026, 7, 22, tzinfo=timezone.utc),
    )

    assert [candidate.source_id for candidate in result] == ["dacon:236800"]
