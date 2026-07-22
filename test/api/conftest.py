"""API 테스트 공용 픽스처: TestClient + SQLite in-memory + InMemory 캐시."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cache import InMemoryCacheBackend, VersionedCache
from app.db import get_db
from app.main import create_app
from app.models import Base, Category
from app.repositories.articles import create_article


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    cache = VersionedCache(InMemoryCacheBackend(), prefix="nexus:", ttl_seconds=300)
    app = create_app(cache=cache, enable_scheduler=False)

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
