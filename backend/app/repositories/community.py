"""커뮤니티 글/댓글 리포지토리."""
from dataclasses import dataclass

from sqlalchemy import delete as sql_delete
from sqlalchemy import case, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import is_unique_violation
from app.models import CommunityComment, CommunityPost, CommunityPostLike
from app.repositories.members import get_member

class NotFoundError(LookupError):
    """대상 리소스 없음 — 온보딩 미완료(LookupError→403)와 달리 404 로 매핑된다."""


ALLOWED_TAGS = ("자료", "노하우", "팁", "기술자료")
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


def list_posts(
    db: Session, tag: str | None = None, page: int = 1, size: int = 20
) -> PostPage:
    conditions = [
        CommunityPost.status == "published",
        CommunityPost.tag.in_(ALLOWED_TAGS),
    ]
    if tag is not None:
        conditions.append(CommunityPost.tag == tag)
    base = select(CommunityPost).where(*conditions)
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
        raise NotFoundError("글을 찾을 수 없습니다")
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


def delete_post(db: Session, *, post_id: int, member_id: int) -> None:
    """본인이 작성한 글 삭제 — 댓글/좋아요를 함께 제거한다."""
    _require_member(db, member_id)
    post = db.get(CommunityPost, post_id)
    if post is None:
        raise NotFoundError("글을 찾을 수 없습니다")
    if post.member_id != member_id:
        raise ValueError("본인이 작성한 글만 삭제할 수 있습니다")
    db.execute(sql_delete(CommunityPostLike).where(CommunityPostLike.post_id == post_id))
    db.execute(sql_delete(CommunityComment).where(CommunityComment.post_id == post_id))
    db.delete(post)
    db.commit()


def toggle_post_like(db: Session, *, post_id: int, member_id: int) -> tuple[int, bool]:
    """회원 기반 좋아요 토글 — (총 좋아요 수, 현재 좋아요 여부) 를 반환한다."""
    _require_member(db, member_id)
    post = db.get(CommunityPost, post_id)
    if post is None or post.status != "published":
        raise NotFoundError("글을 찾을 수 없습니다")

    existing = db.get(CommunityPostLike, (post_id, member_id))
    if existing:
        # 실제 좋아요 행을 삭제한 요청만 카운트를 줄인다. 두 요청이 같은 행을
        # 읽은 뒤 동시에 해제해도 두 번째 DELETE 의 rowcount 는 0 이므로 중복 감소하지 않는다.
        deleted = db.execute(
            sql_delete(CommunityPostLike)
            .where(
                CommunityPostLike.post_id == post_id,
                CommunityPostLike.member_id == member_id,
            )
            .execution_options(synchronize_session=False)
        )
        # bulk DELETE는 identity map을 동기화하지 않으므로 외부 참조가 유지된
        # 객체를 명시적으로 분리해 같은 세션의 다음 토글이 DB를 다시 조회하게 한다.
        if existing in db:
            db.expunge(existing)
        if deleted.rowcount:
            db.execute(
                update(CommunityPost)
                .where(CommunityPost.id == post_id)
                .values(
                    likes_count=case(
                        (CommunityPost.likes_count > 0, CommunityPost.likes_count - 1),
                        else_=0,
                    )
                )
            )
        db.commit()
        db.refresh(post)
        return post.likes_count, False

    db.add(CommunityPostLike(post_id=post_id, member_id=member_id))
    try:
        db.execute(
            update(CommunityPost)
            .where(CommunityPost.id == post_id)
            .values(likes_count=CommunityPost.likes_count + 1)
        )
        db.commit()
    except IntegrityError as exc:
        # 동시 요청 레이스: 다른 트랜잭션이 같은 좋아요를 먼저 반영(복합 PK 충돌).
        # 롤백 후 현재 상태를 다시 읽어 멱등 결과로 수렴한다 — 카운트 중복 증가 없음.
        db.rollback()
        if not is_unique_violation(exc):
            raise
        current = db.get(CommunityPostLike, (post_id, member_id))
        post = db.get(CommunityPost, post_id)
        if post is None:
            raise NotFoundError("글을 찾을 수 없습니다") from None
        return post.likes_count, current is not None
    db.refresh(post)
    return post.likes_count, True
