"""뉴스레터 목록 페이지 파서/수집 테스트 (실제 응답 픽스처 사용).

수집 대상 (목록 → 신규 글 상세 링크):
- 스티비 아카이브 3종: page.stibee.com/archives/{listId}/emails JSON
- KMA 한국능률협회: /kr/usrs/eduRegMgnt/selectInsightSubList.do JSON
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.newsletter_fetcher import (
    NewsletterCandidate,
    clean_preview,
    fetch_newsletter_candidates,
    filter_recent,
    parse_aitimes_featured,
    parse_kma_rows,
    parse_published_time_meta,
    parse_stibee_emails,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"
NOW = datetime(2026, 7, 23, 0, 0, tzinfo=timezone.utc)


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# --- 스티비 아카이브 파싱 ---

def test_parse_stibee_emails_maps_fields():
    candidates = parse_stibee_emails(load("stibee_archive_emails.json"), publisher="모두레터")
    assert len(candidates) == 3  # permanentLink 없는 항목 제외
    c = candidates[0]
    assert isinstance(c, NewsletterCandidate)
    assert c.title == "📮 에이전트 여럿을 한 번에 굴린다면?"
    assert c.url == "https://stib.ee/kWWM"
    assert c.publisher == "모두레터"
    assert c.source_type == "stibee"
    # 개인화 병합태그($%name%$)는 요약에서 제거된다
    assert c.summary == "#GPT5.6 #Inkling I 님, 모두레터가 왔어요😺"
    assert c.published_at == datetime.fromisoformat("2026-07-20T07:00:03.211509954+09:00")


def test_parse_stibee_emails_skips_items_without_link():
    candidates = parse_stibee_emails(load("stibee_archive_emails.json"), publisher="모두레터")
    assert all(c.url for c in candidates)
    assert "링크 없는 항목" not in [c.title for c in candidates]


def test_parse_stibee_emails_rejects_non_http_links():
    """상세 링크는 http(s)만 허용한다 (javascript: 등 응답 오염 방어)."""
    items = [{
        "subject": "악성 링크", "permanentLink": "javascript:alert(1)",
        "sentTime": "2026-07-20T07:00:00+09:00",
    }]
    assert parse_stibee_emails(items, publisher="모두레터") == []


def test_parse_stibee_naive_senttime_treated_as_kst():
    """오프셋 없는 sentTime 도 aware(KST) 로 보정한다 — filter_recent 비교 안전."""
    items = [{
        "subject": "오프셋 없음", "permanentLink": "https://stib.ee/NAIVE",
        "sentTime": "2026-07-20T07:00:00",
    }]
    [c] = parse_stibee_emails(items, publisher="모두레터")
    assert c.published_at.tzinfo is not None
    assert filter_recent([c], now=NOW, days=7) == [c]


def test_parse_stibee_emails_skips_resend_duplicates():
    """"(재발송)" 메일은 원본과 내용이 같으므로 수집하지 않는다."""
    candidates = parse_stibee_emails(load("stibee_archive_emails.json"), publisher="모두레터")
    assert not any("재발송" in c.title for c in candidates)
    # 원본 발송분은 그대로 수집된다
    assert any(c.url == "https://stib.ee/CBbM" for c in candidates)


def test_parse_stibee_emails_thumbnail_passthrough():
    candidates = parse_stibee_emails(
        load("stibee_archive_emails.json"),
        publisher="모두레터",
        thumbnail_url="https://img2.stibee.com/header.png",
    )
    assert candidates[0].thumbnail_url == "https://img2.stibee.com/header.png"


def test_clean_preview_strips_merge_tags():
    assert clean_preview("$%name%$님 안녕하세요") == "님 안녕하세요"
    assert clean_preview("  공백 정리  ") == "공백 정리"
    assert clean_preview(None) == ""


# --- KMA 인사이트 뉴스레터 파싱 ---

def test_parse_kma_rows_maps_fields():
    candidates = parse_kma_rows(load("kma_insight_newsletter_list.json"), base_url="https://www.kma.or.kr")
    assert len(candidates) == 2  # BRD_SEQ/제목 없는 행 제외
    c = candidates[0]
    assert c.title == "여름 마케팅, 길어진 여름, 예측하는 AI | 0 TO 1 | 26년 7월 2주차 뉴스레터"
    # 상세 페이지 이동 URL (formDetail 파라미터 조립)
    assert "eduRegMgntForm.do" in c.url
    assert "p_brd_seq=894" in c.url
    assert "cateNm=insNewsletterDtl" in c.url
    assert c.publisher == "KMA 0 TO 1"
    assert c.source_type == "kma"
    assert c.thumbnail_url == "https://www.kma.or.kr/upload/hub/894/2026071008455402578.jpg"
    # REG_DT(KST) → aware datetime
    assert c.published_at is not None
    assert c.published_at.tzinfo is not None
    assert c.published_at.astimezone(timezone.utc).date().isoformat() == "2026-07-09"


def test_parse_kma_rows_drops_path_traversal_filename():
    """SAVE_FILENM 에 경로 조작 문자가 섞이면 썸네일을 버린다 (응답 오염 방어)."""
    payload = {"rows": [{
        "BRD_SEQ": 900, "TTL": "제목", "REG_DT": "20260720090000",
        "METATEXT": "", "SAVE_FILENM": "../../etc/passwd",
    }]}
    [c] = parse_kma_rows(payload, base_url="https://www.kma.or.kr")
    assert c.thumbnail_url is None


def test_parse_kma_rows_without_thumbnail_or_metatext():
    candidates = parse_kma_rows(load("kma_insight_newsletter_list.json"), base_url="https://www.kma.or.kr")
    plain = candidates[1]
    assert plain.thumbnail_url is None
    assert plain.publisher == "KMA 뉴스레터"


# --- AI타임스 메인 대표기사 파싱 ---

AITIMES_BASE = "https://www.aitimes.com"


def load_text(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_aitimes_featured_maps_fields():
    candidates = parse_aitimes_featured(load_text("aitimes_main.html"), base_url=AITIMES_BASE)
    c = candidates[0]
    assert c.title == "앤트로픽 '클로드 오퍼스 5' 출시 임박…개발 도구·버텍스서 정황 포착"
    assert c.url == "https://www.aitimes.com/news/articleView.html?idxno=213127"
    assert c.publisher == "AI타임스"
    assert c.source_type == "aitimes"
    assert c.summary.startswith("앤트로픽의 차세대 플래그십")
    assert c.thumbnail_url == "https://cdn.aitimes.com/news/thumbnail/custom/20260724/213127_216531_139_600.jpg"
    assert c.published_at is None  # 발행시각은 상세 페이지 메타에서 보강


def test_parse_aitimes_featured_resolves_relative_links():
    candidates = parse_aitimes_featured(load_text("aitimes_main.html"), base_url=AITIMES_BASE)
    urls = [c.url for c in candidates]
    assert "https://www.aitimes.com/news/articleView.html?idxno=213099" in urls


def test_parse_aitimes_featured_only_selector_block_and_skips_broken():
    """지정 selector(grid-1) 밖의 기사, 외부 도메인 링크, 제목 없는 항목은 제외한다."""
    candidates = parse_aitimes_featured(load_text("aitimes_main.html"), base_url=AITIMES_BASE)
    titles = [c.title for c in candidates]
    assert len(candidates) == 2
    assert "grid-1 밖의 기사 — 수집 대상 아님" not in titles
    assert "외부 도메인 링크 기사" not in titles


def test_parse_published_time_meta():
    published = parse_published_time_meta(load_text("aitimes_article_detail.html"))
    assert published == datetime.fromisoformat("2026-07-24T12:21:21+09:00")
    assert parse_published_time_meta("<html>메타 없음</html>") is None


# --- 최근 기간 필터 ---

def test_filter_recent_keeps_only_window():
    old = NewsletterCandidate(
        title="옛글", url="https://stib.ee/OLD", publisher="p", source_type="stibee",
        published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )
    fresh = NewsletterCandidate(
        title="새글", url="https://stib.ee/NEW", publisher="p", source_type="stibee",
        published_at=datetime(2026, 7, 22, tzinfo=timezone.utc),
    )
    undated = NewsletterCandidate(
        title="날짜없음", url="https://stib.ee/NA", publisher="p", source_type="stibee",
        published_at=None,
    )
    assert filter_recent([old, fresh, undated], now=NOW, days=7) == [fresh]


# --- 원격 수집 (스텁 클라이언트) ---

from shared import FakeResponse  # noqa: E402 — fetcher 테스트 공용 스텁


class FakeClient:
    """URL 별 응답을 흉내내는 스텁 (GET=스티비, POST=KMA)."""

    def __init__(self, get_routes, post_routes):
        self.get_routes = get_routes
        self.post_routes = post_routes

    def get(self, url):
        return self.get_routes.get(url, FakeResponse(None, fail=True))

    def post(self, url, data=None):
        return self.post_routes.get(url, FakeResponse(None, fail=True))


STIBEE_BASE = "https://page.stibee.com"
KMA_BASE = "https://www.kma.or.kr"
KMA_LIST_URL = f"{KMA_BASE}/kr/usrs/eduRegMgnt/selectInsightSubList.do"


def make_client(stibee_fail=False, kma_fail=False, aitimes_fail=False):
    emails = load("stibee_archive_emails.json")
    values = {"formSettings": {"formHeaderImage": "https://img2.stibee.com/header.png"}}
    return FakeClient(
        get_routes={
            f"{STIBEE_BASE}/archives/181723/emails": FakeResponse(emails, fail=stibee_fail),
            f"{STIBEE_BASE}/archives/181723/values": FakeResponse(values),
            AITIMES_BASE: FakeResponse(load_text("aitimes_main.html"), fail=aitimes_fail),
            f"{AITIMES_BASE}/news/articleView.html?idxno=213127": FakeResponse(
                load_text("aitimes_article_detail.html")
            ),
            # idxno=213099 상세 라우트는 의도적으로 없음 → 발행시각 폴백 경로 검증
        },
        post_routes={
            KMA_LIST_URL: FakeResponse(load("kma_insight_newsletter_list.json"), fail=kma_fail),
        },
    )


def fetch_with(client):
    return fetch_newsletter_candidates(
        stibee_pairs=[("181723", "모두레터")],
        stibee_base_url=STIBEE_BASE,
        kma_base_url=KMA_BASE,
        aitimes_base_url=AITIMES_BASE,
        client=client,
    )


def test_fetch_collects_all_sources():
    result = fetch_with(make_client())
    assert len(result) == 7  # 스티비 3 + AI타임스 2 + KMA 2
    stibee = [c for c in result if c.source_type == "stibee"]
    assert all(c.thumbnail_url == "https://img2.stibee.com/header.png" for c in stibee)


def test_fetch_aitimes_published_at_from_detail_meta():
    """AI타임스 대표기사의 발행시각은 상세 페이지 article:published_time 메타로 채운다."""
    result = fetch_with(make_client())
    featured = next(
        c for c in result if c.url == f"{AITIMES_BASE}/news/articleView.html?idxno=213127"
    )
    assert featured.published_at == datetime.fromisoformat("2026-07-24T12:21:21+09:00")


def test_fetch_aitimes_detail_failure_falls_back_to_fetch_time():
    """상세 조회 실패 시 기사를 버리지 않고 수집 시각으로 폴백한다 (aware 보장)."""
    result = fetch_with(make_client())
    fallback = next(
        c for c in result if c.url == f"{AITIMES_BASE}/news/articleView.html?idxno=213099"
    )
    assert fallback.published_at is not None
    assert fallback.published_at.tzinfo is not None


def test_fetch_continues_when_one_source_fails():
    """한 소스 실패는 다른 소스 수집을 막지 않는다 (부분 성공)."""
    result = fetch_with(make_client(stibee_fail=True))
    assert {c.source_type for c in result} == {"aitimes", "kma"}
    assert len(result) == 4

    result = fetch_with(make_client(aitimes_fail=True))
    assert {c.source_type for c in result} == {"stibee", "kma"}
    assert len(result) == 5


def test_fetch_stibee_values_failure_only_drops_thumbnail():
    """values(헤더 이미지) 조회 실패 시 썸네일 없이 수집은 계속한다."""
    client = make_client()
    client.get_routes.pop(f"{STIBEE_BASE}/archives/181723/values")
    stibee = [c for c in fetch_with(client) if c.source_type == "stibee"]
    assert len(stibee) == 3
    assert all(c.thumbnail_url is None for c in stibee)


def test_fetch_rejects_non_stibee_header_image():
    """헤더 이미지는 stibee CDN 도메인만 허용한다 (응답 오염 방어)."""
    client = make_client()
    client.get_routes[f"{STIBEE_BASE}/archives/181723/values"] = FakeResponse(
        {"formSettings": {"formHeaderImage": "https://evil.example.com/pixel.png"}}
    )
    stibee = [c for c in fetch_with(client) if c.source_type == "stibee"]
    assert all(c.thumbnail_url is None for c in stibee)
