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
        "linkUrl": link,
        "isExternal": external,
    }


def serialize_article_detail(article: Article) -> dict:
    return {
        **serialize_article_card(article),
        "bodyHtml": article.body_html,
        "keyVisualHtml": article.key_visual_html,
        "sourceUrl": article.source_url,
    }
