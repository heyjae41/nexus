"""Card.Pick 카드사 여행 혜택 수집 — 파서 단위 테스트.

- 하나카드: MKEVT1000M.ajax(EUC-KR JSON) 목록 + MKEVT1010M.web 상세 HTML
- 우리카드: getPrgEvntList.pwkjson 목록 + getPrgEvntDtl.pwkjson 의 pcCmsCntnts(HTML 이스케이프)
파서는 순수 함수로 두고 네트워크/브라우저는 fetch 계층에서만 다룬다.
"""
from datetime import date

from app.services.card_benefit_fetcher import (
    extract_benefit_tags,
    parse_hana_detail_benefit_summary,
    parse_hana_detail_target_cards,
    parse_hana_list,
    parse_woori_detail_benefit_summary,
    parse_woori_detail_target_cards,
    parse_woori_list,
    summarize_benefit_texts,
)

HANA_LIST_DATA = {
    "eventListMap": {
        "totalCount": 2,
        "totalPage": 1,
        "list": [
            {
                "EVN_SEQ": "60480",
                "EVN_TIT_NM": "해외 결제하면 최대 10만 하나머니!",
                "EVN_SDT": "2026.08.01",
                "EVN_EDT": "2026.09.30",
                "APN_FILE_NM": "/ATTACH/MKA/images/event/sum_card_m_60028_1.png",
                "EVN_CATE": "00102",
                "ADD_VAR5": "온·오프라인 여행혜택",
            },
            {
                "EVN_SEQ": "60479",
                "EVN_TIT_NM": "Travel bucket reward 여행비 돌려받기",
                "EVN_SDT": "2026.08.01",
                "EVN_EDT": "2026.09.15",
                "APN_FILE_NM": None,
                "EVN_CATE": "00102",
            },
        ],
    }
}


def test_parse_hana_list_builds_candidates():
    items = parse_hana_list(HANA_LIST_DATA)

    assert len(items) == 2
    first = items[0]
    assert first.card_company == "하나카드"
    assert first.source_id == "hana:60480"
    assert first.title == "해외 결제하면 최대 10만 하나머니!"
    assert first.event_period == "2026.08.01 ~ 2026.09.30"
    assert first.event_start_date == date(2026, 8, 1)
    assert first.event_end_date == date(2026, 9, 30)
    assert first.detail_url == "https://m.hanacard.co.kr/MKEVT1010M.web?EVN_SEQ=60480"
    assert first.image_url == (
        "https://m.hanacard.co.kr/ATTACH/MKA/images/event/sum_card_m_60028_1.png"
    )
    # 목록 단계 요약: ADD_VAR5 (상세 파싱 성공 시 더 구체적인 문장으로 대체된다)
    assert first.benefit_summary == "온·오프라인 여행혜택"
    # 이미지 없는 항목은 None
    assert items[1].image_url is None
    assert items[1].benefit_summary is None


def test_parse_hana_list_tolerates_numeric_seq():
    """EVN_SEQ 가 숫자(JSON number)로 와도 전체 파싱이 죽지 않는다."""
    data = {"eventListMap": {"list": [
        {"EVN_SEQ": 60480, "EVN_TIT_NM": "숫자 시퀀스", "EVN_SDT": "2026.08.01"},
    ]}}
    items = parse_hana_list(data)
    assert len(items) == 1
    assert items[0].source_id == "hana:60480"


def test_parse_hana_list_tolerates_missing_fields():
    assert parse_hana_list({}) == []
    assert parse_hana_list({"eventListMap": {"list": [{"EVN_SEQ": None}]}}) == []
    # 제목 없는 항목은 건너뛴다
    data = {"eventListMap": {"list": [{"EVN_SEQ": "1", "EVN_TIT_NM": ""}]}}
    assert parse_hana_list(data) == []


HANA_DETAIL_HTML = """
<html><body>
<section class="eVgroup-first"><h2 class="tit-round">혜택</h2>
<div class="txt-box">
<p class="txt-cont"><span>응모 후 대상카드로</span> <b>해외 온/오프라인 가맹점 결제 시<br>최대 10만 하나머니 적립</b></p>
</div></section>
<section class="eVgroup"><h2 class="tit-round">혜택 제공일</h2>
<p class="txt-cont"><b>2026. 10. 31 이내</b></p></section>
<section class="eVgroup"><h2 class="tit-round">대상카드</h2>
<p class="txt-cont"><b>JADE First Centum, JADE First<br>JADE Prime, JADE Classic<br>(Visa 브랜드)</b></p>
</section>
</body></html>
"""


def test_parse_hana_detail_benefit_summary():
    summary = parse_hana_detail_benefit_summary(HANA_DETAIL_HTML)
    # '응모 후 ... 결제 시' 조건절을 걷어내고 받는 혜택만 남긴다
    assert summary == "최대 10만 하나머니 적립"


def test_parse_hana_detail_summary_ignores_gnb_banner():
    """GNB 메뉴 레이어(.page-contents)의 공통 배너는 요약 후보에서 배제한다."""
    html = """
    <div class="layer-wrap page-contents">
      <ul><li>100% 당첨 랜덤박스</li><li>트래블로그 적립챌린지</li></ul>
    </div>
    <div class="wcms-data">
      <ul><li>VIA 100만원 할인쿠폰 * 1,000만원 이상 전액 결제 시</li></ul>
    </div>
    """
    summary = parse_hana_detail_benefit_summary(html)
    assert "100만원 할인쿠폰" in summary
    assert "랜덤박스" not in summary


def test_parse_hana_detail_benefit_summary_missing_returns_none():
    assert parse_hana_detail_benefit_summary("<html><body>없음</body></html>") is None


def test_parse_hana_detail_target_cards():
    cards = parse_hana_detail_target_cards(HANA_DETAIL_HTML)
    assert cards == "JADE First Centum, JADE First JADE Prime, JADE Classic (Visa 브랜드)"


def test_parse_hana_detail_without_section_returns_none():
    assert parse_hana_detail_target_cards("<html><body>내용 없음</body></html>") is None


WOORI_LIST = [
    {
        "evntSrno": "30006146",
        "cardEvntNm": "WON트래블 호텔 최대 25% 할인",
        "evntSdt": "2026.08.01",
        "evntEdt": "2026.08.31",
        "fileCoursWeb": "/webcontent/evntFileList/2026/7/31/bc158914.png",
        "hiEvntCtgrNo": "E000003,E000003,E000003",
        "evntSumTxt": "호텔 예약은 WON트래블에서!&lt;br&gt;\r\n쿠폰 추가할인까지 받아보세요\r\n",
        "totalPageCount": 3,
        "totCnt": 29,
    },
    {
        "evntSrno": "30005390",
        "cardEvntNm": "분할납부 이용해서 해외 여행 부담없이 다녀오세요",
        "evntSdt": "2026.02.24",
        "evntEdt": "2026.12.31",
        "fileCoursWeb": None,
        "hiEvntCtgrNo": "E000003",
    },
]


def test_parse_woori_list_builds_candidates():
    items = parse_woori_list({"prgEvntList": WOORI_LIST})

    assert len(items) == 2
    first = items[0]
    assert first.card_company == "우리카드"
    assert first.source_id == "woori:30006146"
    assert first.event_period == "2026.08.01 ~ 2026.08.31"
    assert first.event_start_date == date(2026, 8, 1)
    assert first.event_end_date == date(2026, 8, 31)
    assert first.detail_url == (
        "https://m.wooricard.com/dcmw/yh1/bnf/bnf02/prgevnt/movePrgEvntDtl.do"
        "?evntSrno=30006146"
    )
    assert first.image_url == (
        "https://m.wooricard.com/webcontent/evntFileList/2026/7/31/bc158914.png"
    )
    # evntSumTxt: HTML 이스케이프·<br>·CRLF 를 정리해 한 줄 요약으로
    assert first.benefit_summary == "호텔 예약은 WON트래블에서! 쿠폰 추가할인까지 받아보세요"
    assert items[1].image_url is None
    assert items[1].benefit_summary is None


def test_parse_woori_list_empty():
    assert parse_woori_list({}) == []
    assert parse_woori_list({"prgEvntList": []}) == []


# getPrgEvntDtl.pwkjson 의 pcCmsCntnts 는 HTML 이스케이프된 마크업이다
WOORI_CMS = (
    "&lt;ul class=&quot;eventCont&quot;&gt;&lt;li&gt;&lt;dl&gt;"
    "&lt;dt&gt;대상 카드&lt;/dt&gt;"
    "&lt;dd&gt;우리카드 개인 신용,체크카드 (법인, 선불/기프트카드 제외)&lt;/dd&gt;"
    "&lt;/dl&gt;&lt;/li&gt;&lt;li&gt;&lt;dl&gt;"
    "&lt;dt&gt;예약 기간&lt;/dt&gt;&lt;dd&gt;26년 8월 1일 ~&lt;/dd&gt;&lt;/dl&gt;&lt;/li&gt;&lt;/ul&gt;"
)


def test_parse_woori_detail_target_cards():
    cards = parse_woori_detail_target_cards(WOORI_CMS)
    assert cards == "우리카드 개인 신용,체크카드 (법인, 선불/기프트카드 제외)"


def test_parse_woori_detail_without_target_returns_none():
    assert parse_woori_detail_target_cards("&lt;p&gt;안내&lt;/p&gt;") is None
    assert parse_woori_detail_target_cards(None) is None


class TestSummarizeBenefitTexts:
    """'얼마 쓰면 얼마 받는다' 형태의 실질 혜택 문장을 골라 요약한다."""

    def test_prefers_spend_get_line_over_headline(self):
        texts = [
            "신세계 X 하나카드 신세계 제휴 하나카드 출석 챌린지!",  # 헤드라인 (금액 없음)
            "이벤트 기간 : 2026. 8. 3(월) ~ 8. 17(월)",
            "VIA SHINSEGAE 100만원 할인쿠폰 * 신세계 제휴 하나카드로 1,000만원 이상 전액 결제 시",
            "자세한 쿠폰 내용 및 사용 방법은 증정된 쿠폰 내 유의사항을 통해 확인 가능합니다",
        ]
        summary = summarize_benefit_texts(texts)
        # 받는 것(할인쿠폰)에 집중 — '* 얼마 이상 결제 시' 조건절은 제거한다
        assert summary == "VIA SHINSEGAE 100만원 할인쿠폰"
        assert "결제 시" not in summary and "이상" not in summary

    def test_joins_top_two_distinct_benefit_lines(self):
        texts = [
            "해외 결제 300만원 이상 시 5만 하나머니 적립",
            "해외 결제 500만원 이상 시 10만 하나머니 적립",
        ]
        summary = summarize_benefit_texts(texts)
        # 조건('300만원 이상')이 아니라 보상('5만 하나머니 적립')만 남긴다
        assert summary == "5만 하나머니 적립 · 10만 하나머니 적립"

    def test_reward_first_line_with_paren_condition(self):
        # 보상이 앞에 오고 조건이 괄호인 형태 — 괄호 조건만 제거
        texts = ["대인 종일권 최대 50% 즉시 할인 (스마트/현장 매표 시)"]
        assert summarize_benefit_texts(texts) == "대인 종일권 최대 50% 즉시 할인"

    def test_one_plus_one_line_qualifies(self):
        texts = ["두근두근 여행 시즌!", "아메리카노 1+1 쿠폰 제공"]
        summary = summarize_benefit_texts(texts)
        assert summary is not None and "1+1" in summary

    def test_condition_strip_keeps_line_without_reward_signal_intact(self):
        # 조건 제거 후 보상 신호가 안 남으면 원문(핵심부)을 유지한다
        texts = ["공항 라운지 무료 이용권 증정"]
        assert summarize_benefit_texts(texts) == "공항 라운지 무료 이용권 증정"

    def test_cta_tail_is_removed(self):
        texts = ["3만원 캐시백 트래블버킷 바로가기", "5만원 할인쿠폰 자세히 보기"]
        summary = summarize_benefit_texts(texts)
        assert "바로가기" not in summary and "자세히" not in summary
        assert "3만원 캐시백" in summary and "5만원 할인쿠폰" in summary

    def test_mid_sentence_cta_verb_does_not_delete_reward(self):
        # CTA 제거는 문장 '끝'에만 — 중간의 '확인하기'가 보상을 지우면 안 된다 (리뷰 HIGH)
        summary = summarize_benefit_texts(["확인하기 쉬운 5만원 캐시백 적립"])
        assert summary is not None and "5만원 캐시백" in summary

    def test_leading_reward_survives_later_condition_marker(self):
        # 보상이 앞에 오고 뒤에 '이용 시'가 있는 문장 — 앞 보상을 삼키면 안 된다 (리뷰 HIGH)
        summary = summarize_benefit_texts(["5만원 캐시백, 추가 이용 시 1만원 추가 적립"])
        assert summary is not None and summary.startswith("5만원 캐시백")

    def test_weak_coupon_noun_alone_does_not_qualify(self):
        # '쿠폰' 단독(금액 없음)의 CTA성 문구는 요약이 될 수 없다 (리뷰 MEDIUM)
        assert summarize_benefit_texts(["쿠폰 받고 예약하러 가기"]) is None

    def test_excludes_period_target_and_notice_lines(self):
        texts = [
            "이벤트 기간 : 2026.08.01 ~ 08.31",
            "이벤트 대상 : 전 고객",
            "유의사항: 혜택 제공 전 카드 해지 시 제외됩니다",
        ]
        assert summarize_benefit_texts(texts) is None

    def test_falls_back_to_benefit_verb_line_without_amount(self):
        # 금액이 없어도 혜택 동사가 있는 문장은 헤드라인보다 우선한다
        texts = [
            "두근두근 여행 시즌!",
            "공항 라운지 무료 이용권 증정",
        ]
        assert summarize_benefit_texts(texts) == "공항 라운지 무료 이용권 증정"

    def test_empty_returns_none(self):
        assert summarize_benefit_texts([]) is None
        assert summarize_benefit_texts(["", "  "]) is None

    def test_inline_notice_mention_does_not_kill_benefit_line(self):
        """문장 중간의 '유의사항/자세한' 언급은 배제 사유가 아니다 (행 시작만 배제)."""
        texts = ["해외 결제 시 5만원 캐시백 (유의사항 확인)"]
        summary = summarize_benefit_texts(texts)
        assert summary is not None and "5만원 캐시백" in summary
        # 행 시작이 유의사항이면 여전히 배제
        assert summarize_benefit_texts(["유의사항: 결제 시 5만원 캐시백 제외"]) is None

    def test_bare_percent_headline_does_not_qualify(self):
        """혜택동사·조건 없는 '%' 홍보 문구(당첨 랜덤박스류)는 요약이 될 수 없다."""
        assert summarize_benefit_texts(["100% 당첨 랜덤박스", "최대 100% 당첨 기회!"]) is None

    def test_foreign_currency_counts_as_amount(self):
        texts = ["두근두근 여행!", "50달러 상당 상품권 증정", "면세점 방문 안내"]
        assert summarize_benefit_texts(texts) == "50달러 상당 상품권 증정"

    def test_clips_to_two_line_length(self):
        long = "최대 10% 할인 " + "긴설명 " * 60
        summary = summarize_benefit_texts([long])
        # 목록 카드 2줄 안에 들어오는 길이
        assert summary is not None and len(summary) <= 90


def test_parse_woori_detail_benefit_summary_prefers_amount_lines():
    cms = (
        "&lt;dl&gt;&lt;dt&gt;대상 카드&lt;/dt&gt;&lt;dd&gt;우리카드 전체&lt;/dd&gt;&lt;/dl&gt;"
        "&lt;p&gt;호텔 예약은 WON트래블에서!&lt;/p&gt;"
        "&lt;p&gt;해외 호텔 40만원 이상 결제 시 최대 8만원 할인&lt;/p&gt;"
    )
    summary = parse_woori_detail_benefit_summary(cms)
    # 조건('40만원 이상 결제 시')은 버리고 받는 혜택만
    assert summary == "최대 8만원 할인"


def test_issuer_fetcher_registry():
    """스케줄러/수동 트리거가 공유하는 카드사 fetcher 레지스트리.

    새 카드사는 여기에만 등록하면 수집 경로 전체에 반영된다."""
    from app.services.card_benefit_fetcher import ISSUER_FETCHERS

    assert "hana" in ISSUER_FETCHERS and "woori" in ISSUER_FETCHERS
    assert all(callable(fn) for fn in ISSUER_FETCHERS.values())


def test_extract_benefit_tags():
    text = "호텔 최대 25% 할인 + 캐시백, 라운지 무료 이용권 1+1 증정"
    tags = extract_benefit_tags(text)
    assert "할인" in tags
    assert "캐시백" in tags
    assert "무료" in tags
    assert "1+1" in tags
    # 중복 없이, 매칭 없으면 빈 리스트
    assert extract_benefit_tags("일반 안내문") == []


# ---------------------------------------------------------------- KB국민카드

KB_LIST_DATA = {
    "resultCode": "UCXH0000",
    "totalCnt": 2,
    "totalPage": 1,
    "evntList": [
        {
            "evntId": 1001676,
            "evntTit": "국제선 항공권 청구할인 With 와이페이모어",
            "evtStYmd": "20260801",
            "evtEdYmd": "20260831",
            "evntTmnlImgPthNm": "https://img1.kbcard.com/ST/img/ubb/mgr/event/241220_whypaymore_orange.png",
        },
        {
            "evntId": "1001623",
            "evntTit": "해외결제는 1400원으로 고정환율 적용",
            "evtStYmd": "20260801",
            "evtEdYmd": "20260817",
            "evntTmnlImgPthNm": None,
        },
    ],
}


def test_parse_kb_list_builds_candidates():
    from datetime import date as date_cls

    from app.services.card_benefit_fetcher import parse_kb_list

    items = parse_kb_list(KB_LIST_DATA)
    assert len(items) == 2
    first = items[0]
    assert first.card_company == "KB국민카드"
    assert first.source_id == "kb:1001676"
    assert first.event_period == "2026.08.01 ~ 2026.08.31"
    assert first.event_start_date == date_cls(2026, 8, 1)
    assert first.event_end_date == date_cls(2026, 8, 31)
    assert first.detail_url == (
        "https://m.kbcard.com/BON/DVIEW/MBBMCXHIABNC0026?evntSerno=1001676"
    )
    assert first.image_url.startswith("https://img1.kbcard.com/")
    # 숫자/문자 evntId 모두 수용, 이미지 없으면 None
    assert items[1].source_id == "kb:1001623"
    assert items[1].image_url is None


def test_parse_kb_list_empty_and_broken():
    from app.services.card_benefit_fetcher import parse_kb_list

    assert parse_kb_list({}) == []
    assert parse_kb_list({"evntList": [{"evntId": None, "evntTit": "x"}]}) == []


KB_DETAIL_HTML = """
<html><body><div class="detail">
<h3>기간</h3><p>예약 2026.8.3(월)~8.31(월)</p>
<h3>대상</h3><p>KB국민 마스터 개인 신용/체크카드 기보유 고객 (KB국민 기업 제외)</p>
<h3>내용</h3><p>프로모션 코드 입력하면 최대 10만원 할인 + 글로벌 eSIM 1GB 무료 제공</p>
</div></body></html>
"""


def test_parse_kb_detail_sections():
    from app.services.card_benefit_fetcher import parse_kb_detail

    detail = parse_kb_detail(KB_DETAIL_HTML)
    assert detail.target_cards == "KB국민 마스터 개인 신용/체크카드 기보유 고객"
    assert "최대 10만원 할인" in detail.benefit_summary
    assert "eSIM" in detail.benefit_summary


def test_parse_kb_detail_missing_sections_returns_none_fields():
    from app.services.card_benefit_fetcher import parse_kb_detail

    detail = parse_kb_detail("<html><body>내용 없음</body></html>")
    assert detail.target_cards is None
    assert detail.benefit_summary is None


def test_parse_kb_detail_falls_back_to_body_paragraphs():
    """h3 라벨 구조가 없는 상세는 본문 문단에서 혜택 문장을 점수화해 뽑는다."""
    from app.services.card_benefit_fetcher import parse_kb_detail

    html = """
    <html><body><div class="cont">
    <p>이번 여름 특별한 혜택!</p>
    <p>대상 카드로 해외 이용 시 최대 5만 포인트리 적립</p>
    <p>자세한 내용은 앱에서 확인</p>
    </div></body></html>
    """
    detail = parse_kb_detail(html)
    assert detail.benefit_summary == "최대 5만 포인트리 적립"


# ---------------------------------------------------------------- 신한카드

SHINHAN_LIST = {
    "root": {
        "evnlist": [
            {
                "mobWbEvtNm": "호텔 최대 25% 할인",
                "evtImgSlTilNm": "신한 비자카드x아고다",
                "mobWbEvtStd": "20260722",
                "mobWbEvtEdd": "20260930",
                "hpgEvtCtgImgUrlAr": "/pconts/html/benefit/event/__icsFiles/afieldfile/2026/07/28/260115_agoda_list.png",
                "hpgEvtDlPgeUrlAr": "/pconts/html/benefit/event/2013812_2239.html",
                "mobWbEvtRvN": "2026071512HMPG",
                "mobWbBnfCagVl": "53",
            },
            {  # 다른 카테고리(쇼핑) — 제외돼야 함
                "mobWbEvtNm": "백화점 5% 캐시백",
                "mobWbEvtStd": "20260701",
                "mobWbEvtEdd": "20260931",
                "hpgEvtDlPgeUrlAr": "/pconts/html/benefit/event/999_2239.html",
                "mobWbEvtRvN": "2026070100SHOP",
                "mobWbBnfCagVl": "51",
            },
        ]
    }
}


def test_parse_shinhan_list_filters_travel_category():
    from datetime import date as date_cls

    from app.services.card_benefit_fetcher import parse_shinhan_list

    items = parse_shinhan_list(SHINHAN_LIST)
    assert len(items) == 1  # 여행숙박(53)만
    first = items[0]
    assert first.card_company == "신한카드"
    assert first.source_id == "shinhan:2026071512HMPG"
    assert first.title == "신한 비자카드x아고다 호텔 최대 25% 할인"
    assert first.event_period == "2026.07.22 ~ 2026.09.30"
    assert first.event_start_date == date_cls(2026, 7, 22)
    assert first.detail_url == (
        "https://www.shinhancard.com/pconts/html/benefit/event/2013812_2239.html"
    )
    assert first.image_url.startswith("https://www.shinhancard.com/pconts/")


def test_parse_shinhan_list_empty():
    from app.services.card_benefit_fetcher import parse_shinhan_list

    assert parse_shinhan_list({}) == []
    assert parse_shinhan_list({"root": {"evnlist": []}}) == []


SHINHAN_DETAIL_HTML = """
<html><body>
<h1 class="headline--m">호텔 최대 25% 할인</h1>
<h3 class="mt--6xl">행사대상</h3>
<p class="bodyText">신한Visa 신용 소지 고객 ※ 법인/체크/BC/선불/기프트카드 제외</p>
<h3 class="mt--6xl">행사내용</h3>
<p class="bodyText">신한Visa 개인 신용 카드로 아고다에서 국내외 호텔 결제 시 최대 25% 할인</p>
</body></html>
"""


def test_parse_shinhan_detail_sections():
    from app.services.card_benefit_fetcher import parse_shinhan_detail

    detail = parse_shinhan_detail(SHINHAN_DETAIL_HTML)
    assert detail.target_cards.startswith("신한Visa 신용 소지 고객")
    assert "최대 25% 할인" in detail.benefit_summary


# ---------------------------------------------------------------- 현대카드

HYUNDAI_LIST_HTML = """
<html><body>
<ul id="event_list1">
  <li onclick="location.href='/cpb/ev/CPBEV0101_06.hc?bnftWebEvntCd=196954&searchWord=여행'">
    <div class="eventimg"><img src="/upload/cpd/mb/MO 이벤트 리스트 이미지 등록_1704696963823.png"></div>
    <h3 class="p1_m_lt_1ln">플래티넘카드 무료 해외여행자보험<br>가입 안내(2026년 기준)</h3>
    <p class="p2_m_lt_1ln">2026. 1. 1 ~ 2026. 12. 31</p>
  </li>
  <li onclick="goDetail('OSH869')" data-code="bnftWebEvntCd=OSH869">
    <div class="eventimg"><img src="/upload/cpd/mb/PCMOLogo_privia.png"></div>
    <h3 class="p1_m_lt_1ln">PRIVIA 여행 국제선 항공권 10% M포인트 사용</h3>
    <p class="p2_m_lt_1ln">2026. 1. 1 ~ 2026. 12. 30</p>
  </li>
</ul>
</body></html>
"""


def test_parse_hyundai_list_from_html():
    from datetime import date as date_cls

    from app.services.card_benefit_fetcher import parse_hyundai_list

    items = parse_hyundai_list(HYUNDAI_LIST_HTML)
    assert len(items) == 2
    first = items[0]
    assert first.card_company == "현대카드"
    assert first.source_id == "hyundai:196954"
    assert first.title == "플래티넘카드 무료 해외여행자보험 가입 안내(2026년 기준)"
    assert first.event_period == "2026.01.01 ~ 2026.12.31"
    assert first.event_start_date == date_cls(2026, 1, 1)
    assert first.event_end_date == date_cls(2026, 12, 31)
    assert first.detail_url == (
        "https://www.hyundaicard.com/cpb/ev/CPBEV0101_06.hc?bnftWebEvntCd=196954"
    )
    # 이미지 파일명의 공백은 URL 인코딩된다
    assert " " not in first.image_url
    assert first.image_url.startswith("https://www.hyundaicard.com/upload/")
    assert items[1].source_id == "hyundai:OSH869"


def test_parse_hyundai_list_empty():
    from app.services.card_benefit_fetcher import parse_hyundai_list

    assert parse_hyundai_list("<html><body>없음</body></html>") == []


def test_parse_hyundai_detail_content():

    html = """
    <html><body><div class="content">
    혜택 해외여행자보험 무료 가입 서비스 제공
    기간 2026.1.1 ~ 12.31
    대상 카드 현대카드M2 Platinum, M3 Platinum, T3 Platinum
    이용방법 출국 전 신청
    </div></body></html>
    """
    from app.services.card_benefit_fetcher import parse_hyundai_detail as p

    detail = p(html)
    assert "현대카드M2 Platinum" in (detail.target_cards or "")
    assert "무료" in (detail.benefit_summary or "")


# ---------------------------------------------------------------- 삼성카드

SAMSUNG_LIST = {
    "evtRsCount": 2,
    "evtRsList": [
        {
            "eventTitle": "삼성카드와 떠나는 <!HS>여행<!HE>! 최대 5% 할인",
            "startDate": "26.04.15",
            "endDate": "26.08.31",
            "imagePath": "//static11.samsungcard.com/wcms/event/P_thumb_15.png",
            "contentID": "3744484",
            "eventID": "M261104998",
            "eventIngYN": "진행중",
        },
        {
            "eventTitle": "지난 <!HS>여행<!HE> 이벤트",
            "startDate": "26.01.01",
            "endDate": "26.03.31",
            "imagePath": None,
            "contentID": "111",
            "eventIngYN": "종료",
        },
    ],
}


def test_parse_samsung_list_filters_ongoing_and_cleans_title():
    from datetime import date as date_cls

    from app.services.card_benefit_fetcher import parse_samsung_list

    items = parse_samsung_list(SAMSUNG_LIST)
    assert len(items) == 1  # 종료 이벤트 제외
    first = items[0]
    assert first.card_company == "삼성카드"
    assert first.source_id == "samsung:3744484"
    assert first.title == "삼성카드와 떠나는 여행! 최대 5% 할인"  # 하이라이트 태그 제거
    assert first.event_period == "2026.04.15 ~ 2026.08.31"
    assert first.event_start_date == date_cls(2026, 4, 15)
    assert first.detail_url == (
        "https://www.samsungcard.com/personal/event/ing/UHPPBE1403M0.jsp?cms_id=3744484"
    )
    assert first.image_url == "https://static11.samsungcard.com/wcms/event/P_thumb_15.png"


def test_parse_samsung_detail_dl():
    from app.services.card_benefit_fetcher import parse_samsung_detail

    html = """
    <html><body><dl class="new_dl">
    <dt>행사기간</dt><dd>2026.04.15 ~ 2026.08.31</dd>
    <dt>대상카드</dt><dd>삼성 개인 신용카드 (가족카드 포함)</dd>
    <dt>혜택</dt><dd>참좋은여행 해외여행 5% 즉시할인</dd>
    </dl></body></html>
    """
    detail = parse_samsung_detail(html)
    assert detail.target_cards == "삼성 개인 신용카드"
    assert "5% 즉시할인" in detail.benefit_summary


# ---------------------------------------------------------------- 롯데카드

LOTTE_LIST_PAYLOAD = {
    "Status": "200",
    "Param": {"selectedCategoryName": "레저·여행", "pageNo": 1, "totalPage": 1, "totalRowCnt": 2},
    "Content": """
    <li>
      <a href="#" onclick="fnGoInqEvn('E','11197');" class="lnk_11197"
         data-gtm-body='{"cts_id":"11197","cts_name":"호텔스닷컴 최대 50% 할인"}'>
        <img src="//image.lottecard.co.kr/UploadFiles/event/hotels.png">
        <strong class="thumb-name">호텔스닷컴에서 아웃리거 리조트를<br>예약하면 최대 50% 할인</strong>
        <span class="thumb-date">2026.07.01 ~ 2026.08.31</span>
      </a>
    </li>
    <li>
      <a href="#" onclick="fnGoInqEvn('E','11174');" class="lnk_11174"
         data-gtm-body='{"cts_id":"11174","cts_name":"힐튼 포인트 적립"}'>
        <strong class="thumb-name">힐튼 호텔 숙박하고 최대 4,000 포인트 적립</strong>
        <span class="thumb-date">2026.07.01 ~ 2026.08.15</span>
      </a>
    </li>
    """,
}


def test_parse_lotte_list_builds_candidates():
    from datetime import date as date_cls

    from app.services.card_benefit_fetcher import parse_lotte_list

    items = parse_lotte_list(LOTTE_LIST_PAYLOAD)
    assert len(items) == 2
    first = items[0]
    assert first.card_company == "롯데카드"
    assert first.source_id == "lotte:11197"
    # 제목의 <br> 은 공백으로 정규화
    assert first.title == "호텔스닷컴에서 아웃리거 리조트를 예약하면 최대 50% 할인"
    assert first.event_period == "2026.07.01 ~ 2026.08.31"
    assert first.event_start_date == date_cls(2026, 7, 1)
    assert first.event_end_date == date_cls(2026, 8, 31)
    assert first.detail_url == (
        "https://m.lottecard.co.kr/app/LPBNFDA_V300.lc?evnBultSeq=11197"
    )
    # 프로토콜 상대경로 이미지는 https 로 절대화
    assert first.image_url == "https://image.lottecard.co.kr/UploadFiles/event/hotels.png"
    assert items[1].image_url is None


def test_parse_lotte_list_empty():
    from app.services.card_benefit_fetcher import parse_lotte_list

    assert parse_lotte_list({}) == []
    assert parse_lotte_list({"Content": ""}) == []


def test_parse_lotte_detail_sections():
    from app.services.card_benefit_fetcher import parse_lotte_detail

    html = """
    <html><body>
    <div class="sub-content event-content">
      <h4 class="sub-title title-depth4">혜택 안내</h4>
      <p>호텔스닷컴에서 아웃리거 리조트 예약 시 최대 50% 할인</p>
      <h4 class="sub-title title-depth4">대상카드</h4>
      <p>비자(Visa) 개인 신용카드 중 카드번호 앞 6자리: 401585, 467007</p>
    </div>
    </body></html>
    """
    detail = parse_lotte_detail(html)
    assert detail.target_cards.startswith("비자(Visa) 개인 신용카드")
    assert "최대 50% 할인" in detail.benefit_summary


def test_parse_hyundai_period_invalid_date_does_not_crash():
    """2월 30일 같은 비정상 날짜가 와도 현대카드 수집 전체가 죽지 않는다 (리뷰 MEDIUM)."""
    from app.services.card_benefit_fetcher import _parse_hyundai_period, parse_hyundai_list

    assert _parse_hyundai_period("2026.02.30 ~ 2026.13.01") == (None, None)

    html = HYUNDAI_LIST_HTML.replace("2026. 1. 1 ~ 2026. 12. 31", "2026. 2. 30 ~ 2026. 13. 1")
    items = parse_hyundai_list(html)
    assert len(items) == 2  # 날짜만 비고 나머지 항목은 유지
    assert items[0].event_start_date is None


def test_static_detail_parser_exception_falls_back_to_list_info():
    """상세 파서가 예기치 못한 예외를 던져도 해당 건만 목록 정보로 폴백한다 (리뷰 MEDIUM)."""
    from datetime import date as date_cls

    from app.services.card_benefit_fetcher import CardBenefitCandidate, _with_static_detail

    class FakeRes:
        text = "<html></html>"
        def raise_for_status(self):
            return None

    class FakeClient:
        def get(self, url):
            return FakeRes()

    def broken_parser(html):
        raise AttributeError("정찰 스펙과 다른 마크업")

    c = CardBenefitCandidate(
        source_id="kb:1", card_company="KB국민카드", title="여행 5% 할인",
        event_period="2026.08.01 ~", event_start_date=date_cls(2026, 8, 1),
        event_end_date=None, detail_url="https://ex.com/1", image_url=None,
    )
    result = _with_static_detail(FakeClient(), c, broken_parser, "KB국민카드")
    assert result.title == "여행 5% 할인"  # 목록 정보 유지
    assert result.benefit_tags == "할인"


# ---------------------------------------------------------------- BC카드 (페이북)

BC_LIST_DATA = {
    "data": {
        "evntInqrList": [
            {
                "pybcUnifEvntNo": "2026070035",
                "pybcUnifEvntNm1": "마이리얼트립",
                "pybcUnifEvntNm2": "20만원 이상 결제 시",
                "pybcUnifEvntNm3": "최대 6만원 즉시 할인",
                "evntBltnStrtDtm": "20260731160000",
                "evntBltnEndDtm": "20260831235959",
                "evntBsImgUrlAddr": "https://cdn.paybooc.co.kr/cbf/bannerimage/x.png",
                "evntMrktTypCd": "03",
            },
            {  # 여행/해외(03) 아님 — 제외
                "pybcUnifEvntNo": "2026070017",
                "pybcUnifEvntNm2": "컬리 3천원 즉시적립",
                "pybcUnifEvntNm3": "",
                "evntBltnStrtDtm": "20260803100000",
                "evntBltnEndDtm": "20260831235959",
                "evntMrktTypCd": "04",
            },
        ]
    }
}


def test_parse_bc_list_filters_travel_category():
    from datetime import date as date_cls

    from app.services.card_benefit_fetcher import parse_bc_list

    items = parse_bc_list(BC_LIST_DATA)
    assert len(items) == 1  # 여행/해외(03)만
    first = items[0]
    assert first.card_company == "BC카드"
    assert first.source_id == "bc:2026070035"
    assert first.title == "마이리얼트립 20만원 이상 결제 시 최대 6만원 즉시 할인"
    assert first.event_period == "2026.07.31 ~ 2026.08.31"
    assert first.event_start_date == date_cls(2026, 7, 31)
    assert first.event_end_date == date_cls(2026, 8, 31)
    assert first.detail_url == (
        "https://web.paybooc.co.kr/web/evnt/evnt-dts?pybcUnifEvntNo=2026070035"
    )
    assert first.image_url == "https://cdn.paybooc.co.kr/cbf/bannerimage/x.png"


def test_parse_bc_list_empty():
    from app.services.card_benefit_fetcher import parse_bc_list

    assert parse_bc_list({}) == []
    assert parse_bc_list({"data": {"evntInqrList": []}}) == []


BC_DETAIL_HTML = """
<html><body><script>
const eventData = {"pybcUnifEvntNo":"2026070035","eventDetailsGroupBaseDtoList":[
 {"evntDtGrpNm":"혜택","eventDetailGroupContentDtoList":[
   {"cntnTitlNm":"마이리얼트립에서 여행상품 BC카드로 결제 시, 최대 6만원 즉시 할인",
    "cntnDtCtnt":"<ul><li>20만원 이상 결제 시 7천원 즉시 할인</li><li>200만원 이상 결제 시 6만원 즉시 할인</li></ul>"}]},
 {"evntDtGrpNm":"대상카드","eventDetailGroupContentDtoList":[
   {"cntnTitlNm":"","cntnDtCtnt":"BC 개인 신용카드 대상<br>※ 단, 법인•선불•기프트카드 및 간편결제 제외"}]}
]};
</script></body></html>
"""


def test_parse_bc_detail_groups():
    from app.services.card_benefit_fetcher import parse_bc_detail

    detail = parse_bc_detail(BC_DETAIL_HTML)
    assert detail.target_cards.startswith("BC 개인 신용카드 대상")
    assert "즉시 할인" in detail.benefit_summary


def test_parse_bc_detail_without_event_data_returns_none_fields():
    from app.services.card_benefit_fetcher import parse_bc_detail

    detail = parse_bc_detail("<html><body>없음</body></html>")
    assert detail.target_cards is None
    assert detail.benefit_summary is None
