"""FastAPI 앱 팩토리."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.community import router as community_router
from app.api.auth import router as auth_router
from app.api.internal import router as internal_router
from app.api.routes import router
from app.cache import VersionedCache, create_cache
from app.config import get_settings
from app.serializers import api_response


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

    app = FastAPI(title="NEXUS API", lifespan=lifespan)
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

    @app.exception_handler(HTTPException)
    async def http_exc_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=api_response(success=False, error=str(exc.detail)),
        )

    return app


app = create_app()
