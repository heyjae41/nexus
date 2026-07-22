"""HttpOnly 쿠키용 서버 로그인 세션 저장소."""
from datetime import timedelta
import hashlib
import secrets

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AuthSession, Member, utcnow

SESSION_DAYS = 30


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, member_id: int) -> str:
    # 만료 세션은 발급 시점에 함께 정리해 테이블이 무한 누적되지 않게 한다
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= utcnow()))
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            member_id=member_id,
            token_hash=_token_hash(token),
            expires_at=utcnow() + timedelta(days=SESSION_DAYS),
        )
    )
    db.commit()
    return token


def get_session_member(db: Session, token: str | None) -> Member | None:
    if not token:
        return None
    stmt = (
        select(Member)
        .join(AuthSession, AuthSession.member_id == Member.id)
        .where(
            AuthSession.token_hash == _token_hash(token),
            AuthSession.expires_at > utcnow(),
        )
    )
    return db.scalars(stmt).first()


def delete_session(db: Session, token: str | None) -> None:
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == _token_hash(token)))
        db.commit()


def delete_member_sessions(db: Session, member_id: int) -> None:
    db.execute(delete(AuthSession).where(AuthSession.member_id == member_id))
