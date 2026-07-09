"""밋업 수집기 테스트: 전 페이지 수집 결과를 meet.pl 에 반영한다.

- source_url 기준 중복 제거 (재수집 시 신규만 추가)
- 신규 추가가 있으면 캐시 무효화
- 수집 이력(meetup_collect_runs) 기록
"""
from datetime import datetime, timedelta, timezone

from app.cache import InMemoryCacheBackend, VersionedCache
from app.models import MeetupCollectRun, MeetupEvent
from app.services.meetup_collector import collect_meetups
from app.services.meetup_fetcher import MeetupCandidate


def make_cache():
    return VersionedCache(InMemoryCacheBackend(), prefix="nexus:", ttl_seconds=300)


def cand(source_id="1", **over) -> MeetupCandidate:
    fields = dict(
        source_id=source_id,
        title=f"AI 밋업 {source_id}",
        host_name="호스트",
        source_url=f"https://event-us.kr/ch/event/{source_id}",
        event_start=datetime.now(timezone.utc) + timedelta(days=3),
        event_end=None,
        place="코엑스",
        area="서울/경기/인천",
        address="서울 강남구",
        price_min=0,
        is_free=True,
        view_count=100,
        event_system_type="offline",
        category="IT/프로그래밍",
        cover_image_url=None,
    )
    fields.update(over)
    return MeetupCandidate(**fields)


def test_collect_saves_all_new_events(db):
    cache = make_cache()
    result = collect_meetups(db, cache, candidates=[cand("1"), cand("2"), cand("3")])
    assert result.added == 3
    assert db.query(MeetupEvent).count() == 3
    run = db.query(MeetupCollectRun).one()
    assert run.status == "success"
    assert run.candidates_count == 3
    assert run.added_count == 3


def test_collect_dedups_by_source_url(db):
    cache = make_cache()
    collect_meetups(db, cache, candidates=[cand("1"), cand("2")])
    result = collect_meetups(db, cache, candidates=[cand("2"), cand("3")])
    assert result.added == 1
    assert db.query(MeetupEvent).count() == 3


def test_collect_bumps_cache_only_when_new(db):
    cache = make_cache()
    collect_meetups(db, cache, candidates=[cand("1")])
    cache.set("home", "warm")
    collect_meetups(db, cache, candidates=[cand("1")])  # 전부 중복
    assert cache.get("home") == "warm"
    collect_meetups(db, cache, candidates=[cand("2")])
    assert cache.get("home") is None


def test_collect_empty_records_empty_run(db):
    cache = make_cache()
    result = collect_meetups(db, cache, candidates=[])
    assert result.added == 0
    assert db.query(MeetupCollectRun).one().status == "empty"


def test_collect_dedups_by_source_id_even_if_url_differs(db):
    """subdomain 변경 등으로 URL 이 달라져도 source_id 가 같으면 중복이다."""
    cache = make_cache()
    collect_meetups(db, cache, candidates=[cand("1")])
    result = collect_meetups(
        db, cache,
        candidates=[cand("1", source_url="https://event-us.kr/newch/event/1")],
    )
    assert result.added == 0
    assert db.query(MeetupEvent).count() == 1


def test_collect_records_failed_run_on_db_error(db):
    """저장 중 예외 발생 시 failed 이력을 남기고 예외를 전파한다."""
    import pytest

    cache = make_cache()
    broken = cand("1", title=None)  # NOT NULL 위반 유도
    with pytest.raises(Exception):
        collect_meetups(db, cache, candidates=[broken])
    run = db.query(MeetupCollectRun).one()
    assert run.status == "failed"
    assert run.error_message
