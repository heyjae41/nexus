"""브런치 키워드 페이지 파서/수집 윈도우 필터 테스트 (실제 페이지 픽스처 사용)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.brunch_fetcher import filter_by_window, parse_keyword_page

FIXTURE = Path(__file__).parent.parent / "fixtures" / "brunch_keyword_ai.html"


def test_parse_keyword_page_extracts_candidates():
    html = FIXTURE.read_text(encoding="utf-8")
    candidates = parse_keyword_page(html)
    assert len(candidates) == 20
    first = candidates[0]
    assert first.title == "거품이라며, 1.4조 달러를 걸었다"
    assert first.likes == 12
    assert first.comments == 0
    assert first.author == "쫑대표"
    assert first.url == "https://brunch.co.kr/@ddalkakdiary/41"
    assert first.published_at is not None
    assert first.published_at.tzinfo is not None


def test_parse_keyword_page_handles_page_without_data():
    assert parse_keyword_page("<html><body>없음</body></html>") == []


def test_filter_by_window():
    html = FIXTURE.read_text(encoding="utf-8")
    candidates = parse_keyword_page(html)
    newest = max(c.published_at for c in candidates)
    window_start = newest - timedelta(hours=12)
    inside = filter_by_window(candidates, window_start, newest + timedelta(seconds=1))
    assert all(window_start <= c.published_at for c in inside)
    assert len(inside) < len(candidates) or all(
        c.published_at >= window_start for c in candidates
    )
    # 빈 윈도우는 빈 결과
    past = datetime(2000, 1, 1, tzinfo=timezone.utc)
    assert filter_by_window(candidates, past, past + timedelta(hours=12)) == []
