"""회원(닉네임 + 비밀번호) 등록/로그인 테스트.

정책: 닉네임이 식별자, 비밀번호는 영문·숫자를 각 1자 이상 포함한 8자 이상.
(특수문자·대소문자 조합은 선택 — 개인정보를 다루지 않는 서비스라 최소 조건만 강제)
- 신규 닉네임 → 회원 생성 (비밀번호 정책 검증 + 해시 저장)
- 기존 닉네임 → 비밀번호 검증 후 로그인 (불일치 시 AuthError)
"""
import pytest

from app.repositories.members import AuthError, get_member, register_member

PW = "Nexus1!pw"  # 정책을 만족하는 테스트 비밀번호


def reg(db, nickname, **kw):
    return register_member(db, nickname=nickname, password=PW, **kw)


def test_register_creates_member(db):
    member = reg(db, "김크레딧", role="직장인", interests="LLM,커리어")
    assert member.id is not None
    assert member.nickname == "김크레딧"
    assert get_member(db, member.id).nickname == "김크레딧"


def test_password_is_hashed_never_plaintext(db):
    member = reg(db, "김크레딧")
    assert member.password_hash != PW
    assert member.password_hash.startswith("pbkdf2_sha256$")


def test_password_policy_rejects_weak_with_reason(db):
    """조건 불만족 시 부족한 항목이 에러메시지에 담긴다."""
    cases = [
        ("Ab1!", "8자"),
        ("12345678!", "영문"),
        ("abcdefgh!", "숫자"),
        ("", "8자"),
    ]
    for bad, keyword in cases:
        with pytest.raises(ValueError, match=keyword):
            register_member(db, nickname=f"검증{keyword}", password=bad)


def test_password_policy_accepts_letters_and_digits_only(db):
    """영문+숫자 최소 조건만 채워도 가입되고, 특수문자·대문자는 선택이다."""
    minimal = register_member(db, nickname="최소조건", password="abcdef12")
    assert minimal.password_hash.startswith("pbkdf2_sha256$")
    assert register_member(db, nickname="강화조건", password="Abcdef1!")


def test_relogin_with_correct_password_returns_same_member(db):
    first = reg(db, "김크레딧", role="직장인")
    second = reg(db, "김크레딧", role="개발자")
    assert second.id == first.id
    # 재로그인 시 프로필(역할/관심사)은 최신 값으로 갱신된다
    assert second.role == "개발자"


def test_relogin_with_wrong_password_raises(db):
    reg(db, "김크레딧")
    with pytest.raises(AuthError):
        register_member(db, nickname="김크레딧", password="Wrong1!pw")


def test_login_does_not_revalidate_password_policy(db):
    """로그인(기존 닉네임)은 정책 검증이 아니라 일치 여부만 본다 —
    정책 강화 이전 가입자도 로그인 가능해야 한다."""
    reg(db, "김크레딧")
    with pytest.raises(AuthError):  # 정책 위반 문자열이라도 ValueError 가 아닌 인증 실패
        register_member(db, nickname="김크레딧", password="weak")


def test_register_rejects_blank_or_long_nickname(db):
    with pytest.raises(ValueError):
        reg(db, "   ")
    with pytest.raises(ValueError):
        reg(db, "가" * 51)


def test_register_trims_nickname(db):
    member = reg(db, "  김크레딧  ")
    assert member.nickname == "김크레딧"


def test_update_member_profile_fields(db):
    from app.repositories.members import update_member

    m = reg(db, "김크레딧", role="직장인")
    updated = update_member(db, m.id, nickname="새닉네임", role="개발자", interests="LLM")
    assert updated.nickname == "새닉네임"
    assert updated.role == "개발자"
    assert updated.interests == "LLM"


def test_update_member_rejects_taken_nickname(db):
    from app.repositories.members import update_member

    reg(db, "선점된닉네임")
    m = reg(db, "김크레딧")
    with pytest.raises(ValueError):
        update_member(db, m.id, nickname="선점된닉네임")


def test_update_member_unknown_id(db):
    from app.repositories.members import update_member

    with pytest.raises(LookupError):
        update_member(db, 999, nickname="x")


def test_delete_member_keeps_posts_but_detaches_and_reclaims_likes(db):
    """탈회: 글/댓글은 작성자명만 남기고 연결 해제, 좋아요는 회수(카운트 감소)."""
    from app.repositories.community import create_post, toggle_post_like
    from app.repositories.members import delete_member, get_member

    author = reg(db, "작성자")
    liker = reg(db, "탈회할사람")
    post = create_post(db, member_id=author.id, tag="팁", title="t", body="b")
    toggle_post_like(db, post_id=post.id, member_id=liker.id)
    assert post.likes_count == 1

    delete_member(db, liker.id)

    assert get_member(db, liker.id) is None
    db.refresh(post)
    assert post.likes_count == 0  # 탈회자의 좋아요 회수


def test_delete_member_like_reclaim_never_negative(db):
    """좋아요 회수는 어떤 경우에도 카운트를 음수로 만들지 않는다."""
    from app.models import CommunityPost
    from app.repositories.community import create_post, toggle_post_like
    from app.repositories.members import delete_member

    author = reg(db, "글쓴이")
    liker = reg(db, "좋아요회원")
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

    m = reg(db, "탈회작성자")
    post = create_post(db, member_id=m.id, tag="팁", title="남는 글", body="b")
    delete_member(db, m.id)
    found, _ = get_post_with_comments(db, post.id)
    assert found is not None            # 글은 남는다
    assert found.author_name == "탈회작성자"
    assert found.member_id is None      # 연결만 해제


def test_update_member_nickname_race_reports_nickname_conflict(db, monkeypatch):
    """닉네임 사전 체크 통과 후 커밋에서 UNIQUE 충돌(레이스)이 나도
    명확한 '닉네임 중복' 오류로 안내한다."""
    from app.repositories import members as members_mod
    from app.repositories.members import update_member

    a = reg(db, "가나다")
    reg(db, "라마바")

    # 레이스 재현: 사전 중복 체크가 통과된 것처럼 만들어 커밋 충돌 경로로 유도
    monkeypatch.setattr(members_mod, "_nickname_taken", lambda *args, **kw: False)
    with pytest.raises(ValueError, match="닉네임"):
        update_member(db, a.id, nickname="라마바")
