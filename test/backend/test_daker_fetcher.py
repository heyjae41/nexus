"""DAKER 모집중·진행중 해커톤 수집 테스트."""
from datetime import datetime, timezone

import pytest

from app.services.daker_fetcher import fetch_daker_candidates


class Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


class Client:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        return Response(self.data)


def item(source_id, title, *, status="published", deadline, end, practice=False):
    return {
        "id": source_id,
        "title": title,
        "slug": f"slug-{source_id}",
        "tagline": f"{title} 소개",
        "status": status,
        "organizerName": "주최사",
        "totalPrize": "1000000",
        "registrationDeadline": deadline,
        "endDate": end,
        "lastStageEndDate": end,
        "headerImageUrl": f"/public/{source_id}.png",
        "isPracticeMode": practice,
    }


def test_fetch_daker_keeps_only_recruiting_and_in_progress():
    now = datetime(2026, 7, 22, tzinfo=timezone.utc)
    client = Client([
        item("recruiting", "모집 해커톤", deadline="2026-07-30T00:00:00Z", end="2026-08-30T00:00:00Z"),
        item("running", "진행 해커톤", deadline="2026-07-20T00:00:00Z", end="2026-08-20T00:00:00Z"),
        item("closed", "종료 해커톤", status="closed", deadline="2026-07-01T00:00:00Z", end="2026-07-10T00:00:00Z"),
        item("stale", "상태 지연 해커톤", deadline="2026-07-01T00:00:00Z", end="2026-07-10T00:00:00Z"),
        item("practice", "연습 해커톤", deadline="2026-07-30T00:00:00Z", end="2026-08-30T00:00:00Z", practice=True),
    ])

    result = fetch_daker_candidates(client=client, now=now)

    assert [candidate.source_id for candidate in result] == [
        "daker:recruiting",
        "daker:running",
    ]
    assert [candidate.format_name for candidate in result] == ["모집중", "진행중"]
    assert result[0].source_category_code == "DAKER"
    assert result[0].source_url == "https://daker.ai/public/hackathons/slug-recruiting"
    assert result[0].thumbnail_url == "https://daker.ai/public/recruiting.png"
    assert result[0].sale_price == 1_000_000
    assert result[0].badges == ("모집중",)


def test_fetch_daker_rejects_published_item_without_end_date():
    client = Client([{
        "id": "broken", "title": "깨진 해커톤", "slug": "broken",
        "status": "published", "registrationDeadline": "2026-07-30T00:00:00Z",
    }])

    with pytest.raises(ValueError, match="종료일"):
        fetch_daker_candidates(
            client=client, now=datetime(2026, 7, 22, tzinfo=timezone.utc)
        )


def test_fetch_daker_rejects_naive_datetime():
    client = Client([
        item(
            "naive", "타임존 없는 해커톤",
            deadline="2026-07-30T00:00:00", end="2026-08-30T00:00:00",
        )
    ])

    with pytest.raises(ValueError, match="시간대"):
        fetch_daker_candidates(
            client=client, now=datetime(2026, 7, 22, tzinfo=timezone.utc)
        )


def test_fetch_daker_rejects_empty_source_payload():
    with pytest.raises(ValueError, match="빈 응답"):
        fetch_daker_candidates(
            client=Client([]), now=datetime(2026, 7, 22, tzinfo=timezone.utc)
        )
