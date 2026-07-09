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
    return register_member(db, nickname=nickname)


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

    m = member(db)
    post = create_post(db, member_id=m.id, tag="팁", title="t", body="b")
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


def test_toggle_post_like_validations(db):
    import pytest

    m = member(db)
    post = create_post(db, member_id=m.id, tag="팁", title="t", body="b")
    with pytest.raises(LookupError):
        toggle_post_like(db, post_id=9999, member_id=m.id)
    with pytest.raises(LookupError):
        toggle_post_like(db, post_id=post.id, member_id=9999)


def test_like_rejected_on_hidden_post(db):
    import pytest

    m = member(db)
    post = create_post(db, member_id=m.id, tag="팁", title="t", body="b")
    post.status = "hidden"
    db.commit()
    with pytest.raises(LookupError):
        toggle_post_like(db, post_id=post.id, member_id=m.id)


def test_comments_are_limited(db):
    from app.repositories.community import COMMENTS_LIMIT

    m = member(db)
    post = create_post(db, member_id=m.id, tag="팁", title="t", body="b")
    for i in range(COMMENTS_LIMIT + 5):
        add_comment(db, post_id=post.id, member_id=m.id, body=f"댓글{i}")
    _, comments = get_post_with_comments(db, post.id)
    assert len(comments) == COMMENTS_LIMIT
