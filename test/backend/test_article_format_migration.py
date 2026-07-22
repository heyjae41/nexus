"""article_type 레거시 값(brunch) → 글 포맷(column) 데이터 마이그레이션 검증."""
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from app.models import Article, Category


def test_legacy_brunch_article_type_is_migrated_to_column(db):
    category = Category(slug="curation", name="큐레이션", display_order=1)
    db.add(category)
    db.flush()
    article = Article(
        category_id=category.id,
        article_type="brunch",
        title="AI는 정말 미국 노동시장을 바꾸고 있는가?",
        source_type="brunch",
        source_url="https://brunch.co.kr/@writer/1",
        published_at=datetime(2026, 7, 14, tzinfo=timezone.utc),
    )
    db.add(article)
    db.commit()

    migration = (
        Path(__file__).parents[2]
        / "backend/migrations/008_articles_format_not_source.sql"
    ).read_text(encoding="utf-8")
    db.execute(text(migration))
    db.commit()
    db.refresh(article)

    assert article.article_type == "column"
    assert article.source_type == "brunch"
