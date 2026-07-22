"""내부 실행 API 테스트 (수동 트리거 — 스케줄러와 동일 코드 경로)."""


def test_internal_ingest_run(client, seed, tmp_path, monkeypatch):
    seed(client)
    (tmp_path / "20260707_뉴스레터_수동실행.html").write_text(
        "<html><body><article><p>본문</p></article></body></html>", encoding="utf-8"
    )
    monkeypatch.setenv("CONTENTS_DIR", str(tmp_path))
    from app.config import get_settings

    get_settings.cache_clear()

    res = client.post("/api/internal/ingest/run")
    assert res.status_code == 200
    assert res.json()["data"]["ingested"] == 1

    listed = client.get("/api/articles?category=curation").json()
    assert any(a["title"] == "수동실행" for a in listed["data"])
    get_settings.cache_clear()


def test_internal_brunch_run_picks_one_article_per_keyword(client, seed, monkeypatch):
    seed(client)
    from datetime import datetime, timedelta, timezone

    from app.services.brunch import BrunchCandidate

    def fake_fetch(*, base_url, keywords):
        keyword = keywords[0]
        published_at = datetime.now(timezone.utc) - timedelta(hours=1)
        return [
            BrunchCandidate(
                title=f"{keyword} 낮은 점수", url=f"https://brunch.co.kr/@x/{keyword}-low",
                author="작가", likes=1, comments=1, summary="ai",
                published_at=published_at,
            ),
            BrunchCandidate(
                title=f"{keyword} 인기글", url=f"https://brunch.co.kr/@x/{keyword}-top",
                author="작가", likes=10, comments=5, summary="ai",
                published_at=published_at,
            ),
        ]

    monkeypatch.setattr("app.api.internal.fetch_candidates", fake_fetch)
    res = client.post("/api/internal/brunch/run")

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["candidates"] == 8
    assert [article["title"] for article in data["picked"]] == [
        "인공지능 인기글",
        "AI 인기글",
        "머신러닝 인기글",
        "데이터과학 인기글",
    ]

    listed = client.get("/api/articles?category=curation").json()
    brunch_cards = [
        article
        for article in listed["data"]
        if article["articleType"] == "column" and article["isExternal"]
    ]
    expected_titles = {
        "인공지능 인기글",
        "AI 인기글",
        "머신러닝 인기글",
        "데이터과학 인기글",
    }
    assert {article["title"] for article in brunch_cards} >= expected_titles


def test_internal_classes_run_with_stubbed_fetch(client, monkeypatch):
    from app.services.fastcampus_fetcher import FastCampusCandidate

    candidate = FastCampusCandidate(
        source_id="99", source_category_code="BIZ", source_category_name="AI/업무생산성",
        source_category_url="https://fastcampus.co.kr/category_online_biz",
        source_rank=1, title="수동 수집 클래스", summary="설명",
        source_url="https://fastcampus.co.kr/biz-test", thumbnail_url=None,
        sub_category_name="업무자동화", format_name="올인원", qualification="누구나",
        running_time_minutes=300, sale_price=100000, list_price=200000,
        badges=("얼리버드",),
    )
    monkeypatch.setattr(
        "app.services.fastcampus_fetcher.fetch_fastcampus_candidates",
        lambda: [candidate],
    )
    monkeypatch.setattr(
        "app.services.daker_fetcher.fetch_daker_candidates",
        lambda: [],
    )
    monkeypatch.setattr(
        "app.services.dacon_fetcher.fetch_dacon_candidates",
        lambda: [],
    )
    res = client.post("/api/internal/classes/run")
    assert res.status_code == 200
    assert res.json()["data"] == {
        "candidates": 1, "added": 1, "updated": 0, "hidden": 0, "skipped": 0,
        "sources": {
            "fastcampus": {"candidates": 1, "added": 1, "updated": 0, "hidden": 0, "skipped": 0},
            "daker": {"candidates": 0, "added": 0, "updated": 0, "hidden": 0, "skipped": 0},
            "dacon": {"candidates": 0, "added": 0, "updated": 0, "hidden": 0, "skipped": 0},
        },
    }
    listed = client.get("/api/classes?category=BIZ").json()
    assert listed["data"][0]["title"] == "수동 수집 클래스"


def test_internal_classes_maps_external_schema_error_to_502(client, monkeypatch):
    def malformed():
        raise ValueError("패스트캠퍼스 응답 스키마 오류")

    monkeypatch.setattr(
        "app.services.fastcampus_fetcher.fetch_fastcampus_candidates", malformed,
    )
    res = client.post("/api/internal/classes/run")
    assert res.status_code == 502
    assert res.json()["error"] == "클래스 수집에 실패했습니다"
