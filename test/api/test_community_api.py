"""커뮤니티 API 테스트: 회원 등록 → 글쓰기 → 목록 즉시 반영 → 댓글/좋아요."""


PW = "Nexus1!pw"  # 정책(영문·숫자 포함 8자+)을 만족하는 테스트 비밀번호


def register(client, nickname="김크레딧", password=PW):
    res = client.post(
        "/api/members",
        json={"nickname": nickname, "password": password, "role": "직장인"},
    )
    assert res.status_code == 200
    return res.json()["data"]


def write_post(client, member_id, title="RAG 도입 후기", tag="노하우"):
    return client.post(
        "/api/community/posts",
        json={"memberId": member_id, "tag": tag, "title": title, "body": "본문입니다"},
    )


def test_member_register_and_relogin(client):
    first = register(client)
    again = register(client)
    assert first["id"] == again["id"]
    assert first["nickname"] == "김크레딧"


def test_member_register_validates_nickname(client):
    res = client.post("/api/members", json={"nickname": "   ", "password": PW})
    assert res.status_code == 400
    assert res.json()["success"] is False


def test_write_post_requires_member(client):
    res = write_post(client, member_id=999)
    assert res.status_code == 401
    assert "로그인" in res.json()["error"]


def test_write_post_then_visible_in_list_immediately(client):
    """글쓰기 후 목록 조회는 캐시 무효화로 즉시 새 글을 보여줘야 한다."""
    m = register(client)
    client.get("/api/community/posts")  # 목록 캐시 적재
    res = write_post(client, m["id"], title="새 글 반영 테스트")
    assert res.status_code == 200
    post = res.json()["data"]
    assert post["authorName"] == "김크레딧"

    listed = client.get("/api/community/posts").json()
    assert listed["meta"]["total"] == 1
    assert listed["data"][0]["title"] == "새 글 반영 테스트"
    assert listed["data"][0]["commentsCount"] == 0


def test_community_list_filters_by_defined_badge(client):
    m = register(client)
    write_post(client, m["id"], title="공유 자료", tag="자료")
    write_post(client, m["id"], title="업무 노하우", tag="노하우")

    listed = client.get("/api/community/posts?tag=자료").json()

    assert listed["meta"]["total"] == 1
    assert [post["title"] for post in listed["data"]] == ["공유 자료"]
    assert {post["tag"] for post in listed["data"]} == {"자료"}


def test_post_detail_with_comments_and_like_toggle(client):
    m = register(client)
    post_id = write_post(client, m["id"]).json()["data"]["id"]

    res = client.post(
        f"/api/community/posts/{post_id}/comments",
        json={"memberId": m["id"], "body": "좋은 글이네요"},
    )
    assert res.status_code == 200

    like = client.post(
        f"/api/community/posts/{post_id}/like", json={"memberId": m["id"]}
    )
    assert like.json()["data"] == {"id": post_id, "likesCount": 1, "liked": True}
    unlike = client.post(
        f"/api/community/posts/{post_id}/like", json={"memberId": m["id"]}
    )
    assert unlike.json()["data"]["likesCount"] == 0
    assert unlike.json()["data"]["liked"] is False

    detail = client.get(f"/api/community/posts/{post_id}").json()["data"]
    assert detail["title"] == "RAG 도입 후기"
    assert detail["body"] == "본문입니다"  # plain text — bodyHtml 아님 (XSS 컨벤션 분리)
    assert "bodyHtml" not in detail
    assert [c["body"] for c in detail["comments"]] == ["좋은 글이네요"]
    assert detail["comments"][0]["authorName"] == "김크레딧"


def test_like_requires_member(client):
    m = register(client)
    post_id = write_post(client, m["id"]).json()["data"]["id"]
    res = client.post(f"/api/community/posts/{post_id}/like", json={"memberId": 999})
    assert res.status_code == 403


def test_comment_requires_member(client):
    m = register(client)
    post_id = write_post(client, m["id"]).json()["data"]["id"]
    res = client.post(
        f"/api/community/posts/{post_id}/comments",
        json={"memberId": 999, "body": "x"},
    )
    assert res.status_code == 403


def test_member_profile_get_patch_delete(client):
    m = register(client)

    profile = client.get(f"/api/members/{m['id']}").json()["data"]
    assert profile["nickname"] == "김크레딧"
    assert profile["role"] == "직장인"
    assert "password" not in profile and "passwordHash" not in profile  # 해시 비노출

    # 수정: 닉네임/역할/관심사 가능
    res = client.patch(
        f"/api/members/{m['id']}",
        json={"nickname": "새닉네임", "role": "개발자", "interests": "LLM, 커리어"},
    )
    assert res.status_code == 200
    assert res.json()["data"]["nickname"] == "새닉네임"

    # 탈회
    assert client.delete(f"/api/members/{m['id']}").status_code == 200
    assert client.get(f"/api/members/{m['id']}").status_code == 401


def test_member_patch_rejects_taken_nickname(client):
    register(client, "선점")
    m = register(client, "나")
    res = client.patch(f"/api/members/{m['id']}", json={"nickname": "선점"})
    assert res.status_code == 400


def test_member_register_weak_password_returns_400_with_reason(client):
    """비밀번호 정책 위반 시 400 + 부족 항목이 담긴 에러메시지."""
    res = client.post("/api/members", json={"nickname": "약한비번", "password": "abcd"})
    assert res.status_code == 400
    error = res.json()["error"]
    assert "비밀번호" in error
    assert "8자" in error and "숫자" in error


def test_member_login_wrong_password_returns_401(client):
    register(client, "로그인테스트")
    res = client.post(
        "/api/members", json={"nickname": "로그인테스트", "password": "Wrong1!pw"}
    )
    assert res.status_code == 401
    assert "올바르지" in res.json()["error"]


def test_member_login_correct_password_returns_same_member(client):
    first = register(client, "재로그인")
    second = register(client, "재로그인")  # 같은 비밀번호 → 로그인
    assert second["id"] == first["id"]


def test_member_delete_unknown_returns_404(client):
    assert client.delete("/api/members/9999").status_code == 401


def test_member_nickname_length_consistent_with_db(client):
    """pydantic 검증 상한이 DB 컬럼(50자)과 일치해야 한다."""
    res = client.post("/api/members", json={"nickname": "가" * 51, "password": PW})
    assert res.status_code in (400, 422)  # 리포지토리 도달 전에 거부


def test_post_detail_404(client):
    assert client.get("/api/community/posts/9999").status_code == 404


def test_delete_post_requires_member_password(client):
    member_ = register(client)
    post = write_post(client, member_["id"], title="보호할 글").json()["data"]

    wrong = client.request(
        "DELETE",
        f"/api/community/posts/{post['id']}",
        json={"memberId": member_["id"], "password": "Wrong1!x"},
    )

    assert wrong.status_code == 401
    assert client.get(f"/api/community/posts/{post['id']}").status_code == 200


def test_delete_post_api_removes_from_list(client):
    """DELETE /community/posts/{id} — 비밀번호 인증 후 본인 글 삭제, 목록 즉시 반영."""
    member_ = register(client)
    post = write_post(client, member_["id"], title="삭제될 글").json()["data"]

    res = client.request(
        "DELETE",
        f"/api/community/posts/{post['id']}",
        json={"memberId": member_["id"], "password": PW},
    )
    assert res.status_code == 200
    assert res.json()["data"]["deleted"] is True

    assert client.get(f"/api/community/posts/{post['id']}").status_code == 404
    listing = client.get("/api/community/posts").json()["data"]
    assert all(p["id"] != post["id"] for p in listing)


def test_delete_post_api_forbidden_for_non_author(client):
    a = register(client, "작성자")
    post = write_post(client, a["id"]).json()["data"]
    b = register(client, "타인")

    res = client.request(
        "DELETE",
        f"/api/community/posts/{post['id']}",
        json={"memberId": b["id"], "password": PW},
    )
    assert res.status_code == 400
    assert "본인" in res.json()["error"]


def test_missing_post_returns_404_not_403(client):
    """없는 글은 404 — 회원 미온보딩(403)과 오류 시맨틱을 구분한다."""
    m = register(client)
    assert (
        client.post("/api/community/posts/9999/like", json={"memberId": m["id"]}).status_code
        == 404
    )
    assert (
        client.post(
            "/api/community/posts/9999/comments", json={"memberId": m["id"], "body": "x"}
        ).status_code
        == 404
    )
    assert client.request(
        "DELETE",
        "/api/community/posts/9999",
        json={"memberId": m["id"], "password": PW},
    ).status_code == 404
