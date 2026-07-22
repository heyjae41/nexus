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
        self._lock = threading.RLock()  # incr → get/set 재진입 허용

    def get(self, key: str) -> str | None:
        with self._lock:
            item = self.store.get(key)
            if item is None:
                return None
            value, expires_at = item
            if expires_at is not None and time.monotonic() > expires_at:
                del self.store[key]
                return None
            return value

    def set(self, key: str, value: str, ttl_seconds: int | None) -> None:
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds else None
        with self._lock:
            self.store[key] = (value, expires_at)

    def incr(self, key: str) -> int:
        with self._lock:
            current = int(self.get(key) or 0) + 1
            self.set(key, str(current), None)
            return current


class RedisCacheBackend:
    """기동 후 Redis 런타임 장애 시 예외를 전파하지 않고 캐시 미스처럼 동작한다.

    get 실패 → None(미스, 로더가 DB 직접 조회) / set·incr 실패 → 무시.
    캐시가 가용성을 낮추는 단일 장애점이 되지 않도록 하는 방어선이다.
    """

    def __init__(self, redis_url: str) -> None:
        import redis

        self.client = redis.Redis.from_url(
            redis_url, decode_responses=True, socket_connect_timeout=1
        )
        self.client.ping()

    @staticmethod
    def _errors() -> type[Exception]:
        import redis

        return redis.exceptions.RedisError

    def get(self, key: str) -> str | None:
        try:
            return self.client.get(key)
        except self._errors() as exc:
            logger.warning("Redis GET 실패(%s) → 캐시 미스로 처리", exc)
            return None

    def set(self, key: str, value: str, ttl_seconds: int | None) -> None:
        try:
            self.client.set(key, value, ex=ttl_seconds)
        except self._errors() as exc:
            logger.warning("Redis SET 실패(%s) → 캐시 저장 생략", exc)

    def incr(self, key: str) -> int:
        try:
            return int(self.client.incr(key))
        except self._errors() as exc:
            logger.warning("Redis INCR 실패(%s) → 버전 bump 생략", exc)
            return 0


class VersionedCache:
    def __init__(self, backend: CacheBackend, prefix: str, ttl_seconds: int) -> None:
        self.backend = backend
        self.prefix = prefix
        self.ttl_seconds = ttl_seconds
        # single-flight: 동시 미스 시 로더를 프로세스 내 1회만 실행 (스탬피드 방지)
        self._flight_lock = threading.Lock()
        self._in_flight: dict[str, threading.Event] = {}

    def _version(self) -> int:
        return int(self.backend.get(f"{self.prefix}{VERSION_KEY}") or 0)

    def _full_key_for(self, version: int, key: str) -> str:
        return f"{self.prefix}v{version}:{key}"

    def _full_key(self, key: str) -> str:
        return self._full_key_for(self._version(), key)

    def get(self, key: str) -> Any | None:
        for _ in range(2):
            version = self._version()
            raw = self.backend.get(self._full_key_for(version, key))
            if self._version() == version:
                return json.loads(raw) if raw is not None else None
        return None

    def set(self, key: str, value: Any) -> None:
        self.backend.set(self._full_key(key), json.dumps(value), self.ttl_seconds)

    def get_or_set(self, key: str, loader: Callable[[], Any]) -> Any:
        version = self._version()
        full_key = self._full_key_for(version, key)
        raw = self.backend.get(full_key)
        if self._version() != version:
            return self.get_or_set(key, loader)
        if raw is not None:
            return json.loads(raw)
        with self._flight_lock:
            waiter = self._in_flight.get(full_key)
            if waiter is None:
                self._in_flight[full_key] = threading.Event()
        if waiter is not None:
            # 다른 요청이 같은 키를 로드 중 — 완료를 기다렸다 캐시를 재사용
            waiter.wait(timeout=5)
            return self.get_or_set(key, loader)
        try:
            value = loader()
            # 로드 중 DB 쓰기가 commit되어 버전이 바뀌었다면 구 스냅샷은 저장하지 않는다.
            if self._version() == version:
                self.backend.set(full_key, json.dumps(value), self.ttl_seconds)
            return value
        finally:
            with self._flight_lock:
                event = self._in_flight.pop(full_key, None)
            if event is not None:
                event.set()

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
