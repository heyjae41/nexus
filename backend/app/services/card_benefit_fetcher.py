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


def _ymd_period(start: date | None, end: date | None) -> str:
    """date 쌍 → 'YYYY.MM.DD ~ YYYY.MM.DD' (없는 쪽은 생략)."""
    return " ~ ".join(d.strftime("%Y.%m.%d") for d in (start, end) if d is not None)


def _split_dot_period(raw: str) -> tuple[date | None, date | None]:
    """'2026.07.01 ~ 2026.08.31' 형 문자열 → (시작, 종료)."""
    parts = [p.strip() for p in (raw or "").split("~")]
    start = _parse_dot_date(parts[0]) if parts else None
    end = _parse_dot_date(parts[1]) if len(parts) > 1 else None
    return start, end


def _sel_text(node, selector: str) -> str:
    """CSS 셀렉터 첫 매칭의 정규화 텍스트 (없으면 빈 문자열)."""
    el = node.select_one(selector)
    return el.get_text(" ", strip=True) if el else ""


def _img_src(node) -> str | None:
    """첫 <img> 의 src — 프로토콜 상대(//)면 https 로 절대화 (없으면 None)."""
    img = node.select_one("img")
    src = (img.get("src") or "").strip() if img else ""
    if src.startswith("//"):
        src = f"https:{src}"
    return src or None


def _issuer_client(base_url: str, **kwargs) -> httpx.Client:
    """카드사 공통 httpx 클라이언트 (모바일 UA, 리다이렉트 추적)."""
    kwargs.setdefault("timeout", 15)
    return httpx.Client(
        base_url=base_url, headers={"User-Agent": MOBILE_UA},
        follow_redirects=True, **kwargs,
    )


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
    r"\d[\d,.]*\s*(?:만|천)?\s*(?:원|%|퍼센트|달러|불|엔|하나머니|마일리지|마일|포인트)"
    r"|[$€¥]\s*\d[\d,.]*"
)
# 강한 혜택 신호(동사/1+1)는 단독으로도 인정, 약한 명사(쿠폰류)는 금액 동반 시에만 —
# '쿠폰 받고 예약하러 가기' 같은 CTA성 문구가 신호 하나로 통과하는 것을 막는다
_STRONG_BENEFIT_RE = re.compile(r"할인|적립|캐시백|증정|지급|무료|환급|1\s*\+\s*1")
_WEAK_BENEFIT_RE = re.compile(r"쿠폰|바우처|상품권")
_BENEFIT_VERB_RE = re.compile(
    r"할인|적립|캐시백|증정|지급|무료|환급|쿠폰|바우처|상품권|1\s*\+\s*1"
)
_CONDITION_RE = re.compile(r"(?:결제|이용|사용|구매|예약|충전|투숙)\s*시|이상\s*(?:결제|이용|사용|구매)")
# 행 시작의 안내성 문구만 배제한다 — 혜택 문장 중간의 '유의사항' 언급은 무해
_NOISE_RE = re.compile(
    r"^\s*(?:(?:이벤트\s*)?(?:기간|대상|응모\s*방법|참여\s*방법)\s*[::]"
    r"|유의\s*사항|자세한\s|※)"
)
# '○○ 결제 시 / 이상 시' 형태의 앞쪽 조건절 — 받는 혜택만 남기기 위해 걷어낸다
_LEADING_CONDITION_RE = re.compile(
    r"^.*(?:이상|결제|이용|사용|구매|예약|충전|투숙|매표|응모|가입)\s*시[,!]?\s+"
)
# 문장 '끝'의 이동 버튼성 문구만 제거 — 끝 앵커 없이 지우면 중간의
# '확인하기 쉬운 ...' 같은 표현 뒤 보상까지 삭제된다
_CTA_TAIL_RE = re.compile(
    r"(?:\s*(?:바로\s*가기|자세히\s*보기|확인하기|신청하기|응모하기|[▶»→]))+\s*$"
)
SUMMARY_MAX_LEN = 90  # 목록 카드 2줄 이내


def _extract_reward(text: str) -> str:
    """혜택 문장에서 '받는 것'만 남긴다 — 조건절('* ...', '○○ 시', 괄호)·CTA 꼬리 제거.

    조건을 걷어낸 뒤 보상 신호(금액/혜택어)가 남지 않으면 원문 핵심부를 유지한다.
    """
    core = re.split(r"\s*[*※]\s*", text)[0]
    core = re.sub(r"\([^)]*\)", " ", core)
    core = _CTA_TAIL_RE.sub("", core)
    core = re.sub(r"\s+", " ", core).strip(" ,·-(")
    match = _LEADING_CONDITION_RE.match(core)
    if match is None:
        return core
    prefix, rest = core[: match.end()], core[match.end():].strip(" ,·-(")
    # 걷어낼 앞부분에 이미 보상(금액+혜택동사)이 있으면 보상-선행 문장이므로 유지
    if _AMOUNT_RE.search(prefix) and _STRONG_BENEFIT_RE.search(prefix):
        return core
    if rest and (_AMOUNT_RE.search(rest) or _BENEFIT_VERB_RE.search(rest)):
        return rest
    return core


def _score_benefit_line(text: str) -> int:
    if _NOISE_RE.search(text):
        return 0
    score = 0
    has_amount = _AMOUNT_RE.search(text) is not None
    if _STRONG_BENEFIT_RE.search(text):
        score += 2
    if _CONDITION_RE.search(text):
        score += 2
    if not score and has_amount and _WEAK_BENEFIT_RE.search(text):
        score += 2  # 쿠폰류 명사는 금액이 함께 있을 때만
    # 금액은 혜택 신호와 함께일 때만 가점 —
    # '100% 당첨' 류 홍보 헤드라인이 % 하나로 통과하는 것을 막는다
    if score and has_amount:
        score += 3
    return score


def _select_benefit_lines(texts: list[str]) -> list[str]:
    """혜택 문장 후보를 점수순으로 고른다 (2점 미만 탈락, 중복 제거)."""
    scored: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for order, raw in enumerate(texts or []):
        text = re.sub(r"\s+", " ", (raw or "")).strip()
        norm = re.sub(r"\s", "", text)
        if not text or norm in seen:
            continue
        seen.add(norm)
        score = _score_benefit_line(text)
        if score >= 2:
            scored.append((score, order, text))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [text for _, _, text in scored]


def _pick_rewards(lines: list[str], limit: int = 2) -> list[str]:
    """선택된 문장들에서 보상 구절을 뽑아 중복 없이 limit 건 반환한다."""
    rewards: list[str] = []
    seen: set[str] = set()
    for text in lines:
        reward = _extract_reward(text)
        norm = re.sub(r"\s", "", reward)
        if not reward or norm in seen:
            continue
        seen.add(norm)
        rewards.append(reward)
        if len(rewards) == limit:
            break
    return rewards


def summarize_benefit_texts(texts: list[str]) -> str | None:
    """본문 문단들에서 '받는 혜택'(캐시백·할인·1+1 등)을 골라 최대 2건 요약한다.

    헤드라인/기간/유의사항 문구는 배제하고(점수: 혜택동사 2 + 이용조건 2 +
    동반 금액 3, 2점 미만 탈락), 선택된 문장에서 조건절을 걷어내 보상만 남긴다.
    """
    lines = _select_benefit_lines(texts)
    if not lines:
        return None
    rewards = _pick_rewards(lines)
    summary = " · ".join(rewards)
    if len(summary) > SUMMARY_MAX_LEN and len(rewards) > 1:
        summary = rewards[0]  # 두 번째 보상이 중간에서 잘리느니 하나만 온전히
    if len(summary) > SUMMARY_MAX_LEN:
        summary = summary[: SUMMARY_MAX_LEN - 1].rstrip() + "…"
    return summary or None


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
    client = client or _issuer_client(HANA_BASE)
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


# ---------------------------------------------------------------- KB국민카드

KB_BASE = "https://m.kbcard.com"
KB_TRAVEL_CATEGORIES = ("04", "05")  # 여행, 해외


@dataclass(frozen=True)
class BenefitDetail:
    """상세 페이지에서 보강하는 공통 필드 (KB/신한/현대/삼성)."""

    target_cards: str | None
    benefit_summary: str | None


def _parse_ymd(value) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%Y%m%d").date()
    except ValueError:
        return None


def parse_kb_list(data: dict) -> list[CardBenefitCandidate]:
    """MBBA0005 응답(evntList[])에서 이벤트 후보를 만든다."""
    out: list[CardBenefitCandidate] = []
    for it in data.get("evntList") or []:
        evnt_id = str(it.get("evntId") or "").strip()
        title = (it.get("evntTit") or "").strip()
        if not evnt_id or evnt_id == "None" or not title:
            continue
        start = _parse_ymd(it.get("evtStYmd"))
        end = _parse_ymd(it.get("evtEdYmd"))
        period = _ymd_period(start, end)
        image = (it.get("evntTmnlImgPthNm") or "").strip() or None
        out.append(
            CardBenefitCandidate(
                source_id=f"kb:{evnt_id}",
                card_company="KB국민카드",
                title=title,
                event_period=period,
                event_start_date=start,
                event_end_date=end,
                detail_url=f"{KB_BASE}/BON/DVIEW/MBBMCXHIABNC0026?evntSerno={evnt_id}",
                image_url=image,
            )
        )
    return out


def parse_kb_detail(html: str) -> BenefitDetail:
    """상세 HTML 의 h3 라벨(대상/내용) 섹션에서 대상카드·혜택 요약을 뽑는다.

    h3 구조가 없는 상세는 본문 문단 전체를 점수화해 혜택 문장을 찾는다."""
    soup = BeautifulSoup(html, "html.parser")
    sections: dict[str, str] = {}
    for h3 in soup.find_all("h3"):
        label = h3.get_text(strip=True)
        body = h3.find_next_sibling("p")
        if label and body is not None:
            sections.setdefault(label, body.get_text(" ", strip=True))
    target = sections.get("대상")
    if target:
        target = re.sub(r"\([^)]*\)", "", target).strip() or None

    content = sections.get("내용")
    if content:
        # 긴 안내문은 문장 단위로 쪼개 실질 혜택 문장을 고른다
        sentences = re.split(r"(?<=[.!?])\s+", content)
        summary = summarize_benefit_texts(sentences) or content
    else:
        texts = [el.get_text(" ", strip=True) for el in soup.find_all(["p", "li"])]
        summary = summarize_benefit_texts(texts)
    return BenefitDetail(target_cards=target, benefit_summary=summary)


def fetch_kb_candidates(
    client: httpx.Client | None = None,
    categories: tuple[str, ...] = KB_TRAVEL_CATEGORIES,
    max_pages: int = 10,
    with_details: bool = True,
) -> list[CardBenefitCandidate]:
    """KB국민카드 여행(04)·해외(05) 이벤트를 수집한다 (순수 HTTP)."""
    own = client is None
    client = client or _issuer_client(KB_BASE)
    try:
        candidates: list[CardBenefitCandidate] = []
        seen: set[str] = set()
        for category in categories:
            page, total_pages = 1, 1
            while page <= min(total_pages, max_pages):
                res = client.post(
                    "/BON/API/MBBA0005",
                    data={
                        # mblOsDtcd/osCode 는 모바일웹 노출분 필터 — 빼면 앱전용까지 과다수집
                        "mblOsDtcd": "02", "osCode": "I", "evntBonTag": "ALL",
                        "evtServieCgryCd": category, "evntStsDtcd": "A01",
                        "pageNo": page, "pageSize": 20,
                    },
                )
                res.raise_for_status()
                data = res.json()
                total_pages = int(data.get("totalPage") or 1)
                for c in parse_kb_list(data):
                    if c.source_id in seen:  # 여행/해외 양쪽에 걸린 이벤트
                        continue
                    seen.add(c.source_id)
                    candidates.append(c)
                page += 1

        if with_details:
            candidates = [
                _with_static_detail(client, c, parse_kb_detail, "KB국민카드")
                for c in candidates
            ]
        return candidates
    finally:
        if own:
            client.close()



# ---------------------------------------------------------------- 신한카드

SHINHAN_BASE = "https://www.shinhancard.com"
SHINHAN_LIST_JSON = "/mob/static/json/vendor/evnPgsList01.json"  # 진행중 전체
SHINHAN_TRAVEL_CATEGORY = "53"  # 여행·숙박 (mobWbBnfCagVl)


def _shinhan_item(it: dict) -> CardBenefitCandidate | None:
    rvn = str(it.get("mobWbEvtRvN") or "").strip()
    main = (it.get("mobWbEvtNm") or "").strip()
    detail_path = (it.get("hpgEvtDlPgeUrlAr") or "").strip()
    if not (rvn and main and detail_path):
        return None
    sub = (it.get("evtImgSlTilNm") or "").strip()
    image = (it.get("hpgEvtCtgImgUrlAr") or "").strip()
    start, end = _parse_ymd(it.get("mobWbEvtStd")), _parse_ymd(it.get("mobWbEvtEdd"))
    return CardBenefitCandidate(
        source_id=f"shinhan:{rvn}",
        card_company="신한카드",
        title=f"{sub} {main}".strip(),
        event_period=_ymd_period(start, end),
        event_start_date=start,
        event_end_date=end,
        detail_url=f"{SHINHAN_BASE}{detail_path}",
        image_url=f"{SHINHAN_BASE}{image}" if image else None,
    )


def parse_shinhan_list(
    data: dict, category: str = SHINHAN_TRAVEL_CATEGORY
) -> list[CardBenefitCandidate]:
    """evnPgsList01.json 에서 여행·숙박 카테고리 이벤트 후보를 만든다."""
    items = (data.get("root") or {}).get("evnlist") or []
    picked = (
        _shinhan_item(it) for it in items
        if (it.get("mobWbBnfCagVl") or "") == category
    )
    return [c for c in picked if c is not None]


def parse_shinhan_detail(html: str) -> BenefitDetail:
    """상세 HTML 의 h3 섹션(행사대상/행사내용)에서 대상카드·혜택 요약을 뽑는다."""
    soup = BeautifulSoup(html, "html.parser")
    sections: dict[str, str] = {}
    for h3 in soup.find_all("h3"):
        label = h3.get_text(strip=True).replace(" ", "")
        body = h3.find_next_sibling("p")
        if label and body is not None:
            sections.setdefault(label, body.get_text(" ", strip=True))
    target = sections.get("행사대상") or None
    content = sections.get("행사내용")
    if content:
        summary = summarize_benefit_texts(re.split(r"(?<=[.!?])\s+", content)) or content
    else:
        # 이벤트별 마크업 편차가 커서 섹션이 없으면 본문 전체를 점수화한다
        texts = [
            el.get_text(" ", strip=True)
            for el in soup.find_all(["h2", "p", "li", "dd"])
        ]
        summary = summarize_benefit_texts(texts)
    return BenefitDetail(target_cards=target, benefit_summary=summary)


def fetch_shinhan_candidates(
    client: httpx.Client | None = None,
    category: str = SHINHAN_TRAVEL_CATEGORY,
    with_details: bool = True,
) -> list[CardBenefitCandidate]:
    """신한카드 여행·숙박 이벤트를 수집한다 (정적 JSON + 정적 상세 HTML)."""
    own = client is None
    client = client or _issuer_client(SHINHAN_BASE)
    try:
        res = client.get(SHINHAN_LIST_JSON)
        res.raise_for_status()
        candidates = parse_shinhan_list(res.json(), category=category)
        if with_details:
            candidates = [
                _with_static_detail(client, c, parse_shinhan_detail, "신한카드")
                for c in candidates
            ]
        return candidates
    finally:
        if own:
            client.close()


# ---------------------------------------------------------------- 현대카드

HYUNDAI_BASE = "https://www.hyundaicard.com"
HYUNDAI_SEARCH_WORD = "여행"
_HYUNDAI_DATE_RE = re.compile(r"(?:(\d{4})\s*\.)?\s*(\d{1,2})\s*\.\s*(\d{1,2})")


def _hyundai_ssl_context():
    """현대카드 서버는 legacy TLS renegotiation 을 요구한다 (봇 차단 아님)."""
    import ssl

    ctx = ssl.create_default_context()
    ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
    return ctx


def _safe_date(year, month, day) -> date | None:
    """비정상 날짜(2월 30일 등)는 None — 한 항목 때문에 수집 전체가 죽지 않게."""
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def _parse_hyundai_period(raw: str) -> tuple[date | None, date | None]:
    """'2026. 1. 1 ~ 2026. 12. 31' (종료연도 생략 가능) → (시작, 종료)."""
    parts = raw.split("~")
    start = end = None
    matched = _HYUNDAI_DATE_RE.search(parts[0]) if parts else None
    if matched and matched.group(1):
        start = _safe_date(matched.group(1), matched.group(2), matched.group(3))
    if len(parts) > 1:
        matched = _HYUNDAI_DATE_RE.search(parts[1])
        if matched:
            year = int(matched.group(1)) if matched.group(1) else (
                start.year if start else None
            )
            if year:
                end = _safe_date(year, matched.group(2), matched.group(3))
    return start, end


def _hyundai_item(li) -> CardBenefitCandidate | None:
    from urllib.parse import quote

    code_match = re.search(
        r"bnftWebEvntCd=([A-Za-z0-9]+)|goDetail\('([A-Za-z0-9]+)'\)", li.decode()
    )
    code = (code_match.group(1) or code_match.group(2)) if code_match else None
    title = _sel_text(li, "h3")
    if not code or not title:
        return None
    raw_period = _sel_text(li, "p.p2_m_lt_1ln") or _sel_text(li, "p")
    start, end = _parse_hyundai_period(raw_period)
    img = li.select_one("img")
    src = (img.get("src") or "").strip() if img else ""
    return CardBenefitCandidate(
        source_id=f"hyundai:{code}",
        card_company="현대카드",
        title=title,
        event_period=_ymd_period(start, end) or raw_period,
        event_start_date=start,
        event_end_date=end,
        detail_url=f"{HYUNDAI_BASE}/cpb/ev/CPBEV0101_06.hc?bnftWebEvntCd={code}",
        # 파일명에 공백이 섞여 오므로 URL 인코딩해 절대화한다
        image_url=f"{HYUNDAI_BASE}{quote(src, safe='/:?=&%')}" if src else None,
    )


def parse_hyundai_list(html: str) -> list[CardBenefitCandidate]:
    """검색 결과 목록 HTML(ul#event_list1 > li)에서 이벤트 후보를 만든다."""
    soup = BeautifulSoup(html, "html.parser")
    items = (_hyundai_item(li) for li in soup.select("#event_list1 li"))
    return [c for c in items if c is not None]


def parse_hyundai_detail(html: str) -> BenefitDetail:
    """상세 div.content 인라인 텍스트에서 대상카드·혜택 요약을 뽑는다."""
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one("div.content")
    if content is None:
        return BenefitDetail(target_cards=None, benefit_summary=None)
    text = content.get_text("\n", strip=True)
    target_match = re.search(
        r"대상\s*카드\s*[::]?\s*(.+?)(?=\s*(?:이용\s*방법|유의|신청|대상\s*(?!카드)|$))",
        text, re.S,
    )
    target = None
    if target_match:
        target = re.sub(r"\s+", " ", target_match.group(1)).strip() or None
    lines = [re.sub(r"^(?:혜택|내용)\s+", "", ln) for ln in text.splitlines()]
    return BenefitDetail(
        target_cards=target, benefit_summary=summarize_benefit_texts(lines)
    )


def fetch_hyundai_candidates(
    client: httpx.Client | None = None,
    search_word: str = HYUNDAI_SEARCH_WORD,
    with_details: bool = True,
) -> list[CardBenefitCandidate]:
    """현대카드 여행 검색 이벤트를 수집한다 (legacy-TLS httpx, 목록은 서버렌더)."""
    own = client is None
    client = client or _issuer_client(HYUNDAI_BASE, timeout=25, verify=_hyundai_ssl_context())
    try:
        res = client.get(
            "/cpb/ev/CPBEV0101_01.hc",
            params={"evntCtgrVl": "", "searchWord": search_word},
        )
        res.raise_for_status()
        candidates = parse_hyundai_list(res.text)
        if with_details:
            candidates = [
                _with_static_detail(client, c, parse_hyundai_detail, "현대카드")
                for c in candidates
            ]
        return candidates
    finally:
        if own:
            client.close()


# ---------------------------------------------------------------- 삼성카드

SAMSUNG_BASE = "https://www.samsungcard.com"
_SAMSUNG_HL_RE = re.compile(r"<!HS>|<!HE>")


def _samsung_item(it: dict) -> CardBenefitCandidate | None:
    content_id = str(it.get("contentID") or "").strip()
    title = _SAMSUNG_HL_RE.sub("", (it.get("eventTitle") or "")).strip()
    if not content_id or not title:
        return None
    start = _parse_samsung_date(it.get("startDate"))
    end = _parse_samsung_date(it.get("endDate"))
    image = (it.get("imagePath") or "").strip()
    if image.startswith("//"):
        image = f"https:{image}"
    return CardBenefitCandidate(
        source_id=f"samsung:{content_id}",
        card_company="삼성카드",
        title=title,
        event_period=_ymd_period(start, end),
        event_start_date=start,
        event_end_date=end,
        detail_url=(
            f"{SAMSUNG_BASE}/personal/event/ing/UHPPBE1403M0.jsp?cms_id={content_id}"
        ),
        image_url=image or None,
    )


def parse_samsung_list(data: dict) -> list[CardBenefitCandidate]:
    """SHPPCO2107S01 검색 응답(evtRsList[])에서 진행중 이벤트 후보를 만든다."""
    items = (
        _samsung_item(it) for it in data.get("evtRsList") or []
        if (it.get("eventIngYN") or "") == "진행중"
    )
    return [c for c in items if c is not None]


def _parse_samsung_date(value) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%y.%m.%d").date()
    except ValueError:
        return None


def parse_samsung_detail(html: str) -> BenefitDetail:
    """상세의 dl.new_dl(dt/dd: 행사기간/대상카드/혜택)에서 보강 필드를 뽑는다."""
    soup = BeautifulSoup(html, "html.parser")
    sections: dict[str, str] = {}
    for dl in soup.select("dl.new_dl"):
        for dt in dl.find_all("dt"):
            dd = dt.find_next_sibling("dd")
            if dd is not None:
                sections.setdefault(
                    dt.get_text(strip=True).replace(" ", ""),
                    dd.get_text(" ", strip=True),
                )
    target = sections.get("대상카드")
    if target:
        target = re.sub(r"\([^)]*\)", "", target).strip() or None
    content = sections.get("혜택")
    summary = None
    if content:
        summary = summarize_benefit_texts(re.split(r"(?<=[.!?])\s+", content)) or content
    return BenefitDetail(target_cards=target, benefit_summary=summary)


def fetch_samsung_candidates(
    client: httpx.Client | None = None,
    query: str = "여행",
    max_pages: int = 10,
    with_details: bool = True,
    budget_seconds: float = 300,
) -> list[CardBenefitCandidate]:
    """삼성카드 여행 검색 이벤트를 수집한다.

    목록은 순수 HTTP(JSON 검색 API), 상세 혜택 본문은 세션 게이트라
    Playwright 로 상세 페이지를 렌더해 dl.new_dl 을 파싱한다."""
    own = client is None
    client = client or _issuer_client(SAMSUNG_BASE)
    try:
        candidates: list[CardBenefitCandidate] = []
        page, total = 1, 1
        while page <= max_pages and (page - 1) * 10 < total:
            res = client.post(
                "/frontservice/SHPPCO2107S01",
                json={
                    "query": query, "pageNum": page, "isTotalSearch": False,
                    "isMobile": False, "siteDivision": "personal",
                    "collection": "event", "onGoing": "0",
                    "common": {
                        "scrnId": "UHPPCO2112M0", "stdEtxtCrtSysNm": "M4615309",
                        "stdEtxtSn": "nexus", "stdEtxtPrgDvNo": 0,
                        "stdEtxtPrgNo": 0, "usid": "USERID0",
                    },
                },
            )
            res.raise_for_status()
            data = res.json()
            total = int(data.get("evtRsCount") or 0)
            if not data.get("evtRsList"):
                break  # 페이지 크기 가정(10)이 틀려도 빈 페이지에서 종료
            candidates += parse_samsung_list(data)
            page += 1
    finally:
        if own:
            client.close()

    if with_details and candidates:
        candidates = _samsung_enrich_details(candidates, budget_seconds)
    return candidates


def _samsung_enrich_details(
    candidates: list[CardBenefitCandidate], budget_seconds: float
) -> list[CardBenefitCandidate]:
    """Playwright 로 상세 페이지를 렌더해 대상카드·혜택을 보강한다 (시간 예산제)."""
    from playwright.sync_api import sync_playwright

    deadline = time.monotonic() + budget_seconds
    enriched: list[CardBenefitCandidate] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_context(user_agent=MOBILE_UA).new_page()
            for i, c in enumerate(candidates):
                if time.monotonic() > deadline:
                    logger.warning(
                        "삼성카드 상세 보강 시간 예산 초과 — %d/%d 에서 중단",
                        i, len(candidates),
                    )
                    enriched.extend(candidates[i:])
                    break
                enriched.append(_with_samsung_detail(page, c))
        finally:
            browser.close()
    return enriched


def _with_samsung_detail(page, c: CardBenefitCandidate) -> CardBenefitCandidate:
    try:
        page.goto(c.detail_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2500)
        return _apply_detail(c, parse_samsung_detail(page.content()))
    except Exception:  # noqa: BLE001 — 상세 보강 실패는 목록 정보로 폴백
        logger.warning("삼성카드 상세 조회 실패 — 목록 정보만 사용: %s", c.detail_url)
        return replace(c, benefit_tags=",".join(extract_benefit_tags(c.title)) or None)


# ---------------------------------------------------------------- 롯데카드

LOTTE_BASE = "https://m.lottecard.co.kr"
LOTTE_TRAVEL_TAB = "4"  # 레저·여행 (tabGubun=evnCtgSeq=4)


def _lotte_item(li) -> CardBenefitCandidate | None:
    """목록 Content HTML 의 <li> 하나 → 후보 (식별자/제목 없으면 None)."""
    id_match = re.search(
        r"\"cts_id\"\s*:\s*\"(\d+)\"|lnk_(\d+)|fnGoInqEvn\('[A-Z]',\s*'(\d+)'\)",
        li.decode(),
    )
    seq = next((g for g in (id_match.groups() if id_match else ()) if g), None)
    title = _sel_text(li, "strong.thumb-name")
    if not seq or not title:
        return None
    raw = _sel_text(li, "span.thumb-date")
    start, end = _split_dot_period(raw)
    src = _img_src(li)
    return CardBenefitCandidate(
        source_id=f"lotte:{seq}",
        card_company="롯데카드",
        title=title,
        event_period=_ymd_period(start, end) or raw,
        event_start_date=start,
        event_end_date=end,
        detail_url=f"{LOTTE_BASE}/app/LPBNFDA_V300.lc?evnBultSeq={seq}",
        image_url=src or None,
    )


def parse_lotte_list(payload: dict) -> list[CardBenefitCandidate]:
    """LPBNFDA_A100.lc 응답의 Content(HTML 조각)에서 이벤트 후보를 만든다."""
    content = payload.get("Content") or ""
    if not content.strip():
        return []
    soup = BeautifulSoup(content, "html.parser")
    items = (_lotte_item(li) for li in soup.find_all("li"))
    return [c for c in items if c is not None]


def parse_lotte_detail(html: str) -> BenefitDetail:
    """상세 HTML(.sub-content) 의 섹션 헤딩에서 대상카드·혜택 요약을 뽑는다."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one(".sub-content") or soup
    target = None
    for heading in body.select(".sub-title"):
        if "대상카드" in heading.get_text(strip=True).replace(" ", ""):
            para = heading.find_next_sibling("p")
            if para is not None:
                target = para.get_text(" ", strip=True) or None
            break
    texts = [el.get_text(" ", strip=True) for el in body.find_all(["p", "li", "dd"])]
    return BenefitDetail(
        target_cards=target, benefit_summary=summarize_benefit_texts(texts)
    )


def fetch_lotte_candidates(
    client: httpx.Client | None = None,
    tab: str = LOTTE_TRAVEL_TAB,
    max_pages: int = 10,
    with_details: bool = True,
) -> list[CardBenefitCandidate]:
    """롯데카드 레저·여행 이벤트를 수집한다 (순수 HTTP, HTML 조각 응답)."""
    own = client is None
    client = client or _issuer_client(LOTTE_BASE)
    try:
        candidates: list[CardBenefitCandidate] = []
        page, total_pages = 1, 1
        while page <= min(total_pages, max_pages):
            res = client.post(
                "/app/LPBNFDA_A100.lc",
                headers={"X-Requested-With": "XMLHttpRequest"},
                data={
                    "pageNo": page, "bigTabGubun": "2", "tabGubun": tab,
                    "evnBultSeq": "", "finishYn": "N", "sort": "LATEST",
                    "evnTc": "", "evnCtgSeq": tab, "isLogIn": "N",
                },
            )
            res.raise_for_status()
            payload = res.json()
            total_pages = int((payload.get("Param") or {}).get("totalPage") or 1)
            candidates += parse_lotte_list(payload)
            page += 1
        if with_details:
            candidates = [
                _with_static_detail(client, c, parse_lotte_detail, "롯데카드")
                for c in candidates
            ]
        return candidates
    finally:
        if own:
            client.close()


# ---------------------------------------------------------------- BC카드 (페이북)

BC_BASE = "https://web.paybooc.co.kr"
BC_TRAVEL_CATEGORY = "03"  # 여행/해외 (evntMrktTypCd) — 서버 미필터라 로컬 필터
_BC_EVENT_DATA_RE = re.compile(r"const\s+eventData\s*=\s*")


def _bc_title(it: dict) -> str:
    parts = ((it.get(f"pybcUnifEvntNm{i}") or "").strip() for i in (1, 2, 3))
    return " ".join(p for p in parts if p)


def _bc_item(it: dict) -> CardBenefitCandidate | None:
    no = str(it.get("pybcUnifEvntNo") or "").strip()
    title = _bc_title(it)
    if not no or not title:
        return None
    start = _parse_ymd(str(it.get("evntBltnStrtDtm") or "")[:8])
    end = _parse_ymd(str(it.get("evntBltnEndDtm") or "")[:8])
    return CardBenefitCandidate(
        source_id=f"bc:{no}",
        card_company="BC카드",
        title=title,
        event_period=_ymd_period(start, end),
        event_start_date=start,
        event_end_date=end,
        detail_url=f"{BC_BASE}/web/evnt/evnt-dts?pybcUnifEvntNo={no}",
        image_url=(it.get("evntBsImgUrlAddr") or "").strip() or None,
    )


def parse_bc_list(payload: dict, category: str = BC_TRAVEL_CATEGORY) -> list[CardBenefitCandidate]:
    """lst-evnt-data 응답에서 여행/해외 카테고리 이벤트 후보를 만든다."""
    items = (payload.get("data") or {}).get("evntInqrList") or []
    picked = (
        _bc_item(it) for it in items if (it.get("evntMrktTypCd") or "") == category
    )
    return [c for c in picked if c is not None]


def parse_bc_detail(html: str) -> BenefitDetail:
    """상세 페이지에 임베드된 eventData JSON 의 그룹(혜택/대상카드)을 파싱한다."""
    match = _BC_EVENT_DATA_RE.search(html or "")
    if not match:
        return BenefitDetail(target_cards=None, benefit_summary=None)
    try:
        # raw_decode 로 JSON 의 정확한 끝을 찾는다 (개행/후속 코드에 견고)
        data, _ = json.JSONDecoder().raw_decode(html[match.end():])
    except ValueError:
        return BenefitDetail(target_cards=None, benefit_summary=None)

    target = None
    benefit_texts: list[str] = []
    for group in data.get("eventDetailsGroupBaseDtoList") or []:
        name = (group.get("evntDtGrpNm") or "").replace(" ", "")
        texts = _bc_group_texts(group)
        if name == "대상카드" and texts:
            target = texts[0]
        elif name == "혜택":
            benefit_texts += texts
    return BenefitDetail(
        target_cards=target, benefit_summary=summarize_benefit_texts(benefit_texts)
    )


def _bc_group_texts(group: dict) -> list[str]:
    """그룹 콘텐츠(제목+본문 HTML)를 평문 리스트로 펼친다."""
    contents = group.get("eventDetailGroupContentDtoList") or []
    fields = (
        value
        for c in contents
        for value in (c.get("cntnTitlNm"), c.get("cntnDtCtnt"))
    )
    cleaned = (_clean_summary(v) for v in fields)
    return [t for t in cleaned if t]


def fetch_bc_candidates(
    client: httpx.Client | None = None,
    category: str = BC_TRAVEL_CATEGORY,
    with_details: bool = True,
) -> list[CardBenefitCandidate]:
    """BC카드(페이북) 여행/해외 이벤트를 수집한다 (순수 HTTP).

    목록 API 는 카테고리 파라미터를 무시하고 진행중 전체를 반환하므로 로컬 필터."""
    own = client is None
    client = client or _issuer_client(BC_BASE)
    try:
        res = client.get(
            "/web/evnt/lst-evnt-data",
            params={
                "reqType": "init", "inqrDv": "ING", "pgeNo": 1, "pgeCnt": 20,
                "evntMrktTypCd": "", "ordering": "RECENT",
            },
            headers={"Referer": f"{BC_BASE}/web/evnt/main"},
        )
        res.raise_for_status()
        candidates = parse_bc_list(res.json(), category=category)
        if with_details:
            candidates = [
                _with_static_detail(client, c, parse_bc_detail, "BC카드")
                for c in candidates
            ]
        return candidates
    finally:
        if own:
            client.close()


# ------------------------------------------------------------ 공용 상세 보강


def _apply_detail(c: CardBenefitCandidate, detail: BenefitDetail) -> CardBenefitCandidate:
    """상세에서 얻은 대상카드·요약을 후보에 반영하고 혜택 태그를 재계산한다."""
    tags = extract_benefit_tags(f"{c.title} {detail.benefit_summary or ''}")
    return replace(
        c, target_cards=detail.target_cards or c.target_cards,
        benefit_summary=detail.benefit_summary or c.benefit_summary,
        benefit_tags=",".join(tags) or None,
    )


def _with_static_detail(
    client: httpx.Client, c: CardBenefitCandidate, parser, label: str
) -> CardBenefitCandidate:
    """정적 HTML 상세를 GET 해 대상카드·혜택 요약을 보강한다 (실패해도 목록 유지)."""
    try:
        res = client.get(c.detail_url)
        res.raise_for_status()
        return _apply_detail(c, parser(res.text))
    except Exception:  # noqa: BLE001 — 스펙과 다른 마크업의 파서 예외도 한 건만 폴백
        logger.warning("%s 상세 조회 실패 — 목록 정보만 사용: %s", label, c.detail_url)
        return replace(c, benefit_tags=",".join(extract_benefit_tags(c.title)) or None)


# 카드사별 fetcher 레지스트리 — 스케줄러와 수동 트리거(internal)가 공유한다.
# 새 카드사 추가 시 여기에만 등록하면 수집 경로 전체에 반영된다.
ISSUER_FETCHERS = {
    "hana": fetch_hana_candidates,
    "woori": fetch_woori_candidates,
    "kb": fetch_kb_candidates,
    "hyundai": fetch_hyundai_candidates,
    "samsung": fetch_samsung_candidates,
    "shinhan": fetch_shinhan_candidates,
    "lotte": fetch_lotte_candidates,
    "bc": fetch_bc_candidates,
}
