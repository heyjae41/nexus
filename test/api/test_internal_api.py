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


def test_internal_brunch_run_with_stubbed_fetch(client, seed, monkeypatch):
    seed(client)
    from datetime import datetime, timedelta, timezone

    from app.services.brunch import BrunchCandidate

    def fake_fetch(*args, **kwargs):
        return [
            BrunchCandidate(
                title="AI 전환 사례", url="https://brunch.co.kr/@x/1",
                author="작가", likes=3, comments=4, summary="ai",
                published_at=datetime.now(timezone.utc) - timedelta(hours=1),
            ),
            BrunchCandidate(  # 수집 윈도우(12시간) 밖 글은 선정되지 않아야 한다
                title="AI 옛날 글", url="https://brunch.co.kr/@x/0",
                author="작가", likes=999, comments=999, summary="ai",
                published_at=datetime.now(timezone.utc) - timedelta(days=30),
            ),
        ]

    monkeypatch.setattr("app.api.internal.fetch_candidates", fake_fetch)
    res = client.post("/api/internal/brunch/run")
    assert res.status_code == 200
    assert res.json()["data"]["picked"]["title"] == "AI 전환 사례"

    listed = client.get("/api/articles?category=curation").json()
    brunch_cards = [
        a for a in listed["data"]
        if a["articleType"] == "column" and a["isExternal"]
    ]
    assert any(
        c["linkUrl"] == "https://brunch.co.kr/@x/1?ref=nexus.bccard.ai"
        for c in brunch_cards
    )


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
    res = client.post("/api/internal/classes/run")
    assert res.status_code == 200
    assert res.json()["data"] == {
        "candidates": 1, "added": 1, "updated": 0, "hidden": 0,
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
