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
