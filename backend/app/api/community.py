"""커뮤니티/회원 API 라우터."""
from typing import Literal, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import _set_session_cookie, require_member
from app.api.common import PageQuery, cached_page_response, page_query
from app.api.routes import get_cache
from app.cache import VersionedCache
from app.db import get_db
from app.models import Member
from app.repositories.auth import create_session
from app.repositories.community import (
    NotFoundError,
    add_comment,
    create_post,
    delete_post,
    get_post_with_comments,
    list_posts,
    toggle_post_like,
)
from app.repositories.members import AuthError, get_member, register_member, verify_password
from app.serializers import (
    api_response,
    serialize_comment,
    serialize_member,
    serialize_post_card,
    serialize_post_detail,
)

router = APIRouter(prefix="/api")
CommunityTag = Literal["자료", "노하우", "팁", "기술자료"]


class MemberIn(BaseModel):
    nickname: str = Field(min_length=1, max_length=50)  # DB 컬럼(String(50))과 일치
    password: str = Field(min_length=1, max_length=200)  # 정책 검증은 리포지토리에서
    role: str | None = Field(default=None, max_length=20)
    interests: str | None = Field(default=None, max_length=300)


class MemberPatch(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    role: str | None = Field(default=None, max_length=20)
    interests: str | None = Field(default=None, max_length=300)


class PostIn(BaseModel):
    memberId: int
    tag: str = Field(max_length=20)
    title: str = Field(max_length=300)
    body: str = Field(max_length=10_000)


class CommentIn(BaseModel):
    memberId: int
    body: str = Field(max_length=10_000)


class LikeIn(BaseModel):
    memberId: int


class DeletePostIn(BaseModel):
    memberId: int
    password: str = Field(min_length=1, max_length=200)


def _raise_http(exc: Exception) -> "NoReturn":
    if isinstance(exc, NotFoundError):
        # 대상 리소스(글) 없음 — 표준 404 시맨틱
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, LookupError):
        # 온보딩 미완료 — 인증 실패(401)가 아니라 접근 거부(403) 시맨틱
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


def _require_same_member(member_id: int, current: Member) -> None:
    if member_id != current.id:
        raise HTTPException(status_code=403, detail="다른 회원의 정보에는 접근할 수 없습니다")


def _member_write(current: Member, member_id: int, cache: VersionedCache, action):
    """본인 확인 → 쓰기 실행 → 캐시 bump — 'DB 반영사항 즉시 조회' 불변식을 한 곳에서 보장한다."""
    _require_same_member(member_id, current)
    try:
        result = action()
    except (LookupError, ValueError) as exc:
        _raise_http(exc)
    cache.bump_version()
    return result


@router.post("/members")
def member_register(
    payload: MemberIn,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
):
    """레거시 가입/로그인 호환 경로 — 성공 시에도 서버 세션을 발급한다.

    회원 생성은 cache.bump_version() 면제 — 작성자명이 글/댓글에 쓰기 시점에
    비정규화 저장되고 회원 엔티티 자체는 캐시되지 않아 stale 조회가 없다.
    """
    try:
        member = register_member(
            db, nickname=payload.nickname, password=payload.password,
            role=payload.role, interests=payload.interests,
        )
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    token = create_session(db, member.id)
    _set_session_cookie(response, request, token)
    return api_response(serialize_member(member))


@router.get("/members/{member_id}")
def member_profile(
    member_id: int,
    current: Member = Depends(require_member),
    db: Session = Depends(get_db),
):
    _require_same_member(member_id, current)
    member = get_member(db, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="회원 정보를 찾을 수 없습니다")
    return api_response(serialize_member(member))


@router.patch("/members/{member_id}")
def member_update(
    member_id: int,
    payload: MemberPatch,
    current: Member = Depends(require_member),
    db: Session = Depends(get_db),
):
    from app.repositories.members import update_member

    _require_same_member(member_id, current)

    try:
        member = update_member(
            db, member_id, nickname=payload.nickname,
            role=payload.role, interests=payload.interests,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return api_response(serialize_member(member))


@router.delete("/members/{member_id}")
def member_delete(
    member_id: int,
    current: Member = Depends(require_member),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    from app.repositories.members import delete_member

    _require_same_member(member_id, current)

    try:
        delete_member(db, member_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    cache.bump_version()  # 좋아요 회수가 목록 카드에 반영되도록
    return api_response({"deleted": True})


@router.get("/community/posts")
def community_posts(
    tag: CommunityTag | None = Query(default=None),
    paging: PageQuery = page_query(),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    key = f"community:list:{tag}:{paging.page}:{paging.size}"
    return cached_page_response(
        cache, key,
        lambda: list_posts(db, tag=tag, page=paging.page, size=paging.size),
        serialize_post_card,
    )


@router.post("/community/posts")
def community_post_create(
    payload: PostIn,
    current: Member = Depends(require_member),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    post = _member_write(current, payload.memberId, cache, lambda: create_post(
        db, member_id=payload.memberId, tag=payload.tag,
        title=payload.title, body=payload.body,
    ))
    return api_response(serialize_post_card(post))


@router.get("/community/posts/{post_id}")
def community_post_detail(post_id: int, db: Session = Depends(get_db)):
    post, comments = get_post_with_comments(db, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다")
    return api_response(serialize_post_detail(post, comments))


@router.delete("/community/posts/{post_id}")
def community_post_delete(
    post_id: int,
    payload: DeletePostIn,
    current: Member = Depends(require_member),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    """비밀번호로 인증한 본인 글만 삭제하고 목록 캐시를 무효화한다."""
    _require_same_member(payload.memberId, current)
    member = get_member(db, payload.memberId)
    if member is None or not verify_password(payload.password, member.password_hash or ""):
        raise HTTPException(status_code=401, detail="닉네임 또는 비밀번호가 올바르지 않습니다")
    try:
        delete_post(db, post_id=post_id, member_id=payload.memberId)
    except (LookupError, ValueError) as exc:
        _raise_http(exc)
    cache.bump_version()
    return api_response({"id": post_id, "deleted": True})


@router.post("/community/posts/{post_id}/comments")
def community_comment_create(
    post_id: int,
    payload: CommentIn,
    current: Member = Depends(require_member),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    comment = _member_write(current, payload.memberId, cache, lambda: add_comment(
        db, post_id=post_id, member_id=payload.memberId, body=payload.body,
    ))
    return api_response(serialize_comment(comment))


@router.post("/community/posts/{post_id}/like")
def community_post_like(
    post_id: int,
    payload: LikeIn,
    current: Member = Depends(require_member),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    likes, liked = _member_write(current, payload.memberId, cache, lambda: toggle_post_like(
        db, post_id=post_id, member_id=payload.memberId,
    ))
    return api_response({"id": post_id, "likesCount": likes, "liked": liked})
