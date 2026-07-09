"""응답 직렬화: 모델 → API 응답(dict, camelCase)."""
from typing import Any

from app.models import Article, Category
from app.services.links import with_ref


def api_response(
    data: Any = None,
    *,
    success: bool = True,
    error: str | None = None,
    meta: dict | None = None,
) -> dict:
    body: dict = {"success": success}
    if data is not None:
        body["data"] = data
    if error is not None:
        body["error"] = error
    if meta is not None:
        body["meta"] = meta
    return body


def serialize_category(cat: Category) -> dict:
    return {
        "id": cat.id,
        "slug": cat.slug,
        "name": cat.name,
        "description": cat.description,
        "displayOrder": cat.display_order,
    }


def article_link(article: Article) -> tuple[str, bool]:
    """(이동 URL, 외부링크 여부). 브런치 글은 원글 주소에 항상 ref 를 부착한다."""
    if article.source_type == "brunch" and article.source_url:
        return with_ref(article.source_url), True
    return f"/articles/{article.id}", False


def serialize_article_card(article: Article) -> dict:
    link, external = article_link(article)
    return {
        "id": article.id,
        "categoryId": article.category_id,
        "articleType": article.article_type,
        "title": article.title,
        "summary": article.summary,
        "authorName": article.author_name,
        "readMinutes": article.read_minutes,
        "likesCount": article.likes_count,
        "commentsCount": article.comments_count,
        "viewCount": article.view_count,
        "publishedAt": article.published_at.isoformat() if article.published_at else None,
        "thumbnailUrl": article.thumbnail_url,
        "linkUrl": link,
        "isExternal": external,
    }


def serialize_member(member) -> dict:
    return {"id": member.id, "nickname": member.nickname, "role": member.role}


def serialize_post_card(post) -> dict:
    return {
        "id": post.id,
        "tag": post.tag,
        "title": post.title,
        "authorName": post.author_name,
        "likesCount": post.likes_count,
        "commentsCount": post.comments_count,
        "createdAt": post.created_at.isoformat() if post.created_at else None,
    }


def serialize_comment(comment) -> dict:
    return {
        "id": comment.id,
        "authorName": comment.author_name,
        "body": comment.body,
        "createdAt": comment.created_at.isoformat() if comment.created_at else None,
    }


def serialize_post_detail(post, comments) -> dict:
    return {
        **serialize_post_card(post),
        # 커뮤니티 본문은 사용자 입력 plain text — 절대 HTML 로 렌더링하지 않도록
        # bodyHtml 컨벤션(아티클 전용)과 키를 분리한다 (XSS 방지)
        "body": post.body,
        "comments": [serialize_comment(c) for c in comments],
    }


def _price_text(event) -> str | None:
    if event.is_free is None:
        return None  # 가격 미상 소스 — 무료로 단정하지 않는다
    if event.is_free:
        return "무료"
    # 유료인데 금액 미상인 데이터 불일치도 크래시 없이 처리한다
    return f"{event.price_min:,}원~" if event.price_min is not None else None


def serialize_event_card(event) -> dict:
    """밋업 카드. 클릭 시 원본 사이트로 이동하며 브런치와 동일하게 ref 를 부착한다."""
    return {
        "id": event.id,
        "title": event.title,
        "hostName": event.host_name,
        "eventStart": event.event_start.isoformat() if event.event_start else None,
        "eventEnd": event.event_end.isoformat() if event.event_end else None,
        "place": event.place,
        "area": event.area,
        "priceText": _price_text(event),
        "viewCount": event.view_count,
        "eventSystemType": event.event_system_type,
        "category": event.category,
        "coverImageUrl": event.cover_image_url,
        "linkUrl": with_ref(event.source_url),
        "isExternal": True,
    }


def serialize_article_detail(article: Article) -> dict:
    return {
        **serialize_article_card(article),
        "bodyHtml": article.body_html,
        "keyVisualHtml": article.key_visual_html,
        "sourceUrl": article.source_url,
    }
