"""외부 해커톤·경진대회 upsert, 중복 방지, 숨김 테스트."""
from app.services import class_opportunities, fastcampus_collector
from app.cache import InMemoryCacheBackend, VersionedCache
from app.models import Course
from app.services.class_opportunities import (
    ClassOpportunityCandidate,
    collect_class_opportunities,
)


def cache():
    return VersionedCache(InMemoryCacheBackend(), prefix="nexus:", ttl_seconds=300)


def collect_daker(db, *candidates, using_cache=None):
    return collect_class_opportunities(
        db,
        using_cache or cache(),
        source_type="daker",
        candidates=list(candidates),
    )


def candidate(source_type="daker", source_id="1", **over):
    category = "DAKER" if source_type == "daker" else "DACON"
    values = dict(
        source_type=source_type,
        source_id=f"{source_type}:{source_id}",
        source_category_code=category,
        source_category_name="해커톤" if category == "DAKER" else "경진대회",
        source_category_url=f"https://example.com/{source_type}",
        source_rank=1,
        title="AI 데이터 경진대회",
        summary="소개",
        source_url=f"https://example.com/{source_type}/{source_id}",
        thumbnail_url=None,
        sub_category_name="주최사",
        format_name="모집중",
        qualification=None,
        running_time_minutes=None,
        sale_price=1_000_000,
        list_price=None,
        badges=("모집중",),
    )
    values.update(over)
    return ClassOpportunityCandidate(**values)


def existing_fastcampus(db):
    db.add(Course(
        source_type="fastcampus", source_id="99",
        source_category_code="DATASCIENCEDL", source_category_name="AI TECH",
        source_category_url="https://fastcampus.co.kr/category_online_datasciencedl",
        source_rank=1, title="AI·데이터 경진 대회!", summary="기존",
        source_url="https://fastcampus.co.kr/existing", thumbnail_url=None,
        sub_category_name=None, format_name="올인원", qualification=None,
        running_time_minutes=None, sale_price=None, list_price=None,
        badges="BEST", status="published",
    ))
    db.commit()


def test_all_course_collectors_share_one_lock():
    assert (
        class_opportunities.course_collection_lock
        is fastcampus_collector.course_collection_lock
    )


def test_collect_skips_duplicate_title_across_existing_sources(db):
    existing_fastcampus(db)

    result = collect_class_opportunities(
        db, cache(), source_type="dacon", candidates=[candidate("dacon")]
    )

    assert (result.added, result.updated, result.hidden, result.skipped) == (0, 0, 0, 1)
    assert db.query(Course).count() == 1


def test_collect_skips_duplicate_when_existing_item_changes_title(db):
    existing_fastcampus(db)
    collect_daker(db, candidate(title="원래 해커톤 제목"))

    result = collect_daker(db, candidate(title="AI 데이터 경진 대회"))

    assert (result.updated, result.hidden, result.skipped) == (0, 1, 1)
    stored = db.query(Course).filter_by(source_id="daker:1").one()
    assert stored.title == "원래 해커톤 제목"
    assert stored.status == "hidden"


def test_collect_upserts_and_hides_items_no_longer_eligible(db):
    c = cache()
    collect_daker(
        db,
        candidate(source_id="1"),
        candidate(source_id="2", title="두 번째"),
        using_cache=c,
    )
    c.set("classes", "warm")

    result = collect_daker(
        db,
        candidate(
            source_id="1",
            title="변경된 제목",
            format_name="진행중",
            badges=("진행중",),
        ),
        using_cache=c,
    )

    assert (result.added, result.updated, result.hidden, result.skipped) == (0, 1, 1, 0)
    assert db.query(Course).filter_by(source_id="daker:1").one().title == "변경된 제목"
    assert db.query(Course).filter_by(source_id="daker:2").one().status == "hidden"
    assert c.get("classes") is None


def test_collect_skips_duplicate_source_id_within_batch(db):
    result = collect_class_opportunities(
        db, cache(), source_type="daker",
        candidates=[
            candidate(source_id="same", title="첫 번째"),
            candidate(
                source_id="same", title="두 번째",
                source_url="https://example.com/daker/other",
            ),
        ],
    )

    assert (result.added, result.skipped) == (1, 1)
    assert db.query(Course).filter_by(source_id="daker:same").one().title == "첫 번째"


def test_collect_restores_hidden_item_after_duplicate_disappears(db):
    collect_daker(db, candidate(title="원래 제목"))
    existing_fastcampus(db)
    collect_daker(db, candidate(title="AI 데이터 경진 대회"))
    fastcampus = db.query(Course).filter_by(source_type="fastcampus").one()
    fastcampus.status = "hidden"
    db.commit()

    result = collect_daker(db, candidate(title="AI 데이터 경진 대회"))

    assert (result.updated, result.hidden, result.skipped) == (1, 0, 0)
    assert db.query(Course).filter_by(source_id="daker:1").one().status == "published"


def test_collect_rekeys_same_opportunity_when_source_id_changes(db):
    collect_class_opportunities(
        db, cache(), source_type="daker",
        candidates=[
            candidate(
                source_id="old",
                title="ID가 바뀌는 해커톤",
                source_url="https://example.com/daker/stable",
            )
        ],
    )

    result = collect_class_opportunities(
        db, cache(), source_type="daker",
        candidates=[
            candidate(
                source_id="new",
                title="ID가 바뀌는 해커톤",
                source_url="https://example.com/daker/stable",
            )
        ],
    )

    assert (result.added, result.updated, result.hidden, result.skipped) == (0, 1, 0, 0)
    assert db.query(Course).filter_by(source_id="daker:old").one_or_none() is None
    assert db.query(Course).filter_by(source_id="daker:new").one().status == "published"
