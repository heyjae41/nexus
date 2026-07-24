"""뉴스레터 목록 페이지에서 신규 발행분 후보를 추출한다.

- 스티비 아카이브: page.stibee.com/archives/{listId}/emails 가 발행 이력 JSON 을 반환한다.
  상세 이동 URL 은 각 항목의 permanentLink(stib.ee 단축 주소)다.
- KMA 인사이트 뉴스레터: /kr/usrs/eduRegMgnt/selectInsightSubList.do POST 가
  게시판 rows JSON 을 반환한다. 상세 URL 은 formDetail 파라미터로 조립한다.
- AI타임스: 메인 페이지 대표기사 블록(grid-1)을 CSS selector 로 추출한다.
  발행시각은 기사 상세의 article:published_time 메타로 보강한다.
"""
import html
import logging
import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

FETCH_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NexusBot/1.0)"}
KST = timezone(timedelta(hours=9))

# 스티비 개인화 병합태그 ($%name%$ 등) — 미리보기 텍스트에서 제거한다
MERGE_TAG_RE = re.compile(r"\$%[^%$]*%\$")

KMA_LIST_PATH = "/kr/usrs/eduRegMgnt/selectInsightSubList.do"
KMA_DETAIL_PATH = "/kr/usrs/eduRegMgnt/eduRegMgntForm.do"
# 목록 페이지 formList/formDetail hidden 필드와 동일한 값 (sidx 후행 공백도 사이트 원본 그대로)
KMA_LIST_PARAMS = {
    "sidx": "BRD_SEQ ",
    "sord": "DESC",
    "rows": "30",
    "page": "1",
    "p_menu_id": "50",
    "mkey": "50",
    "cateNm": "insNewsletter",
    "p_assct_cdclsf_id": "1",
    "p_srch_text": "",
}
KMA_DETAIL_QUERY = "p_menu_id=50&mkey=50&cateNm=insNewsletterDtl&p_hmpgcd=30&p_assct_cdclsf_id=1"

# AI타임스 메인 대표기사 블록 (요청 스펙의 CSS selector 그대로)
AITIMES_FEATURED_SELECTOR = (
    "#idx-default > div.index-grid-container.cs01__global.cs01__ly01"
    " > div > div > div.index-item.grid-1 > article"
)
AITIMES_PUBLISHER = "AI타임스"


@dataclass(frozen=True)
class NewsletterCandidate:
    title: str
    url: str
    publisher: str      # 뉴스레터 이름 (카드의 작성자 표기)
    source_type: str    # "stibee" | "kma"
    summary: str = ""
    published_at: datetime | None = None
    thumbnail_url: str | None = None


def clean_preview(text) -> str:
    if not text:
        return ""
    return MERGE_TAG_RE.sub("", text).strip()


def _parse_iso(value) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    # 오프셋 없는 응답 방어: 스티비는 한국 서비스이므로 KST 로 간주한다
    # (naive 그대로 두면 filter_recent 의 aware 비교에서 TypeError)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=KST)


def parse_stibee_emails(
    items: list,
    publisher: str,
    thumbnail_url: str | None = None,
) -> list[NewsletterCandidate]:
    candidates = []
    for item in items or []:
        title = (item.get("subject") or "").strip()
        url = (item.get("permanentLink") or "").strip()
        if not (title and url.startswith(("https://", "http://"))):
            continue
        if "(재발송)" in title:  # 재발송 메일은 원본과 내용이 같다 (링크만 다름)
            continue
        candidates.append(
            NewsletterCandidate(
                title=title,
                url=url,
                publisher=publisher,
                source_type="stibee",
                summary=clean_preview(item.get("previewText")),
                published_at=_parse_iso(item.get("sentTime")),
                thumbnail_url=thumbnail_url,
            )
        )
    return candidates


def _stibee_header_image(url) -> str | None:
    """스티비 CDN 도메인 이미지만 허용한다 (응답 오염 시 외부 이미지 차단)."""
    if not url or not isinstance(url, str):
        return None
    hostname = urlsplit(url).hostname or ""
    if hostname != "stibee.com" and not hostname.endswith(".stibee.com"):
        return None
    return url


def _parse_kma_reg_dt(value) -> datetime | None:
    """REG_DT("yyyymmddHHMMSS", KST) → aware datetime."""
    try:
        return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=KST)
    except (TypeError, ValueError):
        return None


def _safe_filename(value) -> str:
    """썸네일 경로에 붙일 파일명 — 경로 조작 문자가 섞이면 버린다 (응답 오염 방어)."""
    filename = (value or "").strip()
    if any(token in filename for token in ("/", "\\", "..", "?", "#")):
        return ""
    return filename


def _kma_publisher(metatext) -> str:
    decoded = html.unescape(metatext or "")
    series = " ".join(part.strip() for part in decoded.split(",") if part.strip())
    return f"KMA {series}" if series else "KMA 뉴스레터"


def parse_kma_rows(payload: dict, base_url: str) -> list[NewsletterCandidate]:
    candidates = []
    for row in (payload or {}).get("rows") or []:
        seq = row.get("BRD_SEQ")
        # KMA API 는 제목을 HTML 엔티티(&#39; 등)로 인코딩해 준다 — 카드 노출용 디코드
        title = html.unescape(row.get("TTL") or "").strip()
        if not (seq and title):
            continue
        filename = _safe_filename(row.get("SAVE_FILENM"))
        candidates.append(
            NewsletterCandidate(
                title=title,
                url=f"{base_url}{KMA_DETAIL_PATH}?p_brd_seq={seq}&{KMA_DETAIL_QUERY}",
                publisher=_kma_publisher(row.get("METATEXT")),
                source_type="kma",
                published_at=_parse_kma_reg_dt(row.get("REG_DT")),
                thumbnail_url=f"{base_url}/upload/hub/{seq}/{filename}" if filename else None,
            )
        )
    return candidates


def _aitimes_host_url(url, base_url: str) -> str | None:
    """aitimes.com 도메인의 http(s) URL 만 허용한다 (상대경로는 base 로 절대화)."""
    if not url or not isinstance(url, str):
        return None
    absolute = urljoin(f"{base_url}/", url)
    parts = urlsplit(absolute)
    hostname = parts.hostname or ""
    if parts.scheme not in ("http", "https"):
        return None
    if hostname != "aitimes.com" and not hostname.endswith(".aitimes.com"):
        return None
    return absolute


def parse_aitimes_featured(html: str, base_url: str) -> list[NewsletterCandidate]:
    """메인 대표기사 블록에서 후보를 추출한다 — 발행시각은 상세 메타로 나중에 보강."""
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    for block in soup.select(AITIMES_FEATURED_SELECTOR):
        for link in block.select("a.photo-titbg"):
            url = _aitimes_host_url(link.get("href"), base_url)
            heading = link.select_one("h2")
            title = heading.get_text(strip=True) if heading else ""
            if not (url and title):
                continue
            summary_el = link.select_one(".auto-sums")
            item = link.find_parent(class_="item") or block
            # 대표 썸네일 영역(.auto-images)을 우선 — item 내 다른 이미지(아바타 등) 오채택 방지
            image = item.select_one(".auto-images img") or item.select_one("img")
            candidates.append(
                NewsletterCandidate(
                    title=title,
                    url=url,
                    publisher=AITIMES_PUBLISHER,
                    source_type="aitimes",
                    summary=summary_el.get_text(" ", strip=True) if summary_el else "",
                    thumbnail_url=_aitimes_host_url(
                        image.get("src") if image else None, base_url
                    ),
                )
            )
    return candidates


def parse_published_time_meta(html: str) -> datetime | None:
    """기사 상세의 article:published_time 메타 — 속성 순서에 의존하지 않게 bs4 로 찾는다."""
    meta = BeautifulSoup(html or "", "html.parser").find(
        "meta", attrs={"property": "article:published_time"}
    )
    return _parse_iso(meta.get("content")) if meta else None


def filter_recent(
    candidates: list[NewsletterCandidate],
    *,
    now: datetime,
    days: int,
) -> list[NewsletterCandidate]:
    """최근 N일 내 발행분만 남긴다 — 최초 수집 시 아카이브 전체 유입을 막는다."""
    threshold = now - timedelta(days=days)
    return [c for c in candidates if c.published_at is not None and c.published_at >= threshold]


def _fetch_stibee_list(
    http, base_url: str, list_id: str, publisher: str
) -> list[NewsletterCandidate]:
    res = http.get(f"{base_url}/archives/{list_id}/emails")
    res.raise_for_status()
    thumbnail = None
    try:
        values = http.get(f"{base_url}/archives/{list_id}/values")
        values.raise_for_status()
        thumbnail = _stibee_header_image(
            (values.json().get("formSettings") or {}).get("formHeaderImage")
        )
    except (httpx.HTTPError, ValueError, AttributeError):
        logger.warning("스티비 아카이브 정보(values) 조회 실패(%s) — 썸네일 없이 진행", list_id)
    return parse_stibee_emails(res.json(), publisher=publisher, thumbnail_url=thumbnail)


def _fetch_aitimes(http, base_url: str) -> list[NewsletterCandidate]:
    res = http.get(base_url)
    res.raise_for_status()
    enriched = []
    for c in parse_aitimes_featured(res.text, base_url=base_url):
        published = None
        try:
            detail = http.get(c.url)
            detail.raise_for_status()
            published = parse_published_time_meta(detail.text)
        except Exception as exc:  # 기사 단위 격리 — 상세 실패가 대표기사 수집을 막지 않게
            logger.warning("AI타임스 상세 조회 실패(%s): %s", c.url, exc)
        if published is None:
            # 수집 시각 폴백 — 대표기사는 통상 당일 발행이라 오차가 작다
            logger.warning("AI타임스 발행시각 미확인 — 수집 시각으로 폴백: %s", c.url)
            published = datetime.now(timezone.utc)
        enriched.append(replace(c, published_at=published))
    return enriched


def fetch_newsletter_candidates(
    *,
    stibee_pairs: list[tuple[str, str]],
    stibee_base_url: str = "https://page.stibee.com",
    kma_base_url: str = "https://www.kma.or.kr",
    aitimes_base_url: str = "https://www.aitimes.com",
    client: httpx.Client | None = None,
) -> list[NewsletterCandidate]:
    """전체 소스를 조회해 후보를 모은다 — 소스 단위 실패는 건너뛴다 (URL 중복 제거)."""
    own_client = client is None
    http = client or httpx.Client(timeout=15, headers=FETCH_HEADERS, follow_redirects=True)
    seen: set[str] = set()
    results: list[NewsletterCandidate] = []

    def extend(candidates: list[NewsletterCandidate]) -> None:
        for c in candidates:
            if c.url not in seen:
                seen.add(c.url)
                results.append(c)

    try:
        for list_id, publisher in stibee_pairs:
            try:
                extend(_fetch_stibee_list(http, stibee_base_url, list_id, publisher))
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning("스티비 아카이브 조회 실패(%s): %s", list_id, exc)
        try:
            extend(_fetch_aitimes(http, aitimes_base_url))
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("AI타임스 대표기사 조회 실패: %s", exc)
        try:
            res = http.post(f"{kma_base_url}{KMA_LIST_PATH}", data=KMA_LIST_PARAMS)
            res.raise_for_status()
            extend(parse_kma_rows(res.json(), base_url=kma_base_url))
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("KMA 뉴스레터 목록 조회 실패: %s", exc)
    finally:
        if own_client:
            http.close()
    return results
