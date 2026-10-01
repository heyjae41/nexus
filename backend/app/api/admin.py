"""어드민 글쓰기·권한관리."""
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.auth import require_member
from app.api.routes import get_cache
from app.cache import VersionedCache
from app.db import get_db
from app.models import Member
from app.repositories.access import is_super_admin, list_members, set_access_role
from app.serializers import (
    api_response,
    serialize_access_member,
    serialize_article_detail,
)
from app.repositories.articles import get_article
from app.services.authored import (
    assert_can_edit_authored,
    publish_authored_article,
    update_authored_article,
)
from app.services.image_chunks import accept_body_chunk, accept_image_chunk
from app.services.image_store import save_article_image

router = APIRouter(prefix="/api/admin")


def require_admin(member: Member = Depends(require_member)) -> Member:
    if member.access_role != "admin":
        raise HTTPException(status_code=403, detail="어드민 권한이 필요합니다")
    return member


def require_super_admin(member: Member = Depends(require_member)) -> Member:
    if not is_super_admin(member):
        raise HTTPException(status_code=403, detail="수퍼어드민만 권한을 바꿀 수 있습니다")
    return member


MAX_BODY_CHARS = 200_000


class ArticleMetaIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    article_type: Literal["newsletter", "column", "guide"] = Field(alias="articleType")
    title: str = Field(min_length=1, max_length=300)
    summary: str | None = Field(default=None, max_length=500)


class ArticleIn(ArticleMetaIn):
    body_html: str = Field(alias="bodyHtml", max_length=MAX_BODY_CHARS)


class PartIn(BaseModel):
    """8KB 미만 조각 1건 — 앞단(WAF)이 8192바이트 넘는 요청 본문을 403 으로 거절한다."""

    model_config = ConfigDict(populate_by_name=True)

    upload_id: str = Field(alias="uploadId", min_length=16, max_length=64, pattern=r"^[A-Za-z0-9]+$")
    index: int = Field(ge=0, le=1100)
    total: int = Field(ge=1, le=1100)
    data: str = Field(min_length=4, max_length=7800)


class AccessIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_role: Literal["user", "admin"] = Field(alias="accessRole")


class ImagePartIn(PartIn):
    content_type: str = Field(alias="contentType", max_length=100)


class ArticlePartIn(PartIn, ArticleMetaIn):
    """글 메타 + 본문 조각. 마지막 조각이 도착하면 그 요청이 곧 저장이다."""

    article_id: int | None = Field(default=None, alias="articleId")


def _value_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _http_error(exc: Exception) -> HTTPException:
    """도메인 예외 → HTTP 상태 (404 없음 / 403 권한 / 400 검증)."""
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=403, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


def _authorize_save(db: Session, member: Member, article_id: int | None) -> None:
    """생성은 어드민, 수정은 직접 작성한 글의 작성자만 — 조각을 받기 전에 먼저 거른다."""
    if article_id is None:
        if member.access_role != "admin":
            raise PermissionError("어드민 권한이 필요합니다")
        return
    assert_can_edit_authored(get_article(db, article_id), member)


def _save_article(
    db: Session, cache: VersionedCache, member: Member,
    meta: ArticleMetaIn, body_html: str, article_id: int | None,
):
    """생성(어드민)·수정(작성자) 공통 경로."""
    fields = {
        "article_type": meta.article_type, "title": meta.title,
        "summary": meta.summary, "body_html": body_html,
    }
    try:
        _authorize_save(db, member, article_id)
        if article_id is None:
            return publish_authored_article(db, cache, member, **fields)
        return update_authored_article(db, cache, member, article_id, **fields)
    except (LookupError, PermissionError, ValueError) as exc:
        raise _http_error(exc) from exc


@router.post("/articles", status_code=201)
def create_authored_article(
    payload: ArticleIn,
    member: Member = Depends(require_admin),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    article = _save_article(db, cache, member, payload, payload.body_html, None)
    return api_response(serialize_article_detail(article))


@router.post("/articles/parts")
def save_article_from_parts(
    payload: ArticlePartIn,
    request: Request,
    response: Response,
    member: Member = Depends(require_member),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    """긴 본문은 8KB 미만 조각으로 받는다. 마지막 조각이 모이면 생성(201)·수정(200)한다.

    권한은 첫 조각부터 검사한다 — 권한 없는 회원이 조각으로 Redis 를 채우지 못하게."""
    try:
        _authorize_save(db, member, payload.article_id)
        body_html = accept_body_chunk(
            request.app.state.image_chunks, member.id, payload.upload_id,
            payload.index, payload.total, payload.data,
        )
    except (LookupError, PermissionError, ValueError) as exc:
        raise _http_error(exc) from exc
    if body_html is None:
        return api_response({"received": payload.index})
    if len(body_html) > MAX_BODY_CHARS:
        raise HTTPException(status_code=400, detail="본문이 너무 깁니다")
    article = _save_article(db, cache, member, payload, body_html, payload.article_id)
    if payload.article_id is None:
        response.status_code = 201
    return api_response(serialize_article_detail(article))


@router.patch("/articles/{article_id}")
def patch_authored_article(
    article_id: int,
    payload: ArticleIn,
    member: Member = Depends(require_member),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    article = _save_article(db, cache, member, payload, payload.body_html, article_id)
    return api_response(serialize_article_detail(article))


@router.post("/media")
async def upload_media(
    file: UploadFile = File(...),
    _member: Member = Depends(require_admin),
):
    data = await file.read()
    try:
        url = save_article_image(data, file.content_type)
    except ValueError as exc:
        raise _value_error(exc) from exc
    return api_response({"url": url})


@router.post("/media/parts")
def upload_media_part(
    payload: ImagePartIn,
    request: Request,
    member: Member = Depends(require_admin),
):
    try:
        blob = accept_image_chunk(
            request.app.state.image_chunks, member.id, payload.upload_id,
            payload.index, payload.total, payload.content_type, payload.data,
        )
        url = save_article_image(blob, payload.content_type) if blob is not None else None
    except ValueError as exc:
        raise _value_error(exc) from exc
    if url is None:
        return api_response({"received": payload.index})
    return api_response({"url": url})


@router.get("/members")
def admin_members(
    _member: Member = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    return api_response([serialize_access_member(item) for item in list_members(db)])


@router.patch("/members/{member_id}")
def update_member_access(
    member_id: int,
    payload: AccessIn,
    _member: Member = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    try:
        updated = set_access_role(
            db, member_id=member_id, access_role=payload.access_role,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise _value_error(exc) from exc
    return api_response(serialize_access_member(updated))
