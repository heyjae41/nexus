"""회원가입·로그인·현재 세션 API."""
from typing import Annotated, Literal, NoReturn

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.routes import get_cache
from app.cache import VersionedCache
from app.db import get_db
from app.models import Member
from app.repositories.auth import (
    SESSION_DAYS,
    create_session,
    delete_session,
    get_session_member,
)
from app.repositories.members import (
    AuthError,
    authenticate_member,
    create_member,
    delete_member,
    nickname_available,
    update_member,
)
from app.serializers import api_response, serialize_member

router = APIRouter(prefix="/api/auth")
COOKIE_NAME = "nexus_session"
Role = Literal["기획자", "개발자"]
Interest = Literal[
    "서비스기획", "PM/PO", "사업전략", "데이터분석", "UX", "마케팅/그로스",
    "서비스운영", "프론트엔드", "백엔드", "AI/ML", "모바일", "인프라",
    "DevOps", "QA", "보안",
]


class Credentials(BaseModel):
    nickname: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


class RegisterIn(Credentials):
    role: Role
    interests: list[Interest] = Field(min_length=1)


class ProfilePatch(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    role: Role | None = None
    interests: list[Interest] | None = Field(default=None, min_length=1)


def _set_session_cookie(response: Response, request: Request, token: str) -> None:
    # TLS 종단이 nginx 등 앞단에 있으면 앱에는 http 로 보이므로 X-Forwarded-Proto 를 우선한다
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=scheme == "https",
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax")


def _session_response(db: Session, response: Response, request: Request, member: Member):
    """세션 발급 → 쿠키 세팅 → 회원 응답 (가입/로그인 공통 꼬리)."""
    token = create_session(db, member.id)
    _set_session_cookie(response, request, token)
    return api_response(serialize_member(member))


def _raise_member_value_error(exc: ValueError) -> NoReturn:
    """중복 닉네임은 409, 그 외 검증 위반은 400 으로 매핑한다."""
    status = 409 if "사용 중" in str(exc) else 400
    raise HTTPException(status_code=status, detail=str(exc)) from exc


def require_member(
    nexus_session: Annotated[str | None, Cookie()] = None,
    db: Session = Depends(get_db),
) -> Member:
    member = get_session_member(db, nexus_session)
    if member is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    return member


@router.get("/nickname-available")
def nickname_check(
    nickname: str = Query(min_length=1, max_length=50),
    db: Session = Depends(get_db),
):
    try:
        normalized, available = nickname_available(db, nickname)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return api_response({"nickname": normalized, "available": available})


@router.post("/register", status_code=201)
def register(
    payload: RegisterIn,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        member = create_member(
            db,
            nickname=payload.nickname,
            password=payload.password,
            role=payload.role,
            interests=", ".join(payload.interests),
        )
    except ValueError as exc:
        _raise_member_value_error(exc)
    return _session_response(db, response, request, member)


@router.post("/login")
def login(
    payload: Credentials,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    try:
        member = authenticate_member(
            db, nickname=payload.nickname, password=payload.password
        )
    except (AuthError, ValueError) as exc:
        raise HTTPException(
            status_code=401, detail="닉네임 또는 비밀번호가 올바르지 않습니다"
        ) from exc
    return _session_response(db, response, request, member)


@router.get("/me")
def me(member: Member = Depends(require_member)):
    return api_response(serialize_member(member))


@router.patch("/me")
def profile_update(
    payload: ProfilePatch,
    member: Member = Depends(require_member),
    db: Session = Depends(get_db),
):
    try:
        updated = update_member(
            db,
            member.id,
            nickname=payload.nickname,
            role=payload.role,
            interests=None if payload.interests is None else ", ".join(payload.interests),
        )
    except ValueError as exc:
        _raise_member_value_error(exc)
    return api_response(serialize_member(updated))


@router.post("/logout")
def logout(
    response: Response,
    nexus_session: Annotated[str | None, Cookie()] = None,
    db: Session = Depends(get_db),
):
    delete_session(db, nexus_session)
    _clear_session_cookie(response)
    return api_response({"loggedOut": True})


@router.delete("/me")
def withdraw(
    response: Response,
    member: Member = Depends(require_member),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    delete_member(db, member.id)
    cache.bump_version()
    _clear_session_cookie(response)
    return api_response({"deleted": True})
