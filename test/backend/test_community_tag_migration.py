"""폐지된 질문 배지 게시물 숨김 마이그레이션 검증."""
from pathlib import Path

from sqlalchemy import text

from app.models import CommunityPost


def test_legacy_question_posts_are_hidden(db):
    post = CommunityPost(
        author_name="레거시 사용자",
        tag="질문",
        title="기존 질문",
        body="본문",
    )
    db.add(post)
    db.commit()

    migration = (
        Path(__file__).parents[2]
        / "backend/migrations/009_hide_legacy_question_posts.sql"
    ).read_text(encoding="utf-8")
    db.execute(text(migration))
    db.commit()
    db.refresh(post)

    assert post.tag == "질문"
    assert post.status == "hidden"
