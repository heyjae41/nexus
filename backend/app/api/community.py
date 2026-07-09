"""커뮤니티/회원 API 라우터."""
from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.routes import get_cache
from app.cache import VersionedCache
from app.db import get_db
from app.repositories.community import (
    add_comment,
    create_post,
    get_post_with_comments,
    list_posts,
    toggle_post_like,
)
from app.repositories.members import register_member
from app.serializers import (
    api_response,
    serialize_comment,
    serialize_member,
    serialize_post_card,
    serialize_post_detail,
)

router = APIRouter(prefix="/api")


class MemberIn(BaseModel):
    nickname: str = Field(min_length=1, max_length=50)  # DB 컬럼(String(50))과 일치
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


def _raise_http(exc: Exception) -> "NoReturn":
    if isinstance(exc, LookupError):
        # 온보딩 미완료/대상 없음 — 인증 실패(401)가 아니라 접근 거부(403) 시맨틱
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/members")
def member_register(payload: MemberIn, db: Session = Depends(get_db)):
    try:
        member = register_member(
            db, nickname=payload.nickname, role=payload.role, interests=payload.interests
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return api_response(serialize_member(member))


@router.get("/community/posts")
def community_posts(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    key = f"community:list:{page}:{size}"

    def load():
        result = list_posts(db, page=page, size=size)
        return {
            "items": [serialize_post_card(p) for p in result.items],
            "meta": {"total": result.total, "page": result.page, "limit": result.size},
        }

    loaded = cache.get_or_set(key, load)
    return api_response(loaded["items"], meta=loaded["meta"])


@router.post("/community/posts")
def community_post_create(
    payload: PostIn,
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    try:
        post = create_post(
            db, member_id=payload.memberId, tag=payload.tag,
            title=payload.title, body=payload.body,
        )
    except (LookupError, ValueError) as exc:
        _raise_http(exc)
    cache.bump_version()  # 신규 글은 목록/홈에 즉시 반영
    return api_response(serialize_post_card(post))


@router.get("/community/posts/{post_id}")
def community_post_detail(post_id: int, db: Session = Depends(get_db)):
    post, comments = get_post_with_comments(db, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="글을 찾을 수 없습니다")
    return api_response(serialize_post_detail(post, comments))


@router.post("/community/posts/{post_id}/comments")
def community_comment_create(
    post_id: int,
    payload: CommentIn,
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    try:
        comment = add_comment(db, post_id=post_id, member_id=payload.memberId, body=payload.body)
    except (LookupError, ValueError) as exc:
        _raise_http(exc)
    cache.bump_version()  # 댓글 수가 목록 카드에 노출되므로 즉시 반영
    return api_response(serialize_comment(comment))


@router.post("/community/posts/{post_id}/like")
def community_post_like(
    post_id: int,
    payload: LikeIn,
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    try:
        likes, liked = toggle_post_like(db, post_id=post_id, member_id=payload.memberId)
    except (LookupError, ValueError) as exc:
        _raise_http(exc)
    cache.bump_version()
    return api_response({"id": post_id, "likesCount": likes, "liked": liked})
