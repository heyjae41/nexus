"""업로드 조각 저장소 — 회원당 동시에 열어 둘 수 있는 업로드 수에 상한을 둔다 (Redis 메모리 고갈 방지)."""
import pytest

from app.services.image_chunks import MAX_OPEN_UPLOADS, MemoryImageChunks, accept_image_chunk, owner_of

ONE_PART = "AAAA"  # base64 "\x00\x00\x00"


def test_owner_is_the_member_prefix_of_the_key():
    assert owner_of("7:abc") == "7"
    assert owner_of("7:body:abc") == "7"


def test_member_cannot_open_more_than_the_cap():
    store = MemoryImageChunks()
    for i in range(MAX_OPEN_UPLOADS):
        assert accept_image_chunk(store, 7, f"u{i}", 0, 2, "image/png", ONE_PART) is None
    with pytest.raises(ValueError, match="업로드"):
        accept_image_chunk(store, 7, "one-too-many", 0, 2, "image/png", ONE_PART)
    # 다른 회원은 영향 없음, 이미 연 업로드에 조각을 더 보내는 것도 가능
    assert accept_image_chunk(store, 8, "u0", 0, 2, "image/png", ONE_PART) is None
    assert accept_image_chunk(store, 7, "u0", 1, 2, "image/png", ONE_PART) is not None


def test_completed_upload_frees_a_slot():
    store = MemoryImageChunks()
    for i in range(MAX_OPEN_UPLOADS):
        accept_image_chunk(store, 7, f"u{i}", 0, 2, "image/png", ONE_PART)
    accept_image_chunk(store, 7, "u0", 1, 2, "image/png", ONE_PART)
    assert accept_image_chunk(store, 7, "fresh", 0, 2, "image/png", ONE_PART) is None



class FakeRedis:
    """RedisImageChunks 가 쓰는 명령만 흉내 낸다 (문자열 값, TTL 은 무시)."""

    def __init__(self):
        self.kv: dict[str, str] = {}
        self.sets: dict[str, set[str]] = {}

    def get(self, key):
        return self.kv.get(key)

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.kv:
            return False
        self.kv[key] = value
        return True

    def exists(self, key):
        return int(key in self.kv)

    def delete(self, *keys):
        for key in keys:
            self.kv.pop(key, None)

    def sadd(self, key, member):
        self.sets.setdefault(key, set()).add(member)

    def srem(self, key, member):
        self.sets.get(key, set()).discard(member)

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def scard(self, key):
        return len(self.sets.get(key, set()))

    def expire(self, key, ttl):
        return True

    def ping(self):
        return True

    def pipeline(self):
        return _FakePipeline(self)


class _FakePipeline:
    def __init__(self, client):
        self.client, self.ops = client, []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.ops.append((name, args, kwargs))
            return self
        return record

    def execute(self):
        return [getattr(self.client, name)(*args, **kwargs) for name, args, kwargs in self.ops]


def _redis_store():
    from app.services.image_chunks import RedisImageChunks

    store = RedisImageChunks.__new__(RedisImageChunks)
    store.client = FakeRedis()
    return store


def test_redis_cap_blocks_the_ninth_open_upload_and_frees_on_completion():
    store = _redis_store()
    for i in range(MAX_OPEN_UPLOADS):
        assert accept_image_chunk(store, 7, f"u{i}", 0, 2, "image/png", ONE_PART) is None
    with pytest.raises(ValueError, match="업로드"):
        accept_image_chunk(store, 7, "extra", 0, 2, "image/png", ONE_PART)
    assert accept_image_chunk(store, 8, "u0", 0, 2, "image/png", ONE_PART) is None  # 다른 회원
    assert accept_image_chunk(store, 7, "u0", 1, 2, "image/png", ONE_PART) is not None
    assert "7:u0" not in store.client.smembers("nexus:imgup:owner:7")
    assert accept_image_chunk(store, 7, "fresh", 0, 2, "image/png", ONE_PART) is None


def test_redis_cap_prunes_uploads_whose_meta_expired():
    store = _redis_store()
    for i in range(MAX_OPEN_UPLOADS):
        accept_image_chunk(store, 7, f"u{i}", 0, 2, "image/png", ONE_PART)
    store.client.kv.pop("nexus:imgup:7:u3:meta")  # TTL 만료 흉내
    assert accept_image_chunk(store, 7, "fresh", 0, 2, "image/png", ONE_PART) is None
    assert "7:u3" not in store.client.smembers("nexus:imgup:owner:7")
