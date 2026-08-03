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


def test_extract_benefit_tags():
    text = "호텔 최대 25% 할인 + 캐시백, 라운지 무료 이용권 1+1 증정"
    tags = extract_benefit_tags(text)
    assert "할인" in tags
    assert "캐시백" in tags
    assert "무료" in tags
    assert "1+1" in tags
    # 중복 없이, 매칭 없으면 빈 리스트
    assert extract_benefit_tags("일반 안내문") == []
