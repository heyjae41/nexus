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
