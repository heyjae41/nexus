"""회원 리포지토리 — 닉네임 + 비밀번호 기반 회원.

- 신규 닉네임 → 회원 생성 (비밀번호 정책 검증 + PBKDF2 해시 저장).
- 기존 닉네임 → 비밀번호 검증 후 로그인 (불일치 시 AuthError).
- 비밀번호 정책: 영문·숫자를 각 1자 이상 포함한 8자 이상 (특수문자·대소문자 조합은 선택).
- 탈회 시 글/댓글은 작성자명만 남기고 연결을 해제하고, 좋아요는 회수한다.
"""
import hashlib
import hmac
import re
import secrets

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
PASSWORD_MIN = 8
PBKDF2_ITERATIONS = 240_000


class AuthError(Exception):
    """로그인 실패(비밀번호 불일치) — API 에서 401 로 매핑된다."""


def _validate_nickname(nickname: str) -> str:
    name = (nickname or "").strip()
    if not name:
        raise ValueError("닉네임을 입력해 주세요")
    if len(name) > NICKNAME_MAX:
        raise ValueError(f"닉네임은 {NICKNAME_MAX}자 이내여야 합니다")
    return name


def _validate_password(password: str) -> str:
    """정책: 영문·숫자 포함 8자 이상 — 부족 항목을 메시지에 담는다."""
    value = password or ""
    missing = []
    if len(value) < PASSWORD_MIN:
        missing.append(f"{PASSWORD_MIN}자 이상")
    if not re.search(r"[A-Za-z]", value):
        missing.append("영문")
    if not re.search(r"\d", value):
        missing.append("숫자")
    if missing:
        raise ValueError(
            "비밀번호는 영문과 숫자를 포함한 8자 이상이어야 합니다"
            f" (부족: {', '.join(missing)})"
        )
    return value


def hash_password(password: str) -> str:
    """PBKDF2-SHA256 해시 — 표준 라이브러리만 사용 (평문 저장 금지)."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        calc = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
        ).hex()
        return hmac.compare_digest(calc, digest)
    except (ValueError, AttributeError):
        return False  # 형식 불명/미설정(NULL) 해시는 인증 실패로 처리


def _commit_member(db: Session, member) -> None:
    """커밋 시 UNIQUE 위반(닉네임 중복 레이스)을 명확한 오류로 변환한다."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("이미 사용 중인 닉네임입니다") from exc
    db.refresh(member)


def _nickname_taken(db: Session, name: str, exclude_id: int | None = None) -> bool:
    stmt = select(Member.id).where(Member.nickname == name)
    if exclude_id is not None:
        stmt = stmt.where(Member.id != exclude_id)
    return db.scalars(stmt).first() is not None


def nickname_available(db: Session, nickname: str) -> tuple[str, bool]:
    name = _validate_nickname(nickname)
    return name, not _nickname_taken(db, name)


def create_member(
    db: Session,
    *,
    nickname: str,
    password: str,
    role: str,
    interests: str,
) -> Member:
    name = _validate_nickname(nickname)
    if _nickname_taken(db, name):
        raise ValueError("이미 사용 중인 닉네임입니다")
    member = Member(
        nickname=name,
        password_hash=hash_password(_validate_password(password)),
        role=role,
        interests=interests,
    )
    db.add(member)
    _commit_member(db, member)
    return member


def authenticate_member(db: Session, *, nickname: str, password: str) -> Member:
    name = _validate_nickname(nickname)
    member = db.scalars(select(Member).where(Member.nickname == name)).first()
    if member is None or not verify_password(password or "", member.password_hash or ""):
        raise AuthError("닉네임 또는 비밀번호가 올바르지 않습니다")
    return member


def register_member(
    db: Session,
    *,
    nickname: str,
    password: str,
    role: str | None = None,
    interests: str | None = None,
) -> Member:
    """신규 닉네임은 가입, 기존 닉네임은 비밀번호 검증 후 로그인."""
    name = _validate_nickname(nickname)
    member = db.scalars(select(Member).where(Member.nickname == name)).first()
    if member is None:
        member = Member(
            nickname=name, password_hash=hash_password(_validate_password(password))
        )
        db.add(member)
    elif not verify_password(password or "", member.password_hash or ""):
        # 로그인은 정책 재검증 없이 일치 여부만 본다 (정책 강화 이전 가입자 호환)
        raise AuthError("닉네임 또는 비밀번호가 올바르지 않습니다")
    # 가입/로그인 시 프로필은 최신 값으로 갱신
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

    from app.repositories.auth import delete_member_sessions

    delete_member_sessions(db, member_id)

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
