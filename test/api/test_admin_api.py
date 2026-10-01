"""어드민 글쓰기·이미지·권한 API."""
import base64
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import Article, Category, Member

PW = "Nexus1!pw"
PROFILE = {
    "nickname": "운영자",
    "password": PW,
    "role": "기획자",
    "interests": ["서비스기획"],
}
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def _register(client, nickname, **extra):
    payload = {**PROFILE, "nickname": nickname, **extra}
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201, res.text
    return res


def _promote(client, nickname):
    db = client.session_factory()
    member = db.scalars(select(Member).where(Member.nickname == nickname)).one()
    member.access_role = "admin"
    db.commit()
    db.close()


def _curation(client):
    db = client.session_factory()
    db.add(Category(slug="curation", name="큐레이션", display_order=1))
    db.commit()
    db.close()


def test_new_member_access_role_defaults_to_user(client):
    res = _register(client, "일반회원")
    data = res.json()["data"]
    assert data["accessRole"] == "user"
    assert data["superAdmin"] is False
    denied = client.post("/api/admin/articles", json={
        "articleType": "column", "title": "제목", "bodyHtml": "<p>본문</p>",
    })
    assert denied.status_code == 403


def test_super_admin_is_not_a_writer_until_granted(client, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "super_admin", "수퍼")
    res = _register(client, "수퍼")
    data = res.json()["data"]
    assert data["accessRole"] == "user"
    assert data["superAdmin"] is True
    denied = client.post("/api/admin/articles", json={
        "articleType": "column", "title": "제목", "bodyHtml": "<p>본문</p>",
    })
    assert denied.status_code == 403


def test_admin_publishes_article_visible_to_readers_and_pinned(client):
    _curation(client)
    _register(client, "운영자")
    _promote(client, "운영자")
    created = client.post("/api/admin/articles", json={
        "articleType": "column",
        "title": "우리가 쓴 컬럼",
        "summary": "한 줄 요약",
        "bodyHtml": '<p onclick="x">본문입니다</p><script>bad()</script>',
    })
    assert created.status_code == 201, created.text
    body = created.json()["data"]
    assert body["articleType"] == "column"
    assert body["authorName"] == "운영자"
    assert body["linkUrl"] == f"/articles/{body['id']}"
    assert body["isExternal"] is False
    assert "script" not in (body["bodyHtml"] or "").lower()
    assert "onclick" not in (body["bodyHtml"] or "")

    public = client.get(f"/api/articles/{body['id']}")
    assert public.status_code == 200
    assert "본문입니다" in public.json()["data"]["bodyHtml"]

    db = client.session_factory()
    collected = Article(
        category_id=db.scalars(select(Category).where(Category.slug == "curation")).one().id,
        article_type="column",
        title="더 최신 수집글",
        source_type="brunch",
        source_url="https://brunch.co.kr/@w/9",
        published_at=datetime.now(timezone.utc) + timedelta(hours=1),
        status="published",
    )
    db.add(collected)
    db.commit()
    db.close()

    listed = client.get("/api/articles", params={"category": "curation", "type": "column"})
    titles = [item["title"] for item in listed.json()["data"]]
    assert titles[0] == "우리가 쓴 컬럼"


def test_anonymous_cannot_publish(client):
    res = client.post("/api/admin/articles", json={
        "articleType": "guide", "title": "제목", "bodyHtml": "<p>본문</p>",
    })
    assert res.status_code == 401


def test_admin_uploads_png_and_rejects_text(client):
    _register(client, "운영자")
    _promote(client, "운영자")
    ok = client.post(
        "/api/admin/media",
        files={"file": ("shot.png", PNG, "image/png")},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["data"]["url"].startswith("/api/media/authored/")
    assert ok.json()["data"]["url"].endswith(".png")

    bad = client.post(
        "/api/admin/media",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert bad.status_code == 400


def test_user_cannot_upload(client):
    _register(client, "일반회원")
    res = client.post(
        "/api/admin/media",
        files={"file": ("shot.png", PNG, "image/png")},
    )
    assert res.status_code == 403


def test_writer_cannot_grant_access(client):
    _register(client, "운영자")
    _promote(client, "운영자")
    listed = client.get("/api/admin/members")
    assert listed.status_code == 403


def test_super_admin_grants_writer_in_database(client, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "super_admin", "수퍼, heyaj2")
    _register(client, "작가")
    client.post("/api/auth/logout")
    _register(client, "수퍼")

    listed = client.get("/api/admin/members")
    assert listed.status_code == 200
    names = {item["nickname"]: item for item in listed.json()["data"]}
    assert names["작가"]["accessRole"] == "user"
    assert "password" not in str(listed.json()).lower()

    promoted = client.patch(
        f"/api/admin/members/{names['작가']['id']}",
        json={"accessRole": "admin"},
    )
    assert promoted.status_code == 200
    assert promoted.json()["data"]["accessRole"] == "admin"

    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"nickname": "작가", "password": PW})
    _curation(client)
    created = client.post("/api/admin/articles", json={
        "articleType": "guide", "title": "가이드", "bodyHtml": "<p>본문</p>",
    })
    assert created.status_code == 201, created.text


def test_author_can_update_own_authored_article(client):
    _curation(client)
    _register(client, "운영자")
    _promote(client, "운영자")
    created = client.post("/api/admin/articles", json={
        "articleType": "column",
        "title": "처음 제목",
        "summary": "처음 요약",
        "bodyHtml": "<p>처음 본문</p>",
    })
    assert created.status_code == 201, created.text
    article_id = created.json()["data"]["id"]
    published_at = created.json()["data"]["publishedAt"]
    before = client.cache._version()

    updated = client.patch(f"/api/admin/articles/{article_id}", json={
        "articleType": "guide",
        "title": "고친 제목",
        "summary": "고친 요약",
        "bodyHtml": '<p onclick="x">고친 본문</p><script>bad()</script>',
    })
    assert updated.status_code == 200, updated.text
    body = updated.json()["data"]
    assert body["title"] == "고친 제목"
    assert body["articleType"] == "guide"
    assert body["summary"] == "고친 요약"
    assert body["authorName"] == "운영자"
    assert body["sourceType"] == "authored"
    assert body["publishedAt"] == published_at
    assert "고친 본문" in body["bodyHtml"]
    assert "script" not in body["bodyHtml"].lower()
    assert "onclick" not in body["bodyHtml"]
    assert client.cache._version() == before + 1

    public = client.get(f"/api/articles/{article_id}")
    assert public.json()["data"]["title"] == "고친 제목"
    assert "고친 본문" in public.json()["data"]["bodyHtml"]


def test_other_member_cannot_update_authored_article(client):
    _curation(client)
    _register(client, "운영자")
    _promote(client, "운영자")
    created = client.post("/api/admin/articles", json={
        "articleType": "column",
        "title": "운영자 글",
        "bodyHtml": "<p>본문</p>",
    })
    article_id = created.json()["data"]["id"]
    _register(client, "다른사람")
    _promote(client, "다른사람")
    denied = client.patch(f"/api/admin/articles/{article_id}", json={
        "articleType": "column",
        "title": "가로챈 제목",
        "bodyHtml": "<p>가로챔</p>",
    })
    assert denied.status_code == 403
    public = client.get(f"/api/articles/{article_id}")
    assert public.json()["data"]["title"] == "운영자 글"


def test_collected_article_cannot_be_updated(client):
    _curation(client)
    _register(client, "운영자")
    _promote(client, "운영자")
    db = client.session_factory()
    category_id = db.scalars(select(Category).where(Category.slug == "curation")).one().id
    collected = Article(
        category_id=category_id,
        article_type="column",
        title="브런치 글",
        author_name="운영자",
        source_type="brunch",
        source_url="https://brunch.co.kr/@w/edit-me",
        published_at=datetime.now(timezone.utc),
        status="published",
    )
    db.add(collected)
    db.commit()
    article_id = collected.id
    db.close()
    denied = client.patch(f"/api/admin/articles/{article_id}", json={
        "articleType": "column",
        "title": "고치면 안 됨",
        "bodyHtml": "<p>본문</p>",
    })
    assert denied.status_code == 403


def test_uploaded_image_is_served_and_kept_in_the_article(client):
    _curation(client)
    _register(client, "운영자")
    _promote(client, "운영자")
    uploaded = client.post(
        "/api/admin/media",
        files={"file": ("shot.png", PNG, "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    url = uploaded.json()["data"]["url"]
    fetched = client.get(url)
    assert fetched.status_code == 200, fetched.text
    assert fetched.content.startswith(b"\x89PNG")

    created = client.post("/api/admin/articles", json={
        "articleType": "column",
        "title": "그림 있는 글",
        "bodyHtml": f'<p>설명</p><img src="https://edu.dev.bccard.ai{url}" alt="도표">',
    })
    assert created.status_code == 201, created.text
    body = created.json()["data"]["bodyHtml"]
    assert f'src="{url}"' in body
    assert "edu.dev.bccard.ai" not in body
    public = client.get(f"/api/articles/{created.json()['data']['id']}")
    assert f'src="{url}"' in public.json()["data"]["bodyHtml"]


def test_jpg_content_type_alias_is_stored(client):
    _register(client, "운영자")
    _promote(client, "운영자")
    jpeg = b"\xff\xd8\xff" + b"\x00" * 16
    uploaded = client.post(
        "/api/admin/media",
        files={"file": ("shot.jpg", jpeg, "image/jpg")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["data"]["url"].endswith(".jpg")


def test_image_upload_is_assembled_from_small_parts(client):
    _register(client, "운영자")
    _promote(client, "운영자")
    raw = PNG + b"\x00" * 40
    parts = [raw[:20], raw[20:]]
    upload_id = "a" * 32
    for index, part in ((1, parts[1]), (0, parts[0])):
        payload = {
            "uploadId": upload_id,
            "index": index,
            "total": 2,
            "contentType": "image/png",
            "data": base64.b64encode(part).decode(),
        }
        assert len(json.dumps(payload).encode()) < 8192
        res = client.post("/api/admin/media/parts", json=payload)
        assert res.status_code == 200, res.text
        if index == 1:
            assert "url" not in res.json()["data"]
        else:
            url = res.json()["data"]["url"]
    fetched = client.get(url)
    assert fetched.status_code == 200
    assert fetched.content == raw


# --- 글 본문 조각 저장: 앞단(WAF)이 8KB 넘는 요청 본문을 403 으로 거절한다 ---

def _body_part_payload(upload_id, index, total, part, **meta):
    return {
        "uploadId": upload_id, "index": index, "total": total,
        "contentType": "text/html", "data": base64.b64encode(part).decode(),
        "articleType": "guide", "title": "긴 글", "summary": "요약", **meta,
    }


def _post_body_parts(client, body_html: str, **meta):
    raw = body_html.encode("utf-8")
    size = 3900
    parts = [raw[i:i + size] for i in range(0, len(raw), size)] or [b""]
    upload_id = "b" * 32
    last = None
    for index, part in enumerate(parts):
        payload = _body_part_payload(upload_id, index, len(parts), part, **meta)
        assert len(json.dumps(payload).encode()) < 8192, "조각 요청은 8KB 미만이어야 한다"
        last = client.post("/api/admin/articles/parts", json=payload)
        assert last.status_code in (200, 201), last.text
        if index < len(parts) - 1:
            assert last.json()["data"] == {"received": index}
    return last


def test_long_article_is_created_from_small_parts(client):
    _curation(client)
    _register(client, "운영자")
    _promote(client, "운영자")
    body = "<p>" + ("한글 본문 내용입니다. " * 1500) + "</p>"  # 8KB 를 훌쩍 넘는 본문
    assert len(body.encode()) > 8192
    res = _post_body_parts(client, body)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["title"] == "긴 글"
    detail = client.get(f"/api/articles/{data['id']}").json()["data"]
    assert "한글 본문 내용입니다." in detail["bodyHtml"]
    assert detail["bodyHtml"].count("한글 본문 내용입니다.") == 1500


def test_long_article_is_updated_from_small_parts_by_author_only(client):
    _curation(client)
    _register(client, "운영자")
    _promote(client, "운영자")
    created = _post_body_parts(client, "<p>처음</p>").json()["data"]
    body = "<p>" + ("수정된 본문. " * 1200) + "</p>"
    res = _post_body_parts(client, body, articleId=created["id"], title="고친 제목")
    assert res.status_code == 200
    assert res.json()["data"]["title"] == "고친 제목"
    assert "수정된 본문." in client.get(f"/api/articles/{created['id']}").json()["data"]["bodyHtml"]

    client.post("/api/auth/logout")
    _register(client, "다른운영자")
    _promote(client, "다른운영자")
    payload = _body_part_payload("c" * 32, 0, 1, b"<p>x</p>", articleId=created["id"])
    assert client.post("/api/admin/articles/parts", json=payload).status_code == 403


def test_non_admin_cannot_create_article_from_parts(client):
    _register(client, "일반회원")
    payload = _body_part_payload("d" * 32, 0, 1, b"<p>x</p>")
    assert client.post("/api/admin/articles/parts", json=payload).status_code == 403


def test_body_parts_reject_invalid_utf8(client):
    _register(client, "운영자")
    _promote(client, "운영자")
    payload = _body_part_payload("e" * 32, 0, 1, b"\xff\xfe<p>")
    assert client.post("/api/admin/articles/parts", json=payload).status_code == 400


def test_body_parts_are_rejected_before_storing_when_not_authorized(client):
    """권한 검사는 첫 조각에서 — 아무 회원이나 조각으로 Redis 를 채우지 못하게 한다."""
    _curation(client)
    _register(client, "일반회원")
    first_of_two = _body_part_payload("f" * 32, 0, 2, b"<p>x</p>")
    assert client.post("/api/admin/articles/parts", json=first_of_two).status_code == 403

    client.post("/api/auth/logout")
    _register(client, "운영자")
    _promote(client, "운영자")
    created = _post_body_parts(client, "<p>처음</p>").json()["data"]
    client.post("/api/auth/logout")
    _register(client, "다른운영자")
    _promote(client, "다른운영자")
    first_of_two = _body_part_payload("g" * 32, 0, 2, b"<p>x</p>", articleId=created["id"])
    assert client.post("/api/admin/articles/parts", json=first_of_two).status_code == 403
    missing = _body_part_payload("h" * 32, 0, 2, b"<p>x</p>", articleId=999_999)
    assert client.post("/api/admin/articles/parts", json=missing).status_code == 404


def test_body_parts_enforce_part_caps(client):
    _curation(client)
    _register(client, "운영자")
    _promote(client, "운영자")
    too_many = _body_part_payload("i" * 32, 0, 500, b"<p>x</p>")
    assert client.post("/api/admin/articles/parts", json=too_many).status_code == 400
    too_big = _body_part_payload("j" * 32, 0, 2, b"x" * 4000)
    assert client.post("/api/admin/articles/parts", json=too_big).status_code == 400
