"""회원가입·로그인·서버 세션 API 계약."""
from sqlalchemy import select

from app.models import AuthSession, Member

PW = "Nexus1!pw"
PROFILE = {
    "nickname": "새회원",
    "password": PW,
    "role": "기획자",
    "interests": ["서비스기획", "PM/PO"],
}


def test_nickname_availability_and_duplicate_registration(client):
    available = client.get("/api/auth/nickname-available", params={"nickname": "새회원"})
    assert available.status_code == 200
    assert available.json()["data"] == {"nickname": "새회원", "available": True}

    created = client.post("/api/auth/register", json=PROFILE)
    assert created.status_code == 201
    assert created.json()["data"]["interests"] == ["서비스기획", "PM/PO"]

    taken = client.get("/api/auth/nickname-available", params={"nickname": "  새회원  "})
    assert taken.json()["data"]["available"] is False
    duplicate = client.post("/api/auth/register", json=PROFILE)
    assert duplicate.status_code == 409
    assert "사용 중" in duplicate.json()["error"]


def test_register_validates_password_role_and_at_least_one_interest(client):
    weak = client.post("/api/auth/register", json={**PROFILE, "nickname": "약한암호", "password": "weak"})
    assert weak.status_code == 400
    assert "8자" in weak.json()["error"] and "숫자" in weak.json()["error"]

    bad_role = client.post("/api/auth/register", json={**PROFILE, "nickname": "역할오류", "role": "직장인"})
    assert bad_role.status_code == 422

    no_interest = client.post("/api/auth/register", json={**PROFILE, "nickname": "관심없음", "interests": []})
    assert no_interest.status_code == 422


def test_session_cookie_secure_flag_follows_forwarded_proto(client):
    """프록시(TLS 종단) 뒤에서는 X-Forwarded-Proto 로 https 를 판별해 Secure 쿠키를 발급한다."""
    https = client.post(
        "/api/auth/register",
        json={**PROFILE, "nickname": "보안쿠키"},
        headers={"X-Forwarded-Proto": "https"},
    )
    assert https.status_code == 201
    assert "secure" in https.headers["set-cookie"].lower()

    plain = client.post("/api/auth/register", json={**PROFILE, "nickname": "일반쿠키"})
    assert plain.status_code == 201
    assert "secure" not in plain.headers["set-cookie"].lower()


def test_register_creates_hashed_password_and_hashed_server_session(client):
    res = client.post("/api/auth/register", json=PROFILE)
    assert res.status_code == 201
    assert "nexus_session" in res.cookies
    assert "password" not in str(res.json()).lower()

    db = client.session_factory()
    member = db.scalars(select(Member).where(Member.nickname == "새회원")).one()
    session = db.scalars(select(AuthSession).where(AuthSession.member_id == member.id)).one()
    assert member.password_hash != PW
    assert session.token_hash != res.cookies["nexus_session"]
    assert len(session.token_hash) == 64
    db.close()


def test_login_me_logout_session_lifecycle(client):
    client.post("/api/auth/register", json=PROFILE)
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401

    wrong = client.post("/api/auth/login", json={"nickname": "새회원", "password": "Wrong1!pw"})
    assert wrong.status_code == 401
    assert "올바르지" in wrong.json()["error"]

    login = client.post("/api/auth/login", json={"nickname": "새회원", "password": PW})
    assert login.status_code == 200
    assert login.json()["data"]["nickname"] == "새회원"
    assert client.get("/api/auth/me").json()["data"]["role"] == "기획자"

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_authenticated_profile_update_and_withdrawal(client):
    client.post("/api/auth/register", json=PROFILE)
    updated = client.patch(
        "/api/auth/me",
        json={"role": "개발자", "interests": ["백엔드", "AI/ML", "DevOps"]},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["role"] == "개발자"
    assert updated.json()["data"]["interests"] == ["백엔드", "AI/ML", "DevOps"]

    empty = client.patch("/api/auth/me", json={"interests": []})
    assert empty.status_code == 422

    deleted = client.delete("/api/auth/me")
    assert deleted.status_code == 200
    assert client.get("/api/auth/me").status_code == 401

    db = client.session_factory()
    assert db.scalars(select(Member).where(Member.nickname == "새회원")).first() is None
    assert db.scalars(select(AuthSession)).first() is None
    db.close()


def test_profile_mutation_requires_session(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.patch("/api/auth/me", json={"role": "개발자"}).status_code == 401
    assert client.delete("/api/auth/me").status_code == 401


def test_session_cannot_read_mutate_or_write_as_another_member(client):
    first = client.post("/api/auth/register", json=PROFILE).json()["data"]
    second_profile = {
        **PROFILE,
        "nickname": "두번째회원",
        "role": "개발자",
        "interests": ["백엔드"],
    }
    client.post("/api/auth/register", json=second_profile)

    assert client.get(f"/api/members/{first['id']}").status_code == 403
    assert client.patch(
        f"/api/members/{first['id']}", json={"role": "개발자"}
    ).status_code == 403
    assert client.delete(f"/api/members/{first['id']}").status_code == 403
    assert client.post(
        "/api/community/posts",
        json={"memberId": first["id"], "tag": "팁", "title": "위조", "body": "본문"},
    ).status_code == 403
