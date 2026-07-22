"""패스트캠퍼스 클래스 upsert·숨김·캐시 무효화 테스트."""
from app.cache import InMemoryCacheBackend, VersionedCache
from app.models import Course, FastCampusCollectRun
from app.services.fastcampus_collector import collect_fastcampus_courses
from app.services.fastcampus_fetcher import FastCampusCandidate


def cache():
    return VersionedCache(InMemoryCacheBackend(), prefix="nexus:", ttl_seconds=300)


def candidate(source_id="1", **over):
    values = dict(
        source_id=source_id,
        source_category_code="DATASCIENCEDL",
        source_category_name="AI TECH",
        source_category_url="https://fastcampus.co.kr/category_online_datasciencedl",
        source_rank=1,
        title=f"강의 {source_id}",
        summary="설명",
        source_url=f"https://fastcampus.co.kr/course-{source_id}",
        thumbnail_url=f"https://cdn.example/{source_id}.webp",
        sub_category_name="RAG & AI Agent",
        format_name="올인원",
        qualification="누구나",
        running_time_minutes=600,
        sale_price=200000,
        list_price=400000,
        badges=("NEW",),
    )
    values.update(over)
    return FastCampusCandidate(**values)


def test_collect_adds_and_records_run(db):
    result = collect_fastcampus_courses(db, cache(), candidates=[candidate("1"), candidate("2")])
    assert (result.candidates, result.added, result.updated, result.hidden) == (2, 2, 0, 0)
    assert db.query(Course).count() == 2
    run = db.query(FastCampusCollectRun).one()
    assert run.status == "success"
    assert run.added_count == 2


def test_collect_upserts_changes_and_hides_courses_that_lost_target_badges(db):
    c = cache()
    collect_fastcampus_courses(db, c, candidates=[candidate("1"), candidate("2")])
    c.set("classes", "warm")

    result = collect_fastcampus_courses(
        db, c,
        candidates=[candidate("1", title="변경된 제목", badges=("BEST", "NEW"))],
    )

    assert (result.added, result.updated, result.hidden) == (0, 1, 1)
    one = db.query(Course).filter_by(source_id="1").one()
    two = db.query(Course).filter_by(source_id="2").one()
    assert one.title == "변경된 제목"
    assert one.badges == "BEST|NEW"
    assert one.status == "published"
    assert two.status == "hidden"
    assert c.get("classes") is None


def test_collect_idempotent_run_does_not_bump_cache(db):
    c = cache()
    candidates = [candidate("1")]
    collect_fastcampus_courses(db, c, candidates=candidates)
    c.set("classes", "warm")
    result = collect_fastcampus_courses(db, c, candidates=candidates)
    assert (result.added, result.updated, result.hidden) == (0, 0, 0)
    assert c.get("classes") == "warm"


def test_collect_rejects_empty_batch_without_hiding_existing(db):
    import pytest
    from app.services.fastcampus_collector import CollectionSafetyError

    c = cache()
    collect_fastcampus_courses(db, c, candidates=[candidate("1")])
    with pytest.raises(CollectionSafetyError):
        collect_fastcampus_courses(db, c, candidates=[])
    assert db.query(Course).filter_by(source_id="1").one().status == "published"


def test_collect_hides_only_completed_categories(db):
    creative = candidate(
        "2", source_category_code="AICREATIVE", source_category_name="AI CREATIVE",
        source_category_url="https://fastcampus.co.kr/category_online_aicreative",
    )
    c = cache()
    collect_fastcampus_courses(db, c, candidates=[candidate("1"), creative])
    result = collect_fastcampus_courses(
        db, c, candidates=[candidate("1")], completed_categories={"DATASCIENCEDL"},
    )
    assert result.hidden == 0
    assert db.query(Course).filter_by(source_id="2").one().status == "published"


def test_collect_rejects_abrupt_category_drop(db):
    import pytest
    from app.services.fastcampus_collector import CollectionSafetyError

    c = cache()
    collect_fastcampus_courses(db, c, candidates=[candidate(str(i)) for i in range(1, 5)])
    with pytest.raises(CollectionSafetyError, match="급감"):
        collect_fastcampus_courses(db, c, candidates=[candidate("1")])
    assert db.query(Course).filter_by(status="published").count() == 4


def test_concurrent_collect_is_serialized(tmp_path):
    import threading
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from app.models import Base

    engine = create_engine(
        f"sqlite+pysqlite:///{tmp_path / 'classes-race.db'}",
        connect_args={"check_same_thread": False}, future=True,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    barrier = threading.Barrier(2)

    @event.listens_for(factory.class_, "before_flush")
    def overlap_flush(*_):
        try:
            barrier.wait(timeout=0.3)
        except threading.BrokenBarrierError:
            pass

    errors = []

    def run():
        try:
            with factory() as session:
                collect_fastcampus_courses(session, cache(), candidates=[candidate("race")])
        except Exception as exc:  # pragma: no cover - 실패 내용을 assertion으로 보고
            errors.append(exc)

    threads = [threading.Thread(target=run), threading.Thread(target=run)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3)
    with factory() as session:
        assert errors == []
        assert session.query(Course).filter_by(source_id="race").count() == 1
    engine.dispose()
