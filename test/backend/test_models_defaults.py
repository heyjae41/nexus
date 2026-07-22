"""DB 레벨 DEFAULT 검증 — ORM 을 우회한 raw INSERT 도 동작해야 한다.

ARCHITECTURE.md 는 display_order/is_active/created_at 등에 DEFAULT 를 명세하지만,
기존 모델은 SQLAlchemy 클라이언트 사이드 default 만 사용해 raw SQL 경로
(운영 배치, 수기 마이그레이션)가 NOT NULL 위반으로 실패했다.
"""
from sqlalchemy import text


def test_categories_raw_insert_uses_db_defaults(db):
    db.execute(text("INSERT INTO categories (slug, name) VALUES ('raw', '로우')"))
    db.commit()
    row = db.execute(
        text("SELECT display_order, is_active, created_at FROM categories WHERE slug='raw'")
    ).one()
    assert row.display_order == 0
    assert row.is_active in (True, 1)
    assert row.created_at is not None


def test_articles_raw_insert_uses_db_defaults(db):
    db.execute(text("INSERT INTO categories (slug, name) VALUES ('c', '카테고리')"))
    db.execute(
        text(
            "INSERT INTO articles (category_id, article_type, title, source_type, published_at) "
            "SELECT id, 'guide', '로우 인서트', 'internal', CURRENT_TIMESTAMP FROM categories WHERE slug='c'"
        )
    )
    db.commit()
    row = db.execute(
        text(
            "SELECT read_minutes, likes_count, comments_count, view_count, status, "
            "created_at, updated_at FROM articles WHERE title='로우 인서트'"
        )
    ).one()
    assert (row.read_minutes, row.likes_count, row.comments_count, row.view_count) == (4, 0, 0, 0)
    assert row.status == "published"
    assert row.created_at is not None and row.updated_at is not None


def test_community_post_raw_insert_uses_db_defaults(db):
    db.execute(text("INSERT INTO members (nickname) VALUES ('로우회원')"))
    db.execute(
        text(
            "INSERT INTO community_posts (member_id, author_name, tag, title, body) "
            "SELECT id, '로우회원', '팁', '제목', '본문' FROM members WHERE nickname='로우회원'"
        )
    )
    db.commit()
    row = db.execute(
        text(
            "SELECT likes_count, comments_count, status, created_at "
            "FROM community_posts WHERE title='제목'"
        )
    ).one()
    assert (row.likes_count, row.comments_count, row.status) == (0, 0, "published")
    assert row.created_at is not None


def test_community_fk_indexes_exist(engine):
    """FK 조회 컬럼 인덱스 — PG 는 FK 에 자동 인덱스를 만들지 않는다 (댓글/글 조회 경로)."""
    from sqlalchemy import inspect

    insp = inspect(engine)
    comment_idx = {i["name"] for i in insp.get_indexes("community_comments")}
    assert {"ix_community_comments_post", "ix_community_comments_member"} <= comment_idx
    post_idx = {i["name"] for i in insp.get_indexes("community_posts")}
    assert "ix_community_posts_member" in post_idx
