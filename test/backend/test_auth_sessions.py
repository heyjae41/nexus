"""서버 로그인 세션 저장소 — 만료 세션이 무한 누적되지 않아야 한다."""
from datetime import timedelta

from sqlalchemy import select

from app.models import AuthSession, utcnow
from app.repositories.auth import create_session, get_session_member
from app.repositories.members import register_member

PW = "Nexus1!pw"


def test_create_session_purges_expired_rows(db):
    """로그인(세션 발급) 시 만료된 세션 행을 함께 정리한다."""
    member = register_member(db, nickname="세션회원", password=PW)
    db.add(
        AuthSession(
            member_id=member.id,
            token_hash="0" * 64,
            expires_at=utcnow() - timedelta(days=1),
        )
    )
    db.commit()

    token = create_session(db, member.id)

    remaining = db.scalars(select(AuthSession)).all()
    assert len(remaining) == 1
    assert remaining[0].token_hash != "0" * 64  # 만료 행은 지워지고 새 세션만 남는다
    assert get_session_member(db, token).id == member.id


def test_expired_session_is_not_authenticated(db):
    member = register_member(db, nickname="만료회원", password=PW)
    db.add(
        AuthSession(
            member_id=member.id,
            token_hash="1" * 64,
            expires_at=utcnow() - timedelta(seconds=1),
        )
    )
    db.commit()
    assert get_session_member(db, "아무토큰") is None
