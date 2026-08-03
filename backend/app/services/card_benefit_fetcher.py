"""Card.Pick — 카드사 해외여행 혜택 이벤트 fetcher.

- 하나카드: MKEVT1000M.ajax (POST, EUC-KR JSON) 목록 + MKEVT1010M.web 상세 HTML.
  순수 HTTP 로 접근 가능해 httpx 를 쓴다.
- 우리카드: F5 anti-bot(TS* 쿠키) 뒤에 있어 순수 HTTP 재현이 불가 —
  Playwright 로 목록 페이지를 연 뒤 페이지 컨텍스트 fetch 로
  getPrgEvntList/getPrgEvntDtl.pwkjson 을 호출한다.

파싱은 전부 순수 함수로 분리해 단위 테스트한다. 네트워크 실패는 호출부
(스케줄러/internal API)가 처리하도록 예외를 전파한다.
"""
import html as html_lib
import json
import logging
import re
import time
from dataclasses import dataclass, replace
from datetime import date, datetime

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HANA_BASE = "https://m.hanacard.co.kr"
HANA_TRAVEL_CATEGORY = "00102"  # 여행/해외
WOORI_BASE = "https://m.wooricard.com"
WOORI_LIST_PAGE = f"{WOORI_BASE}/dcmw/yh1/bnf/bnf02/prgevnt/M1BNF202S00.do"
WOORI_TRAVEL_CATEGORY = "E000003"  # 여행/해외

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

# 혜택 유형 태그 — 제목/상세 텍스트에서 추출한다
BENEFIT_KEYWORDS = (
    "할인", "캐시백", "적립", "무료", "1+1", "쿠폰", "경품", "면세",
    "라운지", "바우처", "증정", "환급",
)


@dataclass(frozen=True)
class CardBenefitCandidate:
    source_id: str
    card_company: str
    title: str
    event_period: str
    event_start_date: date | None
    event_end_date: date | None
    detail_url: str
    image_url: str | None
    target_cards: str | None = None
    benefit_summary: str | None = None
    benefit_tags: str | None = None


def _parse_dot_date(value) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%Y.%m.%d").date()
    except ValueError:
        return None


def _period(sdt, edt) -> str:
    sdt = (sdt or "").strip()
    edt = (edt or "").strip()
    return f"{sdt} ~ {edt}".strip(" ~") if (sdt or edt) else ""


def extract_benefit_tags(text: str | None) -> list[str]:
    if not text:
        return []
    return [kw for kw in BENEFIT_KEYWORDS if kw in text]


def _clean_summary(raw: str | None) -> str | None:
    """HTML 이스케이프·태그·개행이 섞인 요약 원문을 한 줄 평문으로 정리한다."""
    if not raw:
        return None
    text = BeautifulSoup(html_lib.unescape(raw), "html.parser").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


# '얼마 쓰면 얼마 받는다' 요약 추출 — 금액·혜택동사·이용조건 패턴 점수화
_AMOUNT_RE = re.compile(
    r"\d[\d,.]*\s*(?:만|천)?\s*(?:원|%|퍼센트|하나머니|마일리지|마일|포인트)"
)
_BENEFIT_VERB_RE = re.compile(r"할인|적립|캐시백|증정|지급|무료|환급")
_CONDITION_RE = re.compile(r"(?:결제|이용|사용|구매|예약|충전|투숙)\s*시|이상\s*(?:결제|이용|사용|구매)")
_NOISE_RE = re.compile(
    r"^\s*(?:이벤트\s*)?(?:기간|대상|응모\s*방법|참여\s*방법)\s*[::]"
    r"|유의\s*사항|자세한\s.*(?:확인|안내)"
)
SUMMARY_MAX_LEN = 160


def _score_benefit_line(text: str) -> int:
    if _NOISE_RE.search(text):
        return 0
    score = 0
    if _AMOUNT_RE.search(text):
        score += 3
    if _BENEFIT_VERB_RE.search(text):
        score += 2
    if _CONDITION_RE.search(text):
        score += 2
    return score


def summarize_benefit_texts(texts: list[str]) -> str | None:
    """본문 문단들에서 실질 혜택 문장(금액·조건 포함)을 골라 최대 2건 요약한다.

    헤드라인/기간/유의사항 문구는 배제하고, '얼마 쓰면 얼마 받는다' 형태를
    우선한다 (점수: 금액 3 + 혜택동사 2 + 이용조건 2, 2점 미만 탈락).
    """
    scored: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for order, raw in enumerate(texts or []):
        text = re.sub(r"\s+", " ", (raw or "")).strip()
        if not text:
            continue
        norm = re.sub(r"\s", "", text)
        if norm in seen:
            continue
        seen.add(norm)
        score = _score_benefit_line(text)
        if score >= 2:
            scored.append((score, order, text))

    if not scored:
        return None
    scored.sort(key=lambda item: (-item[0], item[1]))
    summary = " · ".join(text for _, _, text in scored[:2])
    if len(summary) > SUMMARY_MAX_LEN:
        summary = summary[: SUMMARY_MAX_LEN - 1].rstrip() + "…"
    return summary


# ---------------------------------------------------------------- 하나카드

def parse_hana_list(data: dict) -> list[CardBenefitCandidate]:
    """MKEVT1000M.ajax 응답(DATA)에서 이벤트 후보를 만든다."""
    items = (data.get("eventListMap") or {}).get("list") or []
    out: list[CardBenefitCandidate] = []
    for it in items:
        # EVN_SEQ 는 문자열/숫자 어느 쪽으로 와도 수용한다
        seq = str(it.get("EVN_SEQ") or "").strip()
        title = (it.get("EVN_TIT_NM") or "").strip()
        if not seq or not title:
            continue
        image = it.get("APN_FILE_NM")
        out.append(
            CardBenefitCandidate(
                source_id=f"hana:{seq}",
                card_company="하나카드",
                title=title,
                event_period=_period(it.get("EVN_SDT"), it.get("EVN_EDT")),
                event_start_date=_parse_dot_date(it.get("EVN_SDT")),
                event_end_date=_parse_dot_date(it.get("EVN_EDT")),
                detail_url=f"{HANA_BASE}/MKEVT1010M.web?EVN_SEQ={seq}",
                image_url=f"{HANA_BASE}{image}" if image else None,
                benefit_summary=_clean_summary(it.get("ADD_VAR5")),
            )
        )
    return out


def parse_hana_detail_target_cards(html_or_soup) -> str | None:
    """상세 HTML 의 '대상카드' 섹션 텍스트를 추출한다 (없으면 None)."""
    soup = _as_soup(html_or_soup)
    for heading in soup.find_all(["h2", "h3"]):
        if "대상카드" in heading.get_text(strip=True).replace(" ", ""):
            body = heading.find_next_sibling("p")
            if body is not None:
                return body.get_text(" ", strip=True) or None
    return None


def parse_hana_detail_benefit_summary(html_or_soup) -> str | None:
    """상세 본문에서 실질 혜택 문장('얼마 쓰면 얼마 받는다')을 골라 요약한다.

    반드시 이벤트 본문 컨테이너(.wcms-data/.event-data)를 먼저 잡는다 —
    .page-contents 는 GNB 메뉴 레이어에도 붙어 있어 공통 배너가 오염된다.
    """
    soup = _as_soup(html_or_soup)
    body = soup.select_one(".wcms-data") or soup.select_one(".event-data") or soup
    texts = [el.get_text(" ", strip=True) for el in body.select("p.txt-cont, li")]
    return summarize_benefit_texts(texts)


def _as_soup(html_or_soup) -> BeautifulSoup:
    if isinstance(html_or_soup, BeautifulSoup):
        return html_or_soup
    return BeautifulSoup(html_or_soup, "html.parser")


def fetch_hana_candidates(
    client: httpx.Client | None = None,
    category: str = HANA_TRAVEL_CATEGORY,
    max_pages: int = 10,
    with_details: bool = True,
) -> list[CardBenefitCandidate]:
    """하나카드 여행/해외 이벤트 전체 페이지를 수집한다."""
    own = client is None
    client = client or httpx.Client(
        base_url=HANA_BASE, headers={"User-Agent": MOBILE_UA}, timeout=15,
        follow_redirects=True,
    )
    try:
        candidates: list[CardBenefitCandidate] = []
        page, total_pages = 1, 1
        while page <= min(total_pages, max_pages):
            res = client.post(
                "/MKEVT1000M.ajax",
                data={"page": page, "evnCate": category},
                headers={"Referer": f"{HANA_BASE}/MKEVT1000M.web"},
            )
            res.raise_for_status()
            payload = json.loads(res.content.decode("euc-kr", errors="replace"))
            data = payload.get("DATA") or {}
            total_pages = int((data.get("eventListMap") or {}).get("totalPage") or 1)
            candidates += parse_hana_list(data)
            page += 1

        if with_details:
            candidates = [
                _with_hana_detail(client, c) for c in candidates
            ]
        return candidates
    finally:
        if own:
            client.close()


def _with_hana_detail(client: httpx.Client, c: CardBenefitCandidate) -> CardBenefitCandidate:
    """상세 페이지에서 대상카드·혜택 태그를 보강한다 (실패해도 목록 정보는 유지)."""
    try:
        res = client.get(c.detail_url)
        res.raise_for_status()
        soup = BeautifulSoup(res.content.decode("euc-kr", errors="replace"), "html.parser")
        target = parse_hana_detail_target_cards(soup)
        summary = parse_hana_detail_benefit_summary(soup) or c.benefit_summary
        # 공통 네비/푸터의 키워드 오탐을 막기 위해 이벤트 본문 영역만 본다
        body = soup.select_one(".page-contents, .contents-wrap, .event-detail") or soup
        text = body.get_text(" ", strip=True)
        tags = extract_benefit_tags(f"{c.title} {text[:3000]}")
        return replace(
            c, target_cards=target, benefit_summary=summary,
            benefit_tags=",".join(tags) or None,
        )
    except httpx.HTTPError:
        logger.warning("하나카드 상세 조회 실패 — 목록 정보만 사용: %s", c.detail_url)
        return replace(c, benefit_tags=",".join(extract_benefit_tags(c.title)) or None)


# ---------------------------------------------------------------- 우리카드

def parse_woori_list(data: dict) -> list[CardBenefitCandidate]:
    """getPrgEvntList.pwkjson 응답에서 이벤트 후보를 만든다."""
    out: list[CardBenefitCandidate] = []
    for it in data.get("prgEvntList") or []:
        srno = str(it.get("evntSrno") or "").strip()
        title = (it.get("cardEvntNm") or "").strip()
        if not srno or not title:
            continue
        image = it.get("fileCoursWeb")
        out.append(
            CardBenefitCandidate(
                source_id=f"woori:{srno}",
                card_company="우리카드",
                title=title,
                event_period=_period(it.get("evntSdt"), it.get("evntEdt")),
                event_start_date=_parse_dot_date(it.get("evntSdt")),
                event_end_date=_parse_dot_date(it.get("evntEdt")),
                detail_url=(
                    f"{WOORI_BASE}/dcmw/yh1/bnf/bnf02/prgevnt/movePrgEvntDtl.do"
                    f"?evntSrno={srno}"
                ),
                image_url=f"{WOORI_BASE}{image}" if image else None,
                benefit_summary=_clean_summary(
                    it.get("evntSumTxt") or it.get("mblEvntSumTxt")
                ),
            )
        )
    return out


def parse_woori_detail_target_cards(cms_contents: str | None) -> str | None:
    """getPrgEvntDtl 의 pcCmsCntnts(HTML 이스케이프 본문)에서 대상 카드를 추출한다."""
    if not cms_contents:
        return None
    soup = BeautifulSoup(html_lib.unescape(cms_contents), "html.parser")
    for dt in soup.find_all("dt"):
        if "대상카드" in dt.get_text(strip=True).replace(" ", ""):
            dd = dt.find_next_sibling("dd")
            if dd is not None:
                return dd.get_text(" ", strip=True) or None
    return None


def woori_detail_text(cms_contents: str | None) -> str:
    """혜택 태그 추출용 상세 본문 평문."""
    if not cms_contents:
        return ""
    return BeautifulSoup(html_lib.unescape(cms_contents), "html.parser").get_text(
        " ", strip=True
    )


def parse_woori_detail_benefit_summary(cms_contents: str | None) -> str | None:
    """pcCmsCntnts(HTML 이스케이프 본문)에서 실질 혜택 문장을 골라 요약한다."""
    if not cms_contents:
        return None
    soup = BeautifulSoup(html_lib.unescape(cms_contents), "html.parser")
    elements = soup.find_all(["p", "dd", "li"])
    texts = [el.get_text(" ", strip=True) for el in elements]
    if not texts:
        texts = [soup.get_text(" ", strip=True)]
    return summarize_benefit_texts(texts)


_WOORI_FETCH_JS = """
async ({ url, body }) => {
  const r = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      'Accept': 'application/json',
    },
    body: JSON.stringify(body),
  });
  return r.json();
}
"""


def fetch_woori_candidates(
    category: str = WOORI_TRAVEL_CATEGORY,
    max_pages: int = 10,
    with_details: bool = True,
    page_timeout_ms: int = 45000,
    budget_seconds: float = 300,
) -> list[CardBenefitCandidate]:
    """우리카드 여행/해외 이벤트를 Playwright 페이지 컨텍스트에서 수집한다.

    목록 페이지를 실제로 로드해 anti-bot 쿠키를 획득한 뒤, 같은 페이지에서
    fetch 로 pwkjson API 를 호출한다 (더보기 = pageIndex 증가와 동일).
    budget_seconds 를 넘기면 남은 상세 보강을 중단하고 수집분만 반환한다 —
    외부 사이트 지연이 스케줄러 스레드를 무한정 붙잡지 않게 하기 위함이다.
    """
    from playwright.sync_api import sync_playwright

    deadline = time.monotonic() + budget_seconds
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_context(user_agent=MOBILE_UA).new_page()
            page.goto(WOORI_LIST_PAGE, wait_until="domcontentloaded",
                      timeout=page_timeout_ms)
            page.wait_for_timeout(6000)  # anti-bot 쿠키 발급 대기

            def post(url: str, body: dict) -> dict:
                return page.evaluate(_WOORI_FETCH_JS, {"url": url, "body": body})

            candidates = _woori_collect_pages(post, category, max_pages, deadline)
            if with_details:
                enriched = []
                for i, c in enumerate(candidates):
                    if time.monotonic() > deadline:
                        logger.warning(
                            "우리카드 수집 시간 예산 초과 — 상세 보강 %d/%d 에서 중단",
                            i, len(candidates),
                        )
                        enriched.extend(candidates[i:])
                        break
                    enriched.append(_with_woori_detail(post, c))
                candidates = enriched
            return candidates
        finally:
            browser.close()


def _woori_collect_pages(
    post, category: str, max_pages: int, deadline: float
) -> list[CardBenefitCandidate]:
    candidates: list[CardBenefitCandidate] = []
    page_no, total_pages = 1, 1
    while page_no <= min(total_pages, max_pages) and time.monotonic() <= deadline:
        data = post(
            "/dcmw/yh1/bnf/bnf02/prgevnt/getPrgEvntList.pwkjson",
            {"bnf02PrgEvntVo": {
                "evntCtgrNo": category, "searchKwrd": "",
                "sortOrd": "orderNew", "favYn": "D",
                "pageIndex": str(page_no), "pageSize": "20",
                "evntItgCfcd": "",
            }},
        )
        if not (data.get("elHeader") or {}).get("resSuc"):
            raise RuntimeError(
                f"우리카드 목록 API 실패: {(data.get('elHeader') or {}).get('resCode')}"
            )
        items = data.get("prgEvntList") or []
        if not items:
            break
        total_pages = int(items[0].get("totalPageCount") or 1)
        candidates += parse_woori_list(data)
        page_no += 1
    return candidates


def _with_woori_detail(post, c: CardBenefitCandidate) -> CardBenefitCandidate:
    """상세 API 로 대상카드·혜택 태그를 보강한다 (실패해도 목록 정보는 유지)."""
    srno = c.source_id.split(":", 1)[1]
    try:
        data = post(
            "/dcmw/yh1/bnf/bnf02/prgevnt/getPrgEvntDtl.pwkjson",
            {"bnf02PrgEvntVo": {"evntSrno": srno}},
        )
        rows = data.get("prgEvntDtl") or []
        cms = rows[0].get("pcCmsCntnts") if rows else None
        target = parse_woori_detail_target_cards(cms)
        # 상세 본문의 실질 혜택 문장이 목록 요약(evntSumTxt, 홍보 문구)보다 우선
        summary = parse_woori_detail_benefit_summary(cms) or c.benefit_summary
        tags = extract_benefit_tags(f"{c.title} {woori_detail_text(cms)[:3000]}")
        return replace(
            c, target_cards=target, benefit_summary=summary,
            benefit_tags=",".join(tags) or None,
        )
    except Exception:  # noqa: BLE001 — 상세 보강 실패는 목록 정보로 폴백
        logger.warning("우리카드 상세 조회 실패 — 목록 정보만 사용: %s", c.detail_url)
        return replace(c, benefit_tags=",".join(extract_benefit_tags(c.title)) or None)
