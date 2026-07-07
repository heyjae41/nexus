"""카테고리/글 리포지토리 테스트."""
from datetime import datetime, timezone

from app.models import Category
from app.repositories.articles import (
    create_article,
    get_article,
    increment_view,
    list_articles,
)
from app.repositories.categories import list_active_categories


def seed_category(db, slug="curation", name="큐레이션", order=1) -> Category:
    cat = Category(slug=slug, name=name, display_order=order)
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
        "published_at": datetime(2026, 7, 7, tzinfo=timezone.utc),
    }
    fields.update(over)
    return create_article(db, **fields)


def test_list_active_categories_ordered(db):
    seed_category(db, "community", "커뮤니티", order=3)
    seed_category(db, "curation", "큐레이션", order=1)
    inactive = Category(slug="hidden", name="숨김", display_order=0, is_active=False)
    db.add(inactive)
    db.commit()
    cats = list_active_categories(db)
    assert [c.slug for c in cats] == ["curation", "community"]


def test_create_and_get_article(db):
    cat = seed_category(db)
    art = make_article(db, cat, title="AI가 바꾸는 결제")
    found = get_article(db, art.id)
    assert found is not None
    assert found.title == "AI가 바꾸는 결제"
    assert found.status == "published"
    assert found.read_minutes == 4


def test_list_articles_filters_and_sorts_desc(db):
    cat = seed_category(db)
    other = seed_category(db, "class", "클래스", order=2)
    old = make_article(db, cat, title="old",
                       published_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    new = make_article(db, cat, title="new",
                       published_at=datetime(2026, 7, 1, tzinfo=timezone.utc))
    make_article(db, other, title="다른 카테고리")
    make_article(db, cat, title="가이드", article_type="guide")

    result = list_articles(db, category_slug="curation")
    dates = [a.published_at for a in result.items]
    assert dates == sorted(dates, reverse=True), "최신순 정렬이어야 한다"
    assert all(a.category_id == cat.id for a in result.items)
    assert result.total == 3

    newsletters = list_articles(db, category_slug="curation", article_type="newsletter")
    assert {a.article_type for a in newsletters.items} == {"newsletter"}
    assert newsletters.total == 2
    assert old.id in [a.id for a in newsletters.items]
    assert new.id in [a.id for a in newsletters.items]


def test_list_articles_pagination(db):
    cat = seed_category(db)
    for i in range(5):
        make_article(db, cat, title=f"글{i}",
                     published_at=datetime(2026, 7, i + 1, tzinfo=timezone.utc))
    page1 = list_articles(db, page=1, size=2)
    page2 = list_articles(db, page=2, size=2)
    assert page1.total == 5
    assert len(page1.items) == 2
    assert len(page2.items) == 2
    assert page1.items[0].title == "글4"  # 최신순
    assert page2.items[0].title == "글2"


def test_list_articles_excludes_hidden(db):
    cat = seed_category(db)
    make_article(db, cat, title="공개")
    make_article(db, cat, title="비공개", status="hidden")
    result = list_articles(db)
    assert [a.title for a in result.items] == ["공개"]


def test_increment_view(db):
    cat = seed_category(db)
    art = make_article(db, cat)
    increment_view(db, art.id)
    increment_view(db, art.id)
    assert get_article(db, art.id).view_count == 2


def test_duplicate_content_filename_rejected(db):
    import pytest
    from sqlalchemy.exc import IntegrityError

    cat = seed_category(db)
    make_article(db, cat, content_filename="20260707_뉴스레터_A.html")
    with pytest.raises(IntegrityError):
        make_article(db, cat, content_filename="20260707_뉴스레터_A.html")
