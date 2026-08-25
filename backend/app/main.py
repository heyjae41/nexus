"""FastAPI 앱 팩토리."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.community import router as community_router
from app.api.auth import router as auth_router
from app.api.internal import router as internal_router
from app.api.routes import router
from app.cache import VersionedCache, create_cache
from app.config import get_settings
from app.serializers import api_response


class HardenedStaticFiles(StaticFiles):
    """미디어 응답에 스크립트 실행 차단 헤더를 붙인다.

    thumbnails 에는 인제스트 글의 svg 대표 이미지가 올 수 있다. 카드에서는
    <img> 로만 쓰이지만, URL 직접 열람 시 svg 가 문서로 렌더돼 스크립트가 실행될
    수 있어 CSP(sandbox)·nosniff 로 원천 차단한다 (저장 전 svg 위생처리와 이중 방어)."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; sandbox"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


def create_app(
    cache: VersionedCache | None = None,
    enable_scheduler: bool = True,
) -> FastAPI:
    settings = get_settings()
    app_cache = cache or create_cache(
        settings.redis_url, settings.cache_prefix, settings.cache_ttl_seconds
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        scheduler = None
        if enable_scheduler:
            from app.services.scheduler import build_scheduler

            scheduler = build_scheduler(app_cache)
            scheduler.start()
        yield
        if scheduler is not None:
            scheduler.shutdown(wait=False)

    app = FastAPI(title="EDU.AI API", lifespan=lifespan)
    app.state.cache = app_cache
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(community_router)
    app.include_router(internal_router)

    # 인제스트 글의 key-visual 대표 이미지 서빙 — nginx·vite 모두 /api/ 를 백엔드로
    # 프록시하므로 /api/media 로 마운트하면 별도 프록시 설정이 필요 없다.
    media_dir = Path(settings.media_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/api/media", HardenedStaticFiles(directory=str(media_dir)), name="media")

    @app.exception_handler(HTTPException)
    async def http_exc_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=api_response(success=False, error=str(exc.detail)),
        )

    return app


app = create_app()
