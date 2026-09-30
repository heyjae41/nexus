"""어드민 글쓰기·이미지·권한 API."""
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
