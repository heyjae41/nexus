"""회원(경량 닉네임 기반) 등록/식별 테스트.

정책: 비밀번호 없는 프로토타입 회원 — 닉네임이 식별자다.
- 신규 닉네임 → 회원 생성
- 기존 닉네임 → 기존 회원 반환 (재온보딩 = 로그인)
"""
from app.repositories.members import get_member, register_member


def test_register_creates_member(db):
    member = register_member(db, nickname="김크레딧", role="직장인", interests="LLM,커리어")
    assert member.id is not None
    assert member.nickname == "김크레딧"
    assert get_member(db, member.id).nickname == "김크레딧"


def test_register_existing_nickname_returns_same_member(db):
    first = register_member(db, nickname="김크레딧", role="직장인")
    second = register_member(db, nickname="김크레딧", role="개발자")
    assert second.id == first.id
    # 재온보딩 시 프로필(역할/관심사)은 최신 값으로 갱신된다
    assert second.role == "개발자"


def test_register_rejects_blank_or_long_nickname(db):
    import pytest

    with pytest.raises(ValueError):
        register_member(db, nickname="   ")
    with pytest.raises(ValueError):
        register_member(db, nickname="가" * 51)


def test_register_trims_nickname(db):
    member = register_member(db, nickname="  김크레딧  ")
    assert member.nickname == "김크레딧"


def test_register_with_email(db):
    member = register_member(db, nickname="김크레딧", email="heyjae@bccard.com")
    assert member.email == "heyjae@bccard.com"


def test_update_member_profile_fields(db):
    from app.repositories.members import update_member

    m = register_member(db, nickname="김크레딧", role="직장인")
    updated = update_member(db, m.id, nickname="새닉네임", role="개발자", interests="LLM")
    assert updated.nickname == "새닉네임"
    assert updated.role == "개발자"
    assert updated.interests == "LLM"


def test_update_member_email_set_once_only(db):
    """이메일은 수정 불가 — 비어 있을 때 최초 1회만 등록할 수 있다."""
    import pytest

    from app.repositories.members import update_member

    m = register_member(db, nickname="김크레딧")
    updated = update_member(db, m.id, email="heyjae@bccard.com")  # 최초 등록 허용
    assert updated.email == "heyjae@bccard.com"
    with pytest.raises(ValueError):
        update_member(db, m.id, email="other@bccard.com")  # 변경은 거부


def test_update_member_rejects_taken_nickname(db):
    import pytest

    from app.repositories.members import update_member

    register_member(db, nickname="선점된닉네임")
    m = register_member(db, nickname="김크레딧")
    with pytest.raises(ValueError):
        update_member(db, m.id, nickname="선점된닉네임")


def test_update_member_unknown_id(db):
    import pytest

    from app.repositories.members import update_member

    with pytest.raises(LookupError):
        update_member(db, 999, nickname="x")


def test_delete_member_keeps_posts_but_detaches_and_reclaims_likes(db):
    """탈회: 글/댓글은 작성자명만 남기고 연결 해제, 좋아요는 회수(카운트 감소)."""
    from app.repositories.community import create_post, toggle_post_like
    from app.repositories.members import delete_member, get_member

    author = register_member(db, nickname="작성자")
    liker = register_member(db, nickname="탈회할사람")
    post = create_post(db, member_id=author.id, tag="팁", title="t", body="b")
    toggle_post_like(db, post_id=post.id, member_id=liker.id)
    assert post.likes_count == 1

    delete_member(db, liker.id)

    assert get_member(db, liker.id) is None
    db.refresh(post)
    assert post.likes_count == 0  # 탈회자의 좋아요 회수


def test_email_unique_conflict_raises_value_error(db):
    """같은 이메일 중복 등록은 500 이 아니라 명확한 ValueError 여야 한다."""
    import pytest

    register_member(db, nickname="첫회원", email="dup@bccard.com")
    with pytest.raises(ValueError):
        register_member(db, nickname="둘째회원", email="dup@bccard.com")


def test_register_existing_member_with_different_email_raises(db):
    """재온보딩 시 다른 이메일 전달은 조용히 무시하지 않고 거부한다 (set-once 일관성)."""
    import pytest

    register_member(db, nickname="김크레딧", email="first@bccard.com")
    with pytest.raises(ValueError):
        register_member(db, nickname="김크레딧", email="second@bccard.com")


def test_update_email_same_value_with_whitespace_ok(db):
    """공백만 다른 동일 이메일은 수정 거부 대상이 아니다."""
    from app.repositories.members import update_member

    m = register_member(db, nickname="김크레딧", email="a@bccard.com")
    updated = update_member(db, m.id, email="  a@bccard.com  ")
    assert updated.email == "a@bccard.com"


def test_email_format_validation(db):
    import pytest

    for bad in ["@", "a@", "@b.com", "a@b", "no-at-sign"]:
        with pytest.raises(ValueError):
            register_member(db, nickname=f"이메일검증{bad[:2]}", email=bad)


def test_delete_member_like_reclaim_never_negative(db):
    """좋아요 회수는 어떤 경우에도 카운트를 음수로 만들지 않는다."""
    from app.models import CommunityPost
    from app.repositories.community import create_post, toggle_post_like
    from app.repositories.members import delete_member

    author = register_member(db, nickname="글쓴이")
    liker = register_member(db, nickname="좋아요회원")
    post = create_post(db, member_id=author.id, tag="팁", title="t", body="b")
    toggle_post_like(db, post_id=post.id, member_id=liker.id)
    # 레이스 재현: 카운트가 이미 앞질러 감소한 비정상 상태
    db.query(CommunityPost).filter_by(id=post.id).update({"likes_count": 0})
    db.commit()

    delete_member(db, liker.id)
    db.refresh(post)
    assert post.likes_count == 0  # -1 이 아니라 0 에서 멈춘다


def test_delete_member_detaches_own_posts(db):
    from app.repositories.community import create_post, get_post_with_comments
    from app.repositories.members import delete_member

    m = register_member(db, nickname="탈회작성자")
    post = create_post(db, member_id=m.id, tag="팁", title="남는 글", body="b")
    delete_member(db, m.id)
    found, _ = get_post_with_comments(db, post.id)
    assert found is not None            # 글은 남는다
    assert found.author_name == "탈회작성자"
    assert found.member_id is None      # 연결만 해제
