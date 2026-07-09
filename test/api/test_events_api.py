"""밋업 이벤트 API 테스트 (meet.pl 목록)."""
from datetime import datetime, timedelta, timezone

from app.models import MeetupEvent


def seed_events(client, count=3):
    db = client.session_factory()
    now = datetime.now(timezone.utc)
    for i in range(count):
        db.add(
            MeetupEvent(
                source_id=str(100 + i),
                title=f"AI 밋업 {i}",
                host_name="호스트",
                source_url=f"https://event-us.kr/ch/event/{100 + i}",
                event_start=now + timedelta(days=i + 1),
                place="코엑스",
                area="서울/경기/인천",
                price_min=0 if i == 0 else 15000,
                is_free=(i == 0),
                view_count=10 * i,
                event_system_type="offline" if i else "online",
                category="IT/프로그래밍",
            )
        )
    db.commit()
    db.close()


def test_events_list_card_fields(client):
    seed_events(client)
    res = client.get("/api/events")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["meta"]["total"] == 3
    card = body["data"][0]  # 가까운 일정 순
    assert card["title"] == "AI 밋업 0"
    assert card["hostName"] == "호스트"
    # 상세 클릭 = 원본 사이트 이동 + ref 부착 (브런치와 동일 규칙)
    assert card["linkUrl"] == "https://event-us.kr/ch/event/100?ref=nexus.bccard.ai"
    assert card["isExternal"] is True
    assert card["priceText"] == "무료"
    assert body["data"][1]["priceText"] == "15,000원~"


def test_events_list_sorted_by_start_asc(client):
    seed_events(client)
    res = client.get("/api/events").json()
    starts = [c["eventStart"] for c in res["data"]]
    assert starts == sorted(starts)


def test_events_excludes_past(client):
    seed_events(client)
    db = client.session_factory()
    db.add(
        MeetupEvent(
            source_id="old", title="지난 밋업", source_url="https://event-us.kr/ch/event/old",
            event_start=datetime.now(timezone.utc) - timedelta(days=2),
            is_free=True, price_min=0, category="IT/프로그래밍",
        )
    )
    db.commit()
    db.close()
    client.cache.bump_version()
    res = client.get("/api/events").json()
    assert all(c["title"] != "지난 밋업" for c in res["data"])


def test_events_cache_invalidated_on_collect(client):
    seed_events(client, count=1)
    first = client.get("/api/events").json()
    assert first["meta"]["total"] == 1

    from app.services.meetup_collector import collect_meetups
    from app.services.meetup_fetcher import MeetupCandidate

    db = client.session_factory()

    new = MeetupCandidate(
        source_id="900", title="신규 밋업", host_name="h",
        source_url="https://event-us.kr/ch/event/900",
        event_start=datetime.now(timezone.utc) + timedelta(days=5),
        event_end=None, place=None, area=None, address=None,
        price_min=0, is_free=True, view_count=0,
        event_system_type="offline", category="경제/금융", cover_image_url=None,
    )
    collect_meetups(db, client.cache, candidates=[new])
    db.close()

    after = client.get("/api/events").json()
    assert after["meta"]["total"] == 2
