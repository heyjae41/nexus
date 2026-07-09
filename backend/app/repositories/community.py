"""커뮤니티 글/댓글 리포지토리."""
from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import CommunityComment, CommunityPost, CommunityPostLike
from app.repositories.members import get_member

ALLOWED_TAGS = ("노하우", "기술자료", "팁", "자료", "질문")
TITLE_MAX = 300
BODY_MAX = 10_000
COMMENTS_LIMIT = 100


@dataclass(frozen=True)
class PostPage:
    items: list[CommunityPost]
    total: int
    page: int
    size: int


def _require_member(db: Session, member_id: int):
    member = get_member(db, member_id)
    if member is None:
        raise LookupError("회원 정보를 찾을 수 없습니다 — 온보딩(회원가입) 후 이용해 주세요")
    return member


def _validate_post_fields(tag: str, title: str, body: str) -> tuple[str, str]:
    title, body = title.strip(), body.strip()
    if tag not in ALLOWED_TAGS:
        allowed = ", ".join(ALLOWED_TAGS)
        raise ValueError(f"태그는 [{allowed}] 중 하나여야 합니다")
    if not title or len(title) > TITLE_MAX:
        raise ValueError(f"제목은 1~{TITLE_MAX}자여야 합니다")
    if not body or len(body) > BODY_MAX:
        raise ValueError(f"본문은 1~{BODY_MAX:,}자여야 합니다")
    return title, body


def create_post(
    db: Session, *, member_id: int, tag: str, title: str, body: str
) -> CommunityPost:
    member = _require_member(db, member_id)
    title, body = _validate_post_fields(tag, title, body)
    post = CommunityPost(
        member_id=member.id,
        author_name=member.nickname,
        tag=tag,
        title=title,
        body=body,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def list_posts(db: Session, page: int = 1, size: int = 20) -> PostPage:
    base = select(CommunityPost).where(CommunityPost.status == "published")
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = list(
        db.scalars(
            base.order_by(CommunityPost.created_at.desc(), CommunityPost.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    )
    return PostPage(items=items, total=total, page=page, size=size)


def get_post_with_comments(
    db: Session, post_id: int
) -> tuple[CommunityPost | None, list[CommunityComment]]:
    post = db.get(CommunityPost, post_id)
    if post is None or post.status != "published":
        return None, []
    comments = list(
        db.scalars(
            select(CommunityComment)
            .where(CommunityComment.post_id == post_id)
            .order_by(CommunityComment.created_at.asc(), CommunityComment.id.asc())
            .limit(COMMENTS_LIMIT)
        )
    )
    return post, comments


def add_comment(
    db: Session, *, post_id: int, member_id: int, body: str
) -> CommunityComment:
    member = _require_member(db, member_id)
    post = db.get(CommunityPost, post_id)
    if post is None or post.status != "published":
        raise LookupError("글을 찾을 수 없습니다")
    body = body.strip()
    if not body or len(body) > BODY_MAX:
        raise ValueError(f"댓글은 1~{BODY_MAX:,}자여야 합니다")
    comment = CommunityComment(
        post_id=post_id, member_id=member.id, author_name=member.nickname, body=body
    )
    db.add(comment)
    db.execute(
        update(CommunityPost)
        .where(CommunityPost.id == post_id)
        .values(comments_count=CommunityPost.comments_count + 1)
    )
    db.commit()
    db.refresh(comment)
    return comment


def toggle_post_like(db: Session, *, post_id: int, member_id: int) -> tuple[int, bool]:
    """회원 기반 좋아요 토글 — (총 좋아요 수, 현재 좋아요 여부) 를 반환한다."""
    _require_member(db, member_id)
    post = db.get(CommunityPost, post_id)
    if post is None or post.status != "published":
        raise LookupError("글을 찾을 수 없습니다")

    existing = db.get(CommunityPostLike, (post_id, member_id))
    delta, liked = (-1, False) if existing else (1, True)
    if existing:
        db.delete(existing)
    else:
        db.add(CommunityPostLike(post_id=post_id, member_id=member_id))
    db.execute(
        update(CommunityPost)
        .where(CommunityPost.id == post_id)
        .values(likes_count=CommunityPost.likes_count + delta)
    )
    db.commit()
    db.refresh(post)
    return post.likes_count, liked
