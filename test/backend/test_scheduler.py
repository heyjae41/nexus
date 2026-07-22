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
    """브런치 → event-us → luma(AI/TECH) → fastcampus. 실패해도 다음 단계 진행."""
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
    monkeypatch.setattr(
        scheduler_module, "run_fastcampus_job",
        lambda cache: calls.append("fastcampus"),
    )

    run_collect_chain_job(make_cache())
    assert calls == ["brunch", "eventus", "luma:AI", "luma:TECH", "fastcampus"]


def _cache():
    return VersionedCache(InMemoryCacheBackend(), prefix="nexus:", ttl_seconds=300)


def test_run_ingest_job_scans_contents_dir(db, monkeypatch):
    """인제스트 잡: 설정된 contents 경로를 스캔하고, 실패해도 예외를 전파하지 않는다."""
    from app.services.ingest import IngestResult

    monkeypatch.setattr(scheduler_module, "_session", lambda: db)
    seen = {}

    def fake_scan(db_, cache_, path):
        seen["path"] = path
        return IngestResult(ingested=2, skipped=0, already=0)

    monkeypatch.setattr(scheduler_module, "scan_contents_dir", fake_scan)
    scheduler_module.run_ingest_job(_cache())
    assert seen["path"]  # settings.contents_dir 전달됨

    def boom(*a, **k):
        raise RuntimeError("디스크 오류")

    monkeypatch.setattr(scheduler_module, "scan_contents_dir", boom)
    scheduler_module.run_ingest_job(_cache())  # 예외 전파 없음 (로깅만)


def test_run_brunch_job_passes_12h_window(db, monkeypatch):
    """브런치 잡: 후보를 12시간 창으로 거르고 collect_and_pick 에 넘긴다. 실패는 삼킨다."""
    monkeypatch.setattr(scheduler_module, "_session", lambda: db)
    monkeypatch.setattr(scheduler_module, "fetch_candidates", lambda base_url: ["원본"])
    monkeypatch.setattr(
        scheduler_module, "filter_by_window", lambda cands, s, e: ["창내글"]
    )
    calls = {}

    def fake_pick(db_, cache_, *, candidates, window_start, window_end):
        calls["candidates"] = candidates
        calls["hours"] = (window_end - window_start).total_seconds() / 3600

    monkeypatch.setattr(scheduler_module, "collect_and_pick", fake_pick)
    scheduler_module.run_brunch_job(_cache())
    assert calls["candidates"] == ["창내글"]
    assert calls["hours"] == 12  # settings.brunch_collect_interval_hours 기본값

    def boom(*a, **k):
        raise RuntimeError("네트워크")

    monkeypatch.setattr(scheduler_module, "fetch_candidates", boom)
    scheduler_module.run_brunch_job(_cache())  # 예외 전파 없음


def test_run_meetup_and_luma_jobs_collect(db, monkeypatch):
    """밋업/luma 잡: 각 fetcher 후보를 collect_meetups 로 전달, 실패는 삼킨다."""
    from app.services import luma_fetcher, meetup_collector, meetup_fetcher

    monkeypatch.setattr(scheduler_module, "_session", lambda: db)
    collected = []
    monkeypatch.setattr(
        meetup_collector,
        "collect_meetups",
        lambda db_, cache_, *, candidates: collected.append(candidates),
    )
    monkeypatch.setattr(
        meetup_fetcher,
        "fetch_meetup_candidates",
        lambda **kw: ["이벤터스후보"],
    )
    scheduler_module.run_meetup_job(_cache())

    monkeypatch.setattr(
        luma_fetcher, "fetch_luma_candidates", lambda cid, label, window_days: ["루마후보"]
    )
    scheduler_module.run_luma_job(_cache(), "cat-ai", "AI")
    assert collected == [["이벤터스후보"], ["루마후보"]]

    def boom(**kw):
        raise RuntimeError("네트워크")

    monkeypatch.setattr(meetup_fetcher, "fetch_meetup_candidates", boom)
    scheduler_module.run_meetup_job(_cache())  # 예외 전파 없음


def test_run_fastcampus_job_fetches_and_collects(db, monkeypatch):
    from app.services import fastcampus_collector, fastcampus_fetcher

    monkeypatch.setattr(scheduler_module, "_session", lambda: db)
    monkeypatch.setattr(fastcampus_fetcher, "fetch_fastcampus_candidates", lambda: ["과정"])
    collected = []
    monkeypatch.setattr(
        fastcampus_collector,
        "collect_fastcampus_courses",
        lambda db_, cache_, *, candidates: collected.append(candidates),
    )
    scheduler_module.run_fastcampus_job(_cache())
    assert collected == [["과정"]]

    monkeypatch.setattr(
        fastcampus_fetcher,
        "fetch_fastcampus_candidates",
        lambda: (_ for _ in ()).throw(RuntimeError("네트워크")),
    )
    scheduler_module.run_fastcampus_job(_cache())  # 실패를 삼켜 다음 스케줄을 방해하지 않음
