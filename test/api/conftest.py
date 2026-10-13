"""API 테스트 공용 픽스처: TestClient + SQLite in-memory + InMemory 캐시."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cache import InMemoryCacheBackend, VersionedCache
from app.config import get_settings
from app.db import get_db
from app.main import create_app
from app.models import Base, Category
from app.repositories.articles import create_article


INTERNAL_TOKEN = "test-internal-token"


@pytest.fixture()
def client(monkeypatch):
    # /api/internal/* 은 토큰 또는 루프백만 허용한다. TestClient 는 루프백이 아니므로
    # 토큰을 설정하고 기본 헤더로 붙인다 (거부 경로는 test_internal_api 가 따로 검증).
    # 캐시된 Settings 와 환경 둘 다에 둔다 — autouse _isolated_media 가 캐시 객체를 패치하므로
    # 여기서 cache_clear 하면 안 되고, 개별 테스트가 cache_clear 해도 토큰이 유지돼야 한다.
    monkeypatch.setenv("INTERNAL_API_TOKEN", INTERNAL_TOKEN)
    monkeypatch.setattr(get_settings(), "internal_api_token", INTERNAL_TOKEN)
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    cache = VersionedCache(InMemoryCacheBackend(), prefix="nexus:", ttl_seconds=300)
    app = create_app(cache=cache, enable_scheduler=False, log_secrets=False)

    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        c.session_factory = factory
        c.cache = cache
        c.headers["X-Internal-Token"] = INTERNAL_TOKEN
        yield c
    engine.dispose()


@pytest.fixture(name="seed")
def seed_fixture():
    """seed(client) 형태로 호출 가능한 시드 함수를 제공한다."""
    return _seed


def _seed(client):
    """기본 카테고리 2개 + 내부 글/브런치 글 각 1건."""
    db = client.session_factory()
    curation = Category(slug="curation", name="큐레이션", display_order=1,
                        description="AI 테크 인사이트")
    community = Category(slug="community", name="커뮤니티", display_order=2)
    db.add_all([curation, community])
    db.commit()
    a1 = create_article(
        db, category_id=curation.id, article_type="newsletter",
        title="AI가 바꾸는 결제", summary="요약1", body_html="<p>본문</p>",
        key_visual_html="<svg/>", author_name="AI사업팀", source_type="internal",
        published_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    a2 = create_article(
        db, category_id=curation.id, article_type="column",
        title="브런치 인기글", summary="요약2", source_type="brunch",
        source_url="https://brunch.co.kr/@writer/1",
        thumbnail_url="https://t1.kakaocdn.net/brunch/cover.png",
        published_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    db.close()
    return a1, a2
