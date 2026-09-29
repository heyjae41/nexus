"""직접 작성 글의 24시간 우선 노출."""
from datetime import datetime, timedelta, timezone

from app.models import Category
from app.repositories.articles import create_article, latest_articles_per_type, list_articles

NOW = datetime(2026, 9, 29, 6, 0, tzinfo=timezone.utc)


def seed_category(db) -> Category:
    cat = Category(slug="curation", name="큐레이션", display_order=1)
    db.add(cat)
    db.commit()
    return cat


def make_article(db, cat, **over):
    fields = {
        "category_id": cat.id,
        "article_type": "newsletter",
        "title": "제목",
        "summary": "요약",
        "body_html": "<p>본문</p>",
        "author_name": "AI사업팀",
        "source_type": "internal",
        "published_at": NOW,
    }
    fields.update(over)
    return create_article(db, **fields)


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
