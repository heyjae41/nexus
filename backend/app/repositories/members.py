"""회원 리포지토리 — 닉네임 기반 경량 회원 (비밀번호 없음, 프로토타입 정책).

- 같은 닉네임으로 재온보딩하면 기존 회원을 반환한다 (= 로그인).
- 이메일은 최초 1회만 등록 가능하며 이후 수정할 수 없다.
- 탈회 시 글/댓글은 작성자명만 남기고 연결을 해제하고, 좋아요는 회수한다.
"""
import re

from sqlalchemy import case
from sqlalchemy import delete as sql_delete
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    CommunityComment,
    CommunityPost,
    CommunityPostLike,
    Member,
)

NICKNAME_MAX = 50
EMAIL_MAX = 200


def _validate_nickname(nickname: str) -> str:
    name = (nickname or "").strip()
    if not name:
        raise ValueError("닉네임을 입력해 주세요")
    if len(name) > NICKNAME_MAX:
        raise ValueError(f"닉네임은 {NICKNAME_MAX}자 이내여야 합니다")
    return name


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(email: str) -> str:
    value = (email or "").strip()
    if not value or len(value) > EMAIL_MAX or not EMAIL_RE.fullmatch(value):
        raise ValueError("올바른 이메일 형식이 아닙니다")
    return value


def _commit_member(db: Session, member) -> None:
    """커밋 시 UNIQUE 위반(이메일 중복)을 명확한 오류로 변환한다."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("이미 사용 중인 이메일입니다") from exc
    db.refresh(member)


def _nickname_taken(db: Session, name: str, exclude_id: int | None = None) -> bool:
    stmt = select(Member.id).where(Member.nickname == name)
    if exclude_id is not None:
        stmt = stmt.where(Member.id != exclude_id)
    return db.scalars(stmt).first() is not None


def register_member(
    db: Session,
    *,
    nickname: str,
    email: str | None = None,
    role: str | None = None,
    interests: str | None = None,
) -> Member:
    name = _validate_nickname(nickname)
    member = db.scalars(select(Member).where(Member.nickname == name)).first()
    if member is None:
        member = Member(nickname=name)
        db.add(member)
    # 재온보딩 시 프로필은 최신 값으로 갱신 (이메일은 최초 1회만, 다른 값은 거부)
    if email:
        cleaned = _validate_email(email)
        if member.email is None:
            member.email = cleaned
        elif member.email != cleaned:
            raise ValueError("이메일은 수정할 수 없습니다")
    if role is not None:
        member.role = role
    if interests is not None:
        member.interests = interests
    _commit_member(db, member)
    return member


def get_member(db: Session, member_id: int) -> Member | None:
    return db.get(Member, member_id)


def update_member(
    db: Session,
    member_id: int,
    *,
    nickname: str | None = None,
    email: str | None = None,
    role: str | None = None,
    interests: str | None = None,
) -> Member:
    member = db.get(Member, member_id)
    if member is None:
        raise LookupError("회원 정보를 찾을 수 없습니다")
    if nickname is not None:
        name = _validate_nickname(nickname)
        if _nickname_taken(db, name, exclude_id=member_id):
            raise ValueError("이미 사용 중인 닉네임입니다")
        member.nickname = name
    if email is not None:
        cleaned = email.strip()
        if member.email is not None and member.email != cleaned:
            raise ValueError("이메일은 수정할 수 없습니다")
        if member.email is None:
            member.email = _validate_email(cleaned)  # 최초 1회 등록만 허용
    if role is not None:
        member.role = role
    if interests is not None:
        member.interests = interests
    _commit_member(db, member)
    return member


def delete_member(db: Session, member_id: int) -> None:
    """탈회 — 콘텐츠는 보존(작성자명 유지·연결 해제), 좋아요는 회수한다."""
    member = db.get(Member, member_id)
    if member is None:
        raise LookupError("회원 정보를 찾을 수 없습니다")

    # 좋아요 회수: 카운트 감소 후 좋아요 행 삭제
    liked_post_ids = list(
        db.scalars(
            select(CommunityPostLike.post_id).where(
                CommunityPostLike.member_id == member_id
            )
        )
    )
    if liked_post_ids:
        db.execute(
            update(CommunityPost)
            .where(CommunityPost.id.in_(liked_post_ids))
            .values(
                likes_count=case(
                    (CommunityPost.likes_count > 0, CommunityPost.likes_count - 1),
                    else_=0,
                )
            )
        )
        db.execute(
            sql_delete(CommunityPostLike).where(
                CommunityPostLike.member_id == member_id
            )
        )

    # 글/댓글은 작성자명만 남기고 연결 해제
    db.execute(
        update(CommunityPost)
        .where(CommunityPost.member_id == member_id)
        .values(member_id=None)
    )
    db.execute(
        update(CommunityComment)
        .where(CommunityComment.member_id == member_id)
        .values(member_id=None)
    )

    db.delete(member)
    db.commit()
