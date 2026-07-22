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
    assert any(k.startswith("nexus:v0:") for k in raw_keys)
    cache.bump_version()
    cache.set("home", "v2")
    assert any(k.startswith("nexus:v1:") for k in backend.store.keys())


def test_first_bump_invalidates_initial_version():
    """버전 키가 없는 최초 상태에서도 bump 는 반드시 무효화해야 한다 (TOCTOU 가드 불필요)."""
    cache = make_cache()
    cache.set("home", "initial")
    cache.bump_version()
    assert cache.get("home") is None


def test_get_or_set_uses_loader_once():
    cache = make_cache()
    calls = []

    def loader():
        calls.append(1)
        return "loaded"

    assert cache.get_or_set("detail:1", loader) == "loaded"
    assert cache.get_or_set("detail:1", loader) == "loaded"
    assert len(calls) == 1


def test_get_or_set_does_not_store_old_snapshot_under_new_version():
    """DB 로드 중 쓰기가 commit되면 구 스냅샷을 새 버전 키에 저장하지 않는다."""
    cache = make_cache()

    def stale_loader():
        cache.bump_version()  # 로드와 수집 commit의 결정적 경합 재현
        return "old-db-snapshot"

    assert cache.get_or_set("classes", stale_loader) == "old-db-snapshot"
    assert cache.get("classes") is None
    assert cache.get_or_set("classes", lambda: "fresh-db-snapshot") == "fresh-db-snapshot"
    assert cache.get("classes") == "fresh-db-snapshot"


def test_create_cache_falls_back_to_memory_when_redis_unavailable():
    cache = create_cache(redis_url="redis://127.0.0.1:1/0", prefix="nexus:", ttl_seconds=60)
    cache.set("k", "v")
    assert cache.get("k") == "v"
    assert isinstance(cache.backend, InMemoryCacheBackend)


def test_redis_backend_degrades_gracefully_on_runtime_failure():
    """기동 후 Redis 장애(연결 단절 등)가 나도 예외를 전파하지 않고
    캐시 미스처럼 동작해 서비스 가용성을 유지한다."""
    import redis as redis_lib

    from app.cache import RedisCacheBackend, VersionedCache

    backend = RedisCacheBackend.__new__(RedisCacheBackend)  # __init__(ping) 우회

    class DownClient:
        def get(self, *a, **k):
            raise redis_lib.exceptions.ConnectionError("down")

        def set(self, *a, **k):
            raise redis_lib.exceptions.ConnectionError("down")

        def incr(self, *a, **k):
            raise redis_lib.exceptions.ConnectionError("down")

    backend.client = DownClient()
    cache = VersionedCache(backend, prefix="nexus:", ttl_seconds=300)

    calls = {"n": 0}

    def loader():
        calls["n"] += 1
        return {"ok": True}

    assert cache.get_or_set("home", loader) == {"ok": True}  # 로더로 우회, 예외 없음
    cache.bump_version()  # 예외 없이 무시
    assert calls["n"] == 1


def test_inmemory_backend_thread_safety():
    """InMemory 폴백: 동시 set/incr 에서 갱신 유실(lost-update) 없이 카운터가 정확하다."""
    import threading

    from app.cache import InMemoryCacheBackend

    backend = InMemoryCacheBackend()
    N = 2000

    def do_incr():
        for _ in range(N):
            backend.incr("counter")

    def do_set():
        for i in range(N):
            backend.set(f"k{i % 7}", str(i), None)

    threads = [threading.Thread(target=do_incr), threading.Thread(target=do_set)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert backend.get("counter") == str(N)


def test_get_or_set_single_flight():
    """동시 캐시 미스에서 로더(DB 조회)는 한 번만 실행된다 — 스탬피드 방지."""
    import threading
    import time

    from app.cache import InMemoryCacheBackend, VersionedCache

    cache = VersionedCache(InMemoryCacheBackend(), prefix="nexus:", ttl_seconds=300)
    calls = {"n": 0}
    started = threading.Event()

    def loader():
        calls["n"] += 1
        started.set()
        time.sleep(0.2)  # 로더가 도는 동안 두 번째 요청 도착
        return {"v": 1}

    results = []
    t1 = threading.Thread(target=lambda: results.append(cache.get_or_set("k", loader)))
    t1.start()
    assert started.wait(1)
    t2 = threading.Thread(target=lambda: results.append(cache.get_or_set("k", loader)))
    t2.start()
    t1.join()
    t2.join()

    assert calls["n"] == 1  # 두 번째 요청은 리더의 결과를 기다렸다 재사용
    assert results == [{"v": 1}, {"v": 1}]
