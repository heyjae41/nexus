"""뉴스레터 수집기 테스트: 신규 발행분을 큐레이션 글(article_type=newsletter)로 반영한다.

- source_url 기준 중복 제거 (재수집 시 신규만 추가)
- 신규 추가가 있으면 캐시 무효화 (즉시 조회 가능 불변식)
- 수집 이력(newsletter_collect_runs) 기록
"""
from datetime import datetime, timezone

import pytest

from app.models import Article, NewsletterCollectRun
from app.services.newsletter_collector import collect_newsletters
from app.services.newsletter_fetcher import NewsletterCandidate

from shared import make_cache, seed_curation  # noqa: E402 — 수집 테스트 공용 헬퍼


def cand(slug="a", **over) -> NewsletterCandidate:
    fields = dict(
        title=f"뉴스레터 {slug}",
        url=f"https://stib.ee/{slug}",
        publisher="모두레터",
        source_type="stibee",
        summary="요약",
        published_at=datetime(2026, 7, 22, 8, 0, tzinfo=timezone.utc),
        thumbnail_url=None,
    )
    fields.update(over)
    return NewsletterCandidate(**fields)


def test_collect_saves_all_new_issues_as_newsletter_articles(db):
    seed_curation(db)
    cache = make_cache()
    result = collect_newsletters(db, cache, candidates=[cand("1"), cand("2")])
    assert result.candidates == 2
    assert result.added == 2

    articles = db.query(Article).order_by(Article.id).all()
    assert len(articles) == 2
    a = articles[0]
    assert a.article_type == "newsletter"
    assert a.source_type == "stibee"
    assert a.source_url == "https://stib.ee/1"
    assert a.author_name == "모두레터"
    assert a.summary == "요약"
    assert a.published_at is not None
    run = db.query(NewsletterCollectRun).one()
    assert run.status == "success"
    assert run.candidates_count == 2
    assert run.added_count == 2


def test_collect_dedups_by_source_url_and_within_batch(db):
    seed_curation(db)
    cache = make_cache()
    collect_newsletters(db, cache, candidates=[cand("1"), cand("2")])
    result = collect_newsletters(db, cache, candidates=[cand("2"), cand("3"), cand("3")])
    assert result.added == 1
    assert db.query(Article).count() == 3


def test_collect_bumps_cache_only_when_new(db):
    seed_curation(db)
    cache = make_cache()
    collect_newsletters(db, cache, candidates=[cand("1")])
    cache.set("home", "warm")
    collect_newsletters(db, cache, candidates=[cand("1")])  # 전부 중복
    assert cache.get("home") == "warm"
    collect_newsletters(db, cache, candidates=[cand("2")])
    assert cache.get("home") is None


def test_collect_empty_records_empty_run(db):
    seed_curation(db)
    cache = make_cache()
    result = collect_newsletters(db, cache, candidates=[])
    assert result.added == 0
    assert db.query(NewsletterCollectRun).one().status == "empty"


def test_collect_truncates_fields_to_column_limits(db):
    """PG 의 VARCHAR 길이 제약(제목 300/요약 500)을 넘는 값은 잘라서 저장한다.

    SQLite 테스트 DB 는 길이를 강제하지 않으므로 값 자체를 검증한다."""
    seed_curation(db)
    cache = make_cache()
    collect_newsletters(
        db, cache,
        candidates=[cand("1", title="긴제목" * 200, summary="긴요약" * 300)],
    )
    saved = db.query(Article).one()
    assert len(saved.title) <= 300
    assert len(saved.summary) <= 500


def test_collect_skips_candidate_without_published_at(db):
    """published_at 은 NOT NULL — 날짜 없는 후보는 저장하지 않는다."""
    seed_curation(db)
    cache = make_cache()
    result = collect_newsletters(db, cache, candidates=[cand("1", published_at=None), cand("2")])
    assert result.added == 1
    assert db.query(Article).one().source_url == "https://stib.ee/2"


def test_collect_partial_conflict_keeps_rest_of_batch(db, monkeypatch):
    """동시 수집 레이스로 배치 중 1건이 UNIQUE 충돌해도 나머지는 유실하지 않는다."""
    from app.services import newsletter_collector as collector_mod

    seed_curation(db)
    cache = make_cache()
    collect_newsletters(db, cache, candidates=[cand("1")])  # "1" 은 이미 저장됨

    # 레이스 재현: 사전 중복 체크가 아무것도 못 본 것처럼 만든다
    monkeypatch.setattr(collector_mod, "_existing_urls", lambda db_, cands: set())
    result = collect_newsletters(db, cache, candidates=[cand("1"), cand("2"), cand("3")])

    assert result.added == 2
    assert db.query(Article).count() == 3
    runs = db.query(NewsletterCollectRun).order_by(NewsletterCollectRun.id).all()
    assert runs[-1].status == "success"
    assert runs[-1].added_count == 2


def test_collect_records_failed_run_on_db_error(db):
    seed_curation(db)
    cache = make_cache()
    broken = cand("1", title=None)  # NOT NULL 위반 유도
    with pytest.raises(Exception):
        collect_newsletters(db, cache, candidates=[broken])
    run = db.query(NewsletterCollectRun).one()
    assert run.status == "failed"
    assert run.error_message


def test_collect_requires_curation_category(db):
    cache = make_cache()
    with pytest.raises(ValueError):
        collect_newsletters(db, cache, candidates=[cand("1")])


def test_newsletter_card_links_to_source_with_ref(db):
    """수집 뉴스레터 카드는 외부 원문으로 이동하며 항상 ref 파라미터를 붙인다."""
    from app.serializers import serialize_article_card

    seed_curation(db)
    cache = make_cache()
    collect_newsletters(
        db, cache,
        candidates=[
            cand("1"),
            cand(
                "kma-894",
                source_type="kma",
                url="https://www.kma.or.kr/kr/usrs/eduRegMgnt/eduRegMgntForm.do?p_brd_seq=894",
            ),
            cand(
                "aitimes-213127",
                source_type="aitimes",
                url="https://www.aitimes.com/news/articleView.html?idxno=213127",
            ),
        ],
    )
    cards = [serialize_article_card(a) for a in db.query(Article).order_by(Article.id)]
    assert cards[0]["isExternal"] is True
    assert cards[0]["linkUrl"] == "https://stib.ee/1?ref=nexus.bccard.ai"
    assert cards[1]["isExternal"] is True
    assert "ref=nexus.bccard.ai" in cards[1]["linkUrl"]
    assert "p_brd_seq=894" in cards[1]["linkUrl"]
    assert cards[2]["isExternal"] is True
    assert cards[2]["linkUrl"] == (
        "https://www.aitimes.com/news/articleView.html?idxno=213127&ref=nexus.bccard.ai"
    )
