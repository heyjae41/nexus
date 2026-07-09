"""스케줄러 구성 테스트: 인제스트 1분 / 브런치 12시간 / 밋업 12시간 (설정값)."""
from app.cache import InMemoryCacheBackend, VersionedCache
from app.services.scheduler import build_scheduler


def test_scheduler_has_all_jobs():
    cache = VersionedCache(InMemoryCacheBackend(), prefix="nexus:", ttl_seconds=300)
    scheduler = build_scheduler(cache)
    jobs = {j.id: j for j in scheduler.get_jobs()}
    assert set(jobs) == {"ingest_contents", "brunch_collect", "meetup_collect"}

    assert jobs["ingest_contents"].trigger.interval.total_seconds() == 60
    assert jobs["brunch_collect"].trigger.interval.total_seconds() == 12 * 3600
    assert jobs["meetup_collect"].trigger.interval.total_seconds() == 12 * 3600
