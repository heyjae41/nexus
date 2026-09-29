"""회원 서비스 권한 — user / admin."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Member

ACCESS_ROLES = ("user", "admin")


def promote_configured_admin(db: Session, member: Member) -> Member:
    """설정된 닉네임이면 어드민으로 승격한다. 권한 화면을 열 최초 계정용."""
    if member.nickname not in get_settings().admin_nickname_set:
        return member
    if member.access_role == "admin":
        return member
    member.access_role = "admin"
    db.commit()
    db.refresh(member)
    return member


def list_members(db: Session) -> list[Member]:
    return list(db.scalars(select(Member).order_by(Member.nickname).limit(500)))


def set_access_role(db: Session, *, actor_id: int, member_id: int, access_role: str) -> Member:
    _validate_role(access_role)
    target = db.get(Member, member_id)
    if target is None:
        raise LookupError("회원을 찾을 수 없습니다")
    _guard_demotion(db, actor_id, target, access_role)
    target.access_role = access_role
    db.commit()
    db.refresh(target)
    return target


def _validate_role(access_role: str) -> None:
    if access_role not in ACCESS_ROLES:
        raise ValueError("권한은 사용자 또는 어드민만 선택할 수 있습니다")


def _guard_demotion(db: Session, actor_id: int, target: Member, access_role: str) -> None:
    if access_role == "admin" or target.access_role != "admin":
        return
    if target.id == actor_id:
        raise ValueError("자신의 어드민 권한은 내릴 수 없습니다")
    if _admin_count(db) <= 1:
        raise ValueError("마지막 어드민 권한은 내릴 수 없습니다")


def _admin_count(db: Session) -> int:
    total = db.scalar(select(func.count()).select_from(Member).where(Member.access_role == "admin"))
    return total or 0
