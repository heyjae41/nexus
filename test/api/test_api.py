"""FastAPI 엔드포인트 테스트 (픽스처는 conftest.py 공용)."""
from datetime import datetime, timezone


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_categories_returns_active_menu(client, seed):
    seed(client)
    res = client.get("/api/categories")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    slugs = [c["slug"] for c in body["data"]]
    assert slugs == ["curation", "community"]


def test_articles_list_card_fields(client, seed):
    seed(client)
    res = client.get("/api/articles?category=curation")
    body = res.json()
    assert body["success"] is True
    assert body["meta"]["total"] == 2
    card = body["data"][0]  # 최신순 → 브런치 글
    assert card["title"] == "브런치 인기글"
    assert card["articleType"] == "brunch"
    # 브런치 글 링크에는 항상 ref 파라미터가 붙는다
    assert card["linkUrl"] == "https://brunch.co.kr/@writer/1?ref=nexus.bccard.ai"
    assert card["isExternal"] is True
    internal = body["data"][1]
    assert internal["linkUrl"] == f"/articles/{internal['id']}"
    assert internal["isExternal"] is False


def test_article_detail_increments_view(client, seed):
    a1, _ = seed(client)
    res1 = client.get(f"/api/articles/{a1.id}")
    res2 = client.get(f"/api/articles/{a1.id}")
    assert res1.status_code == 200
    assert res2.json()["data"]["viewCount"] == 2
    assert res2.json()["data"]["bodyHtml"] == "<p>본문</p>"
    assert res2.json()["data"]["keyVisualHtml"] == "<svg/>"


def test_article_detail_404(client):
    res = client.get("/api/articles/9999")
    assert res.status_code == 404
    assert res.json()["success"] is False


def test_like_increments(client, seed):
    a1, _ = seed(client)
    res = client.post(f"/api/articles/{a1.id}/like")
    assert res.status_code == 200
    assert res.json()["data"]["likesCount"] == 1


def test_like_reflects_immediately_in_cached_list(client, seed):
    """DB 반영사항(좋아요)은 캐시 무효화로 목록에 즉시 반영되어야 한다."""
    a1, _ = seed(client)
    client.get("/api/articles?category=curation")  # 목록 캐시 적재
    client.post(f"/api/articles/{a1.id}/like")
    listed = client.get("/api/articles?category=curation").json()
    card = next(c for c in listed["data"] if c["id"] == a1.id)
    assert card["likesCount"] == 1  # 캐시가 남아있으면 0 으로 실패


def test_home_bundle_sections(client, seed):
    seed(client)
    res = client.get("/api/home")
    body = res.json()
    assert body["success"] is True
    sections = body["data"]["sections"]
    assert [s["category"]["slug"] for s in sections] == ["curation", "community"]
    curation_section = sections[0]
    assert len(curation_section["articles"]) == 2


def test_home_cache_invalidated_on_new_article(client, seed):
    """캐시 정책: 신규 글 등록(쓰기) 후 홈 조회는 즉시 최신을 반영해야 한다."""
    seed(client)
    first = client.get("/api/home").json()
    assert len(first["data"]["sections"][0]["articles"]) == 2

    # 신규 글 등록을 서비스 경로(캐시 무효화 포함)로 시뮬레이션
    db = client.session_factory()
    from app.services.publish import publish_article

    publish_article(
        db, client.cache,
        category_slug="curation", article_type="guide",
        title="새 가이드", summary="방금 등록", body_html="<p>new</p>",
        source_type="internal",
        published_at=datetime(2026, 7, 3, tzinfo=timezone.utc),
    )
    db.close()

    after = client.get("/api/home").json()
    titles = [a["title"] for a in after["data"]["sections"][0]["articles"]]
    assert "새 가이드" in titles  # 캐시가 남아있으면 실패
