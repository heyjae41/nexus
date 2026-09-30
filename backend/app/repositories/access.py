"""회원 서비스 권한 — user / admin. 수퍼어드민은 환경변수다."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Member

ACCESS_ROLES = ("user", "admin")


def is_super_admin(member: Member) -> bool:
    return member.nickname in get_settings().super_admin_set


def list_members(db: Session) -> list[Member]:
    return list(db.scalars(select(Member).order_by(Member.nickname).limit(500)))


def set_access_role(db: Session, *, member_id: int, access_role: str) -> Member:
    _validate_role(access_role)
    target = db.get(Member, member_id)
    if target is None:
        raise LookupError("회원을 찾을 수 없습니다")
    target.access_role = access_role
    db.commit()
    db.refresh(target)
    return target


def _validate_role(access_role: str) -> None:
    if access_role not in ACCESS_ROLES:
        raise ValueError("권한은 사용자 또는 어드민만 선택할 수 있습니다")
