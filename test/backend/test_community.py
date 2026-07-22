"""커뮤니티 글/댓글 리포지토리·서비스 테스트."""
from app.repositories.community import (
    add_comment,
    create_post,
    get_post_with_comments,
    list_posts,
    toggle_post_like,
)
from app.repositories.members import register_member


def member(db, nickname="김크레딧"):
    return register_member(db, nickname=nickname, password="Nexus1!pw")


def member_post(db):
    m = member(db)
    return m, create_post(db, member_id=m.id, tag="팁", title="t", body="b")


def test_create_post_and_list(db):
    m = member(db)
    post = create_post(db, member_id=m.id, tag="노하우", title="첫 글", body="본문입니다")
    page = list_posts(db)
    assert page.total == 1
    assert page.items[0].id == post.id
    assert page.items[0].author_name == "김크레딧"
    assert page.items[0].tag == "노하우"


def test_create_post_requires_valid_member(db):
    import pytest

    with pytest.raises(LookupError):
        create_post(db, member_id=999, tag="팁", title="t", body="b")


def test_create_post_validates_fields(db):
    import pytest

    m = member(db)
    with pytest.raises(ValueError):
        create_post(db, member_id=m.id, tag="노하우", title="  ", body="b")
    with pytest.raises(ValueError):
        create_post(db, member_id=m.id, tag="이상한태그", title="t", body="b")
    with pytest.raises(ValueError):
        create_post(db, member_id=m.id, tag="팁", title="t", body="가" * 10001)


def test_list_posts_newest_first_with_pagination(db):
    m = member(db)
    for i in range(5):
        create_post(db, member_id=m.id, tag="팁", title=f"글{i}", body="b")
    page1 = list_posts(db, page=1, size=2)
    assert page1.total == 5
    assert [p.title for p in page1.items] == ["글4", "글3"]


def test_list_posts_filters_by_tag(db):
    m = member(db)
    create_post(db, member_id=m.id, tag="자료", title="공유 자료", body="b")
    create_post(db, member_id=m.id, tag="노하우", title="업무 노하우", body="b")

    page = list_posts(db, tag="자료")

    assert page.total == 1
    assert [post.title for post in page.items] == ["공유 자료"]


def test_list_posts_excludes_legacy_question_badges(db):
    from datetime import datetime, timezone

    from app.models import CommunityPost

    m = member(db)
    db.add(
        CommunityPost(
            member_id=m.id,
            author_name=m.nickname,
            tag="질문",
            title="레거시 질문",
            body="본문",
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    assert list_posts(db).total == 0


def test_comments_flow_updates_count(db):
    m = member(db)
    post = create_post(db, member_id=m.id, tag="자료", title="t", body="b")
    add_comment(db, post_id=post.id, member_id=m.id, body="첫 댓글")
    add_comment(db, post_id=post.id, member_id=m.id, body="둘째 댓글")

    found, comments = get_post_with_comments(db, post.id)
    assert found.comments_count == 2
    assert [c.body for c in comments] == ["첫 댓글", "둘째 댓글"]
    assert comments[0].author_name == "김크레딧"


def test_add_comment_requires_valid_member_and_post(db):
    import pytest

    m, post = member_post(db)
    with pytest.raises(LookupError):
        add_comment(db, post_id=post.id, member_id=999, body="x")
    with pytest.raises(LookupError):
        add_comment(db, post_id=9999, member_id=m.id, body="x")
    with pytest.raises(ValueError):
        add_comment(db, post_id=post.id, member_id=m.id, body="  ")


def test_toggle_post_like_per_member(db):
    """좋아요는 회원 기반 토글 — 같은 회원의 반복 호출은 켜기/끄기만 반복한다 (어뷰징 방지)."""
    m1 = member(db)
    m2 = member(db, "다른회원")
    post = create_post(db, member_id=m1.id, tag="팁", title="t", body="b")

    assert toggle_post_like(db, post_id=post.id, member_id=m1.id) == (1, True)
    assert toggle_post_like(db, post_id=post.id, member_id=m1.id) == (0, False)  # 취소
    assert toggle_post_like(db, post_id=post.id, member_id=m1.id) == (1, True)
    assert toggle_post_like(db, post_id=post.id, member_id=m2.id) == (2, True)   # 회원별 1개


def test_unlike_clears_stale_identity_before_relike(db):
    """삭제 전 객체 참조가 남아 있어도 같은 세션의 다음 토글은 재좋아요로 동작한다."""
    from app.models import CommunityPostLike

    m, post = member_post(db)
    assert toggle_post_like(db, post_id=post.id, member_id=m.id) == (1, True)
    retained = db.get(CommunityPostLike, (post.id, m.id))
    assert retained is not None

    assert toggle_post_like(db, post_id=post.id, member_id=m.id) == (0, False)
    assert retained not in db
    assert toggle_post_like(db, post_id=post.id, member_id=m.id) == (1, True)


def test_toggle_post_like_race_is_idempotent(db, monkeypatch):
    """동시 좋아요 레이스: 커밋 시 PK 충돌(IntegrityError)이 나도 500 대신 멱등 결과로 수렴한다."""
    from app.models import CommunityPostLike

    m, post = member_post(db)
    toggle_post_like(db, post_id=post.id, member_id=m.id)  # 좋아요 반영 (count=1)

    # 레이스 재현: 첫 존재 확인만 None 을 보게 해(다른 요청의 INSERT 를 아직 못 본 상태)
    # 중복 INSERT → 커밋 시 IntegrityError 경로로 유도한다.
    real_get = db.get
    seen = {"n": 0}

    def racy_get(entity, ident, **kw):
        if entity is CommunityPostLike:
            seen["n"] += 1
            if seen["n"] == 1:
                return None
        return real_get(entity, ident, **kw)

    monkeypatch.setattr(db, "get", racy_get)
    likes, liked = toggle_post_like(db, post_id=post.id, member_id=m.id)
    assert (likes, liked) == (1, True)  # 이미 좋아요 상태 그대로 — 카운트 중복 증가 없음


def test_concurrent_unlike_does_not_decrement_count_twice(tmp_path):
    """두 세션이 같은 좋아요를 해제해도 실제 삭제한 요청만 카운트를 감소시킨다."""
    from sqlalchemy import create_engine, delete, update
    from sqlalchemy.orm import sessionmaker

    from app.models import Base, CommunityPost, CommunityPostLike

    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'unlike-race.db'}", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    first, second = factory(), factory()
    try:
        m = member(first)
        post = create_post(first, member_id=m.id, tag="팁", title="t", body="b")
        assert toggle_post_like(first, post_id=post.id, member_id=m.id) == (1, True)

        # 첫 요청이 좋아요 행과 글을 읽은 직후, 두 번째 요청이 먼저 해제를 완료한다.
        stale_like = first.get(CommunityPostLike, (post.id, m.id))
        assert stale_like is not None
        first.get(CommunityPost, post.id)
        first.commit()
        second.execute(
            delete(CommunityPostLike).where(
                CommunityPostLike.post_id == post.id,
                CommunityPostLike.member_id == m.id,
            )
        )
        second.execute(
            update(CommunityPost)
            .where(CommunityPost.id == post.id)
            .values(likes_count=CommunityPost.likes_count - 1)
        )
        second.commit()

        assert toggle_post_like(first, post_id=post.id, member_id=m.id) == (0, False)
        second.expire_all()
        assert second.get(CommunityPost, post.id).likes_count == 0
    finally:
        first.close()
        second.close()
        engine.dispose()


def test_toggle_post_like_validations(db):
    import pytest

    m, post = member_post(db)
    with pytest.raises(LookupError):
        toggle_post_like(db, post_id=9999, member_id=m.id)
    with pytest.raises(LookupError):
        toggle_post_like(db, post_id=post.id, member_id=9999)


def test_like_rejected_on_hidden_post(db):
    import pytest

    m, post = member_post(db)
    post.status = "hidden"
    db.commit()
    with pytest.raises(LookupError):
        toggle_post_like(db, post_id=post.id, member_id=m.id)


def test_comments_are_limited(db):
    from app.repositories.community import COMMENTS_LIMIT

    m, post = member_post(db)
    for i in range(COMMENTS_LIMIT + 5):
        add_comment(db, post_id=post.id, member_id=m.id, body=f"댓글{i}")
    _, comments = get_post_with_comments(db, post.id)
    assert len(comments) == COMMENTS_LIMIT


def test_delete_post_by_author_removes_comments_and_likes(db):
    """본인 글 삭제 — 글과 함께 댓글/좋아요도 제거된다 (e2e 데이터 정리에도 사용)."""
    from app.repositories.community import delete_post

    m, post = member_post(db)
    add_comment(db, post_id=post.id, member_id=m.id, body="댓글")
    toggle_post_like(db, post_id=post.id, member_id=m.id)

    delete_post(db, post_id=post.id, member_id=m.id)

    assert list_posts(db).total == 0
    gone, comments = get_post_with_comments(db, post.id)
    assert gone is None and comments == []


def test_delete_post_only_by_author(db):
    import pytest

    from app.repositories.community import delete_post

    m1 = member(db)
    m2 = member(db, "다른회원")
    post = create_post(db, member_id=m1.id, tag="팁", title="t", body="b")

    with pytest.raises(ValueError):
        delete_post(db, post_id=post.id, member_id=m2.id)  # 남의 글
    with pytest.raises(LookupError):
        delete_post(db, post_id=9999, member_id=m1.id)  # 없는 글
    assert list_posts(db).total == 1
