"""회원 리포지토리 — 닉네임 기반 경량 회원 (비밀번호 없음, 프로토타입 정책).

같은 닉네임으로 재온보딩하면 기존 회원을 반환한다 (= 로그인).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Member

NICKNAME_MAX = 50


def register_member(
    db: Session,
    *,
    nickname: str,
    role: str | None = None,
    interests: str | None = None,
) -> Member:
    name = (nickname or "").strip()
    if not name:
        raise ValueError("닉네임을 입력해 주세요")
    if len(name) > NICKNAME_MAX:
        raise ValueError(f"닉네임은 {NICKNAME_MAX}자 이내여야 합니다")

    member = db.scalars(select(Member).where(Member.nickname == name)).first()
    if member is None:
        member = Member(nickname=name)
        db.add(member)
    # 재온보딩 시 프로필은 최신 값으로 갱신
    if role is not None:
        member.role = role
    if interests is not None:
        member.interests = interests
    db.commit()
    db.refresh(member)
    return member


def get_member(db: Session, member_id: int) -> Member | None:
    return db.get(Member, member_id)
