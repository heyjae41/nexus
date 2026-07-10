"""커뮤니티 API 테스트: 회원 등록 → 글쓰기 → 목록 즉시 반영 → 댓글/좋아요."""


def register(client, nickname="김크레딧"):
    res = client.post("/api/members", json={"nickname": nickname, "role": "직장인"})
    assert res.status_code == 200
    return res.json()["data"]


def write_post(client, member_id, title="RAG 도입 후기"):
    return client.post(
        "/api/community/posts",
        json={"memberId": member_id, "tag": "노하우", "title": title, "body": "본문입니다"},
    )


def test_member_register_and_relogin(client):
    first = register(client)
    again = register(client)
    assert first["id"] == again["id"]
    assert first["nickname"] == "김크레딧"


def test_member_register_validates_nickname(client):
    res = client.post("/api/members", json={"nickname": "   "})
    assert res.status_code == 400
    assert res.json()["success"] is False


def test_write_post_requires_member(client):
    res = write_post(client, member_id=999)
    assert res.status_code == 403
    assert "회원" in res.json()["error"]


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
    m = client.post(
        "/api/members",
        json={"nickname": "김크레딧", "role": "직장인", "email": "heyjae@bccard.com"},
    ).json()["data"]

    profile = client.get(f"/api/members/{m['id']}").json()["data"]
    assert profile["nickname"] == "김크레딧"
    assert profile["email"] == "heyjae@bccard.com"
    assert profile["role"] == "직장인"

    # 수정: 닉네임/역할/관심사 가능
    res = client.patch(
        f"/api/members/{m['id']}",
        json={"nickname": "새닉네임", "role": "개발자", "interests": "LLM, 커리어"},
    )
    assert res.status_code == 200
    assert res.json()["data"]["nickname"] == "새닉네임"

    # 이메일 변경은 거부
    res = client.patch(f"/api/members/{m['id']}", json={"email": "other@x.com"})
    assert res.status_code == 400
    assert "이메일" in res.json()["error"]

    # 탈회
    assert client.delete(f"/api/members/{m['id']}").status_code == 200
    assert client.get(f"/api/members/{m['id']}").status_code == 404


def test_member_patch_rejects_taken_nickname(client):
    client.post("/api/members", json={"nickname": "선점"})
    m = client.post("/api/members", json={"nickname": "나"}).json()["data"]
    res = client.patch(f"/api/members/{m['id']}", json={"nickname": "선점"})
    assert res.status_code == 400


def test_member_email_set_once_via_patch(client):
    m = client.post("/api/members", json={"nickname": "이메일없음"}).json()["data"]
    res = client.patch(f"/api/members/{m['id']}", json={"email": "first@bccard.com"})
    assert res.status_code == 200
    assert res.json()["data"]["email"] == "first@bccard.com"
    res = client.patch(f"/api/members/{m['id']}", json={"email": "second@bccard.com"})
    assert res.status_code == 400


def test_member_delete_unknown_returns_404(client):
    assert client.delete("/api/members/9999").status_code == 404


def test_member_duplicate_email_returns_400(client):
    client.post("/api/members", json={"nickname": "회원A", "email": "dup@bccard.com"})
    res = client.post("/api/members", json={"nickname": "회원B", "email": "dup@bccard.com"})
    assert res.status_code == 400
    assert "이메일" in res.json()["error"]


def test_member_nickname_length_consistent_with_db(client):
    """pydantic 검증 상한이 DB 컬럼(50자)과 일치해야 한다."""
    res = client.post("/api/members", json={"nickname": "가" * 51})
    assert res.status_code in (400, 422)  # 리포지토리 도달 전에 거부


def test_post_detail_404(client):
    assert client.get("/api/community/posts/9999").status_code == 404
