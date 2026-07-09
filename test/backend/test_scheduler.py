"""스케줄러 구성 테스트: 인제스트 1분 / 수집 체인(브런치→밋업 순차) 12시간."""
from app.cache import InMemoryCacheBackend, VersionedCache
from app.services import scheduler as scheduler_module
from app.services.scheduler import build_scheduler, run_collect_chain_job


def make_cache():
    return VersionedCache(InMemoryCacheBackend(), prefix="nexus:", ttl_seconds=300)


def test_scheduler_has_ingest_and_collect_chain():
    scheduler = build_scheduler(make_cache())
    jobs = {j.id: j for j in scheduler.get_jobs()}
    assert set(jobs) == {"ingest_contents", "collect_chain"}
    assert jobs["ingest_contents"].trigger.interval.total_seconds() == 60
    assert jobs["collect_chain"].trigger.interval.total_seconds() == 12 * 3600


def test_collect_chain_runs_brunch_first_then_meetups(monkeypatch):
    """수행 순서: 브런치 → event-us → luma(AI) → luma(TECH). 하나가 실패해도 다음은 진행."""
    calls = []
    monkeypatch.setattr(
        scheduler_module, "run_brunch_job",
        lambda cache: calls.append("brunch"),
    )

    def fake_meetup(cache):
        calls.append("eventus")
        raise RuntimeError("eventus 실패해도 체인은 계속")

    monkeypatch.setattr(scheduler_module, "run_meetup_job", fake_meetup)
    monkeypatch.setattr(
        scheduler_module, "run_luma_job",
        lambda cache, category_api_id, label: calls.append(f"luma:{label}"),
    )

    run_collect_chain_job(make_cache())
    assert calls == ["brunch", "eventus", "luma:AI", "luma:TECH"]
