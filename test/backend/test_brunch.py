"""브런치 수집기 테스트.

정책(범위 문서):
- 12시간 주기로 brunch.co.kr 의 AI 관련 글만 수집한다.
- 해당 기간 동안 댓글수+좋아요수 합이 가장 큰 글 1건을 선정해 목록에 노출한다.
- 클릭 시 원글 브런치 주소로 이동하며 항상 ?ref=nexus.bccard.ai 를 붙인다.
"""
from datetime import datetime, timezone

from app.cache import InMemoryCacheBackend, VersionedCache
from app.models import BrunchCollectRun, Category
from app.repositories.articles import list_articles
from app.services.brunch import (
    BrunchCandidate,
    collect_and_pick,
    is_ai_related,
    pick_top,
)

WINDOW = (
    datetime(2026, 7, 7, 0, 0, tzinfo=timezone.utc),
    datetime(2026, 7, 7, 12, 0, tzinfo=timezone.utc),
)


def cand(**over) -> BrunchCandidate:
    fields = dict(
        title="생성형 AI로 업무 자동화하기",
        url="https://brunch.co.kr/@writer/10",
        author="작가",
        likes=10,
        comments=5,
        summary="AI 활용기",
    )
    fields.update(over)
    return BrunchCandidate(**fields)


def make_cache():
    return VersionedCache(InMemoryCacheBackend(), prefix="nexus:", ttl_seconds=300)


def seed_curation(db):
    db.add(Category(slug="curation", name="큐레이션", display_order=1))
    db.commit()


def test_is_ai_related_filters_by_keywords():
    assert is_ai_related(cand(title="LLM 프롬프트 잘 쓰는 법", summary=""))
    assert is_ai_related(cand(title="일상", summary="머신러닝 공부 후기"))
    assert not is_ai_related(cand(title="제주도 여행기", summary="맛집 추천"))


def test_pick_top_by_likes_plus_comments():
    a = cand(url="https://brunch.co.kr/@w/1", likes=10, comments=1)   # 11
    b = cand(url="https://brunch.co.kr/@w/2", likes=5, comments=20)   # 25
    c = cand(url="https://brunch.co.kr/@w/3", likes=12, comments=3)   # 15
    assert pick_top([a, b, c]).url == b.url


def test_collect_and_pick_saves_thumbnail(db):
    seed_curation(db)
    cache = make_cache()
    picked = collect_and_pick(
        db, cache,
        candidates=[cand(thumbnail_url="https://t1.kakaocdn.net/brunch/cover.png")],
        window_start=WINDOW[0], window_end=WINDOW[1],
    )
    assert picked.thumbnail_url == "https://t1.kakaocdn.net/brunch/cover.png"


def test_collect_and_pick_saves_brunch_article(db):
    seed_curation(db)
    cache = make_cache()
    picked = collect_and_pick(
        db, cache,
        candidates=[
            cand(url="https://brunch.co.kr/@w/1", likes=1, comments=0),
            cand(url="https://brunch.co.kr/@w/2", title="AI 도입기", likes=9, comments=9),
            cand(url="https://brunch.co.kr/@w/3", title="여행기", summary="맛집", likes=99, comments=99),
        ],
        window_start=WINDOW[0], window_end=WINDOW[1],
    )
    # AI 무관 글(여행기)은 아무리 인기가 많아도 제외된다
    assert picked is not None
    assert picked.source_url == "https://brunch.co.kr/@w/2"
    arts = list_articles(db)
    assert arts.total == 1
    art = arts.items[0]
    assert art.source_type == "brunch"
    assert art.article_type == "brunch"
    assert art.likes_count == 9
    assert art.comments_count == 9

    run = db.query(BrunchCollectRun).one()
    assert run.status == "success"
    assert run.candidates_count == 3
    assert run.picked_article_id == picked.id


def test_collect_and_pick_dedups_already_saved_url(db):
    seed_curation(db)
    cache = make_cache()
    c1 = cand(url="https://brunch.co.kr/@w/1", likes=50, comments=0)
    c2 = cand(url="https://brunch.co.kr/@w/2", title="AI 후기", likes=10, comments=0)
    collect_and_pick(db, cache, candidates=[c1], window_start=WINDOW[0], window_end=WINDOW[1])
    picked = collect_and_pick(
        db, cache, candidates=[c1, c2], window_start=WINDOW[0], window_end=WINDOW[1]
    )
    # 이미 저장된 글은 다시 선정하지 않고 차순위를 선정한다
    assert picked.source_url == "https://brunch.co.kr/@w/2"
    assert list_articles(db).total == 2


def test_collect_and_pick_empty_records_run(db):
    seed_curation(db)
    cache = make_cache()
    picked = collect_and_pick(
        db, cache, candidates=[cand(title="여행", summary="바다")],
        window_start=WINDOW[0], window_end=WINDOW[1],
    )
    assert picked is None
    run = db.query(BrunchCollectRun).one()
    assert run.status == "empty"
    assert list_articles(db).total == 0


def test_collect_and_pick_records_failed_run_on_error(db):
    """발행 중 예외가 나도 수집 이력(status=failed)은 남아야 한다."""
    import pytest

    cache = make_cache()  # curation 카테고리를 시드하지 않아 publish 가 실패한다
    with pytest.raises(ValueError):
        collect_and_pick(
            db, cache, candidates=[cand()],
            window_start=WINDOW[0], window_end=WINDOW[1],
        )
    run = db.query(BrunchCollectRun).one()
    assert run.status == "failed"
    assert run.error_message
    assert run.picked_article_id is None


def test_collect_and_pick_bumps_cache_only_on_success(db):
    seed_curation(db)
    cache = make_cache()
    cache.set("home", "warm")
    collect_and_pick(db, cache, candidates=[cand(title="여행", summary="바다")],
                     window_start=WINDOW[0], window_end=WINDOW[1])
    assert cache.get("home") == "warm"

    collect_and_pick(db, cache, candidates=[cand()],
                     window_start=WINDOW[0], window_end=WINDOW[1])
    assert cache.get("home") is None
