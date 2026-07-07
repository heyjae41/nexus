"""시드 스크립트 테스트: 카테고리(메뉴) + 샘플 큐레이션 글, 멱등성 보장."""
from app.models import Article, Category
from app.seed import seed_all


def test_seed_creates_categories_and_articles(db):
    seed_all(db)
    cats = db.query(Category).order_by(Category.display_order).all()
    assert [c.slug for c in cats] == ["curation", "class", "community", "meetpl", "hotdeal"]
    assert cats[0].name == "큐레이션"

    articles = db.query(Article).all()
    assert len(articles) == 6
    assert {a.article_type for a in articles} <= {"newsletter", "column", "guide"}
    assert all(a.source_type == "internal" for a in articles)
    assert all(a.body_html for a in articles)
    assert all(a.key_visual_html for a in articles)


def test_seed_is_idempotent(db):
    seed_all(db)
    seed_all(db)
    assert db.query(Category).count() == 5
    assert db.query(Article).count() == 6
