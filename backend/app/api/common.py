"""API 라우터 공통 헬퍼."""
from dataclasses import dataclass

from fastapi import Depends, Query

from app.serializers import api_response


@dataclass
class PageQuery:
    page: int
    size: int


def page_query(default_size: int = 20):
    """페이지네이션 쿼리 파라미터 공통 의존성 — size 기본값만 엔드포인트별로 다르다."""

    def dep(
        page: int = Query(default=1, ge=1),
        size: int = Query(default=default_size, ge=1, le=50),
    ) -> PageQuery:
        return PageQuery(page=page, size=size)

    return Depends(dep)


def cached_page_response(cache, key, load_page, serialize):
    """페이지 조회를 버전 캐시에 태워 표준 목록 응답(items + meta)으로 만든다."""

    def load():
        result = load_page()
        return {
            "items": [serialize(item) for item in result.items],
            "meta": {"total": result.total, "page": result.page, "limit": result.size},
        }

    loaded = cache.get_or_set(key, load)
    return api_response(loaded["items"], meta=loaded["meta"])
