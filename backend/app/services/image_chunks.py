"""본문 이미지를 8KB 미만 조각으로 받아 조립한다.

앞단이 8192바이트를 넘는 요청 본문을 403 HTML로 거절한다. 사진은 그 한도를
넘으므로 조각으로 올리고, 조각이 모이면 파일로 저장한다.
"""
import base64
import logging
import threading
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

MAX_CHUNK_RAW = 5598
TTL_SECONDS = 600
MAX_PARTS = 1100


@dataclass
class _Upload:
    total: int
    content_type: str
    parts: dict[int, bytes] = field(default_factory=dict)
    expires_at: float = 0.0


class MemoryImageChunks:
    """프로세스 안의 조각 저장소. 테스트와 Redis 실패 시 사용한다."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, _Upload] = {}

    def add(self, key: str, index: int, total: int, content_type: str, raw: bytes) -> bytes | None:
        with self._lock:
            self._purge()
            item = self._items.get(key)
            if item is None:
                item = _Upload(
                    total=total,
                    content_type=content_type,
                    expires_at=time.monotonic() + TTL_SECONDS,
                )
                self._items[key] = item
            elif item.total != total or item.content_type != content_type:
                raise ValueError("이미지 업로드 정보가 일치하지 않습니다")
            item.parts[index] = raw
            item.expires_at = time.monotonic() + TTL_SECONDS
            if len(item.parts) < total:
                return None
            blob = b"".join(item.parts[i] for i in range(total))
            del self._items[key]
            return blob

    def _purge(self) -> None:
        now = time.monotonic()
        expired = [key for key, item in self._items.items() if item.expires_at <= now]
        for key in expired:
            del self._items[key]


class RedisImageChunks:
    """여러 파드가 같은 업로드 조각을 이어 붙이도록 Redis에 둔다."""

    def __init__(self, redis_url: str) -> None:
        import redis

        self.client = redis.Redis.from_url(
            redis_url, decode_responses=True, socket_connect_timeout=1,
        )
        self.client.ping()

    def add(self, key: str, index: int, total: int, content_type: str, raw: bytes) -> bytes | None:
        prefix = f"nexus:imgup:{key}"
        meta = f"{total}|{content_type}"
        existing = self.client.get(f"{prefix}:meta")
        if existing is not None and existing != meta:
            raise ValueError("이미지 업로드 정보가 일치하지 않습니다")
        pipe = self.client.pipeline()
        pipe.set(f"{prefix}:meta", meta, ex=TTL_SECONDS)
        pipe.set(f"{prefix}:{index}", base64.b64encode(raw).decode(), ex=TTL_SECONDS)
        pipe.sadd(f"{prefix}:idx", str(index))
        pipe.expire(f"{prefix}:idx", TTL_SECONDS)
        pipe.scard(f"{prefix}:idx")
        count = pipe.execute()[-1]
        if count < total:
            return None
        if not self.client.set(f"{prefix}:lock", "1", nx=True, ex=60):
            return None
        parts: list[bytes] = []
        for part_index in range(total):
            encoded = self.client.get(f"{prefix}:{part_index}")
            if not encoded:
                self.client.delete(f"{prefix}:lock")
                return None
            parts.append(base64.b64decode(encoded))
        self.client.delete(
            f"{prefix}:meta", f"{prefix}:idx", f"{prefix}:lock",
            *[f"{prefix}:{part_index}" for part_index in range(total)],
        )
        return b"".join(parts)


def build_image_chunks(redis_url: str):
    if not redis_url:
        return MemoryImageChunks()
    try:
        return RedisImageChunks(redis_url)
    except Exception as exc:  # noqa: BLE001 - Redis 없으면 메모리로 이어 간다
        logger.warning("이미지 조각 저장소 Redis 실패(%s) → 메모리", exc)
        return MemoryImageChunks()


def accept_image_chunk(store, member_id: int, upload_id: str, index: int, total: int, content_type: str, data: str) -> bytes | None:
    if total < 1 or total > MAX_PARTS or index < 0 or index >= total:
        raise ValueError("이미지 조각 정보가 올바르지 않습니다")
    try:
        raw = base64.b64decode(data, validate=True)
    except Exception as exc:
        raise ValueError("이미지 파일을 선택해 주세요") from exc
    if not raw or len(raw) > MAX_CHUNK_RAW:
        raise ValueError("이미지 조각이 너무 큽니다")
    return store.add(f"{member_id}:{upload_id}", index, total, content_type, raw)
