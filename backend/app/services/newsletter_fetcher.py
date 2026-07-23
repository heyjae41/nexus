"""뉴스레터 목록 페이지에서 신규 발행분 후보를 추출한다.

- 스티비 아카이브: page.stibee.com/archives/{listId}/emails 가 발행 이력 JSON 을 반환한다.
  상세 이동 URL 은 각 항목의 permanentLink(stib.ee 단축 주소)다.
- KMA 인사이트 뉴스레터: /kr/usrs/eduRegMgnt/selectInsightSubList.do POST 가
  게시판 rows JSON 을 반환한다. 상세 URL 은 formDetail 파라미터로 조립한다.
"""
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

FETCH_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NexusBot/1.0)"}
KST = timezone(timedelta(hours=9))

# 스티비 개인화 병합태그 ($%name%$ 등) — 미리보기 텍스트에서 제거한다
MERGE_TAG_RE = re.compile(r"\$%[^%$]*%\$")

KMA_LIST_PATH = "/kr/usrs/eduRegMgnt/selectInsightSubList.do"
KMA_DETAIL_PATH = "/kr/usrs/eduRegMgnt/eduRegMgntForm.do"
# 목록 페이지 formList/formDetail hidden 필드와 동일한 값
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
        return datetime.fromisoformat(value)
    except ValueError:
        return None


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


def _kma_publisher(metatext) -> str:
    series = " ".join(part.strip() for part in (metatext or "").split(",") if part.strip())
    return f"KMA {series}" if series else "KMA 뉴스레터"


def parse_kma_rows(payload: dict, base_url: str) -> list[NewsletterCandidate]:
    candidates = []
    for row in (payload or {}).get("rows") or []:
        seq = row.get("BRD_SEQ")
        title = (row.get("TTL") or "").strip()
        if not (seq and title):
            continue
        filename = (row.get("SAVE_FILENM") or "").strip()
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


def fetch_newsletter_candidates(
    *,
    stibee_pairs: list[tuple[str, str]],
    stibee_base_url: str = "https://page.stibee.com",
    kma_base_url: str = "https://www.kma.or.kr",
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
            res = http.post(f"{kma_base_url}{KMA_LIST_PATH}", data=KMA_LIST_PARAMS)
            res.raise_for_status()
            extend(parse_kma_rows(res.json(), base_url=kma_base_url))
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("KMA 뉴스레터 목록 조회 실패: %s", exc)
    finally:
        if own_client:
            http.close()
    return results
