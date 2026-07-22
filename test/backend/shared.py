"""backend 단위 테스트 공용 헬퍼 (수집·인제스트 테스트에서 공유)."""
from app.cache import InMemoryCacheBackend, VersionedCache
from app.models import Category


def make_cache():
    return VersionedCache(InMemoryCacheBackend(), prefix="nexus:", ttl_seconds=300)


def seed_curation(db):
    db.add(Category(slug="curation", name="큐레이션", display_order=1))
    db.commit()


class JsonResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


class StaticJsonClient:
    def __init__(self, data):
        self.data = data
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        return JsonResponse(self.data)


class PaginatedJsonClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url, params):
        self.calls.append((url, params))
        return JsonResponse({"status": 1, "data": self.pages.get(params["offset"], [])})
