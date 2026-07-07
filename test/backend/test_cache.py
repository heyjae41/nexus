"""캐시 정책 테스트.

정책: cache-aside + 네임스페이스 버전 무효화.
- 캐시 키에 버전이 포함되며, 쓰기 발생 시 bump_version() 으로 전체 무효화(O(1)).
- DB 반영사항(신규 글 등)은 무효화 직후 조회에서 항상 최신을 가져와야 한다.
"""
from app.cache import InMemoryCacheBackend, VersionedCache, create_cache


def make_cache() -> VersionedCache:
    return VersionedCache(InMemoryCacheBackend(), prefix="nexus:", ttl_seconds=300)


def test_get_returns_none_on_miss():
    cache = make_cache()
    assert cache.get("home") is None


def test_set_then_get_roundtrip():
    cache = make_cache()
    cache.set("home", {"sections": [1, 2]})
    assert cache.get("home") == {"sections": [1, 2]}


def test_bump_version_invalidates_all_keys():
    cache = make_cache()
    cache.set("home", "old-home")
    cache.set("articles:list:curation:1", "old-list")
    cache.bump_version()
    assert cache.get("home") is None
    assert cache.get("articles:list:curation:1") is None


def test_new_value_after_bump_is_served():
    cache = make_cache()
    cache.set("home", "old")
    cache.bump_version()          # 신규 글 등록 시점
    cache.set("home", "fresh")    # 다음 조회가 DB에서 재적재
    assert cache.get("home") == "fresh"


def test_keys_are_prefixed_and_versioned():
    backend = InMemoryCacheBackend()
    cache = VersionedCache(backend, prefix="nexus:", ttl_seconds=300)
    cache.set("home", "v")
    raw_keys = list(backend.store.keys())
    assert any(k.startswith("nexus:v1:") for k in raw_keys)
    cache.bump_version()
    cache.set("home", "v2")
    assert any(k.startswith("nexus:v2:") for k in backend.store.keys())


def test_get_or_set_uses_loader_once():
    cache = make_cache()
    calls = []

    def loader():
        calls.append(1)
        return "loaded"

    assert cache.get_or_set("detail:1", loader) == "loaded"
    assert cache.get_or_set("detail:1", loader) == "loaded"
    assert len(calls) == 1


def test_create_cache_falls_back_to_memory_when_redis_unavailable():
    cache = create_cache(redis_url="redis://127.0.0.1:1/0", prefix="nexus:", ttl_seconds=60)
    cache.set("k", "v")
    assert cache.get("k") == "v"
    assert isinstance(cache.backend, InMemoryCacheBackend)
