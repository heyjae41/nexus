"""backend 단위 테스트 공용 헬퍼 (수집·인제스트 테스트에서 공유)."""
from app.cache import InMemoryCacheBackend, VersionedCache
from app.models import Category


def make_cache():
    return VersionedCache(InMemoryCacheBackend(), prefix="nexus:", ttl_seconds=300)


def seed_curation(db):
    db.add(Category(slug="curation", name="큐레이션", display_order=1))
    db.commit()
