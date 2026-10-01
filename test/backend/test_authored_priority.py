"""직접 작성 글의 24시간 우선 노출."""
from datetime import datetime, timedelta, timezone

from app.repositories.articles import latest_articles_per_type, list_articles

from shared import make_article as _make_article  # 리포지토리 테스트 공용 헬퍼
from shared import seed_category

NOW = datetime(2026, 9, 29, 6, 0, tzinfo=timezone.utc)


def make_article(db, cat, **over):
    return _make_article(db, cat, **{"published_at": NOW, **over})


def test_fresh_authored_article_leads_its_format(db):
    cat = seed_category(db)
    collected = make_article(
        db, cat, title="수집 뉴스레터", source_type="stibee",
        source_url="https://example.com/news", published_at=NOW,
    )
    authored = make_article(
        db, cat, title="직접 뉴스레터", source_type="authored",
        published_at=NOW - timedelta(hours=23),
    )
    result = list_articles(
        db, category_slug="curation", article_type="newsletter", now=NOW,
    )
    assert [item.id for item in result.items] == [authored.id, collected.id]


def test_authored_priority_expires_after_24_hours(db):
    cat = seed_category(db)
    authored = make_article(
        db, cat, title="지난 직접글", source_type="authored",
        published_at=NOW - timedelta(hours=25),
    )
    collected = make_article(
        db, cat, title="최신 수집글", source_type="stibee",
        source_url="https://example.com/new",
        published_at=NOW - timedelta(hours=1),
    )
    result = list_articles(
        db, category_slug="curation", article_type="newsletter", now=NOW,
    )
    assert [item.id for item in result.items] == [collected.id, authored.id]


def test_home_format_slot_prefers_fresh_authored(db):
    cat = seed_category(db)
    make_article(
        db, cat, title="수집 컬럼", source_type="brunch",
        source_url="https://brunch.co.kr/@w/1", article_type="column", published_at=NOW,
    )
    make_article(
        db, cat, title="직접 컬럼", article_type="column", source_type="authored",
        published_at=NOW - timedelta(hours=2),
    )
    picked = latest_articles_per_type(db, cat.id, ("column",), now=NOW)
    assert [item.title for item in picked] == ["직접 컬럼"]
