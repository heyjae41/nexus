"""캐시 계층: cache-aside + 네임스페이스 버전 무효화.

- 모든 캐시 키는 `{prefix}v{version}:{key}` 형태로 저장된다.
- 쓰기(신규 글 인제스트, 브런치 선정 등) 발생 시 bump_version() 호출로
  네임스페이스 버전을 올려 이전 캐시 전체를 즉시 무효화한다 (O(1), SCAN 불필요).
- Redis 미가용 시 동일 인터페이스의 InMemory 백엔드로 자동 폴백한다.
"""
import json
import logging
import threading
import time
from typing import Any, Callable, Protocol

logger = logging.getLogger(__name__)

VERSION_KEY = "ver:articles"


class CacheBackend(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ttl_seconds: int | None) -> None: ...
    def incr(self, key: str) -> int: ...


class InMemoryCacheBackend:
    """프로세스 로컬 캐시 (개발/테스트/Redis 폴백용 — 단일 프로세스 전제)."""

    def __init__(self) -> None:
        self.store: dict[str, tuple[str, float | None]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        item = self.store.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at is not None and time.monotonic() > expires_at:
            self.store = {k: v for k, v in self.store.items() if k != key}
            return None
        return value

    def set(self, key: str, value: str, ttl_seconds: int | None) -> None:
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds else None
        self.store = {**self.store, key: (value, expires_at)}

    def incr(self, key: str) -> int:
        with self._lock:
            current = int(self.get(key) or 0) + 1
            self.set(key, str(current), None)
            return current


class RedisCacheBackend:
    def __init__(self, redis_url: str) -> None:
        import redis

        self.client = redis.Redis.from_url(
            redis_url, decode_responses=True, socket_connect_timeout=1
        )
        self.client.ping()

    def get(self, key: str) -> str | None:
        return self.client.get(key)

    def set(self, key: str, value: str, ttl_seconds: int | None) -> None:
        self.client.set(key, value, ex=ttl_seconds)

    def incr(self, key: str) -> int:
        return int(self.client.incr(key))


class VersionedCache:
    def __init__(self, backend: CacheBackend, prefix: str, ttl_seconds: int) -> None:
        self.backend = backend
        self.prefix = prefix
        self.ttl_seconds = ttl_seconds

    def _version(self) -> int:
        return int(self.backend.get(f"{self.prefix}{VERSION_KEY}") or 0)

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}v{self._version()}:{key}"

    def get(self, key: str) -> Any | None:
        raw = self.backend.get(self._full_key(key))
        return json.loads(raw) if raw is not None else None

    def set(self, key: str, value: Any) -> None:
        self.backend.set(self._full_key(key), json.dumps(value), self.ttl_seconds)

    def get_or_set(self, key: str, loader: Callable[[], Any]) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = loader()
        self.set(key, value)
        return value

    def bump_version(self) -> None:
        """DB 반영사항 발생 시 호출 — 이전 캐시 전체를 즉시 무효화한다.

        INCR 은 키가 없으면 원자적으로 1을 만든다(기본 버전 0 → 1).
        별도 초기화 가드가 없어 다중 프로세스 경합에도 안전하다.
        """
        self.backend.incr(f"{self.prefix}{VERSION_KEY}")


def create_cache(redis_url: str, prefix: str, ttl_seconds: int) -> VersionedCache:
    """Redis 연결을 시도하고 실패하면 InMemory 로 폴백한다."""
    backend: CacheBackend
    try:
        backend = RedisCacheBackend(redis_url)
        logger.info("캐시 백엔드: Redis (%s)", redis_url)
    except Exception as exc:  # noqa: BLE001 - 폴백 목적의 광역 캐치
        logger.warning("Redis 연결 실패(%s) → InMemory 캐시로 폴백", exc)
        backend = InMemoryCacheBackend()
    return VersionedCache(backend, prefix=prefix, ttl_seconds=ttl_seconds)
