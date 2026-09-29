"""어드민 글쓰기·권한관리."""
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.auth import require_member
from app.api.routes import get_cache
from app.cache import VersionedCache
from app.db import get_db
from app.models import Member
from app.repositories.access import list_members, set_access_role
from app.serializers import (
    api_response,
    serialize_access_member,
    serialize_article_detail,
)
from app.services.authored import publish_authored_article
from app.services.image_store import save_article_image

router = APIRouter(prefix="/api/admin")


def require_admin(member: Member = Depends(require_member)) -> Member:
    if member.access_role != "admin":
        raise HTTPException(status_code=403, detail="어드민 권한이 필요합니다")
    return member


class ArticleIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    article_type: Literal["newsletter", "column", "guide"] = Field(alias="articleType")
    title: str = Field(min_length=1, max_length=300)
    summary: str | None = Field(default=None, max_length=500)
    body_html: str = Field(alias="bodyHtml", max_length=200_000)


class AccessIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_role: Literal["user", "admin"] = Field(alias="accessRole")


def _value_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.post("/articles", status_code=201)
def create_authored_article(
    payload: ArticleIn,
    member: Member = Depends(require_admin),
    db: Session = Depends(get_db),
    cache: VersionedCache = Depends(get_cache),
):
    try:
        article = publish_authored_article(
            db, cache, member,
            article_type=payload.article_type,
            title=payload.title,
            summary=payload.summary,
            body_html=payload.body_html,
        )
    except ValueError as exc:
        raise _value_error(exc) from exc
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


@router.get("/members")
def admin_members(
    _member: Member = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return api_response([serialize_access_member(item) for item in list_members(db)])


@router.patch("/members/{member_id}")
def update_member_access(
    member_id: int,
    payload: AccessIn,
    member: Member = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        updated = set_access_role(
            db, actor_id=member.id, member_id=member_id, access_role=payload.access_role,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise _value_error(exc) from exc
    return api_response(serialize_access_member(updated))
