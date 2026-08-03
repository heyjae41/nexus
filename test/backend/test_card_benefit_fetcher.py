"""Card.Pick 카드사 여행 혜택 수집 — 파서 단위 테스트.

- 하나카드: MKEVT1000M.ajax(EUC-KR JSON) 목록 + MKEVT1010M.web 상세 HTML
- 우리카드: getPrgEvntList.pwkjson 목록 + getPrgEvntDtl.pwkjson 의 pcCmsCntnts(HTML 이스케이프)
파서는 순수 함수로 두고 네트워크/브라우저는 fetch 계층에서만 다룬다.
"""
from datetime import date

from app.services.card_benefit_fetcher import (
    extract_benefit_tags,
    parse_hana_detail_target_cards,
    parse_hana_list,
    parse_woori_detail_target_cards,
    parse_woori_list,
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
    # 이미지 없는 항목은 None
    assert items[1].image_url is None


def test_parse_hana_list_tolerates_missing_fields():
    assert parse_hana_list({}) == []
    assert parse_hana_list({"eventListMap": {"list": [{"EVN_SEQ": None}]}}) == []
    # 제목 없는 항목은 건너뛴다
    data = {"eventListMap": {"list": [{"EVN_SEQ": "1", "EVN_TIT_NM": ""}]}}
    assert parse_hana_list(data) == []


HANA_DETAIL_HTML = """
<html><body>
<section class="eVgroup"><h2 class="tit-round">혜택 제공일</h2>
<p class="txt-cont"><b>2026. 10. 31 이내</b></p></section>
<section class="eVgroup"><h2 class="tit-round">대상카드</h2>
<p class="txt-cont"><b>JADE First Centum, JADE First<br>JADE Prime, JADE Classic<br>(Visa 브랜드)</b></p>
</section>
</body></html>
"""


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
    assert items[1].image_url is None


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


def test_extract_benefit_tags():
    text = "호텔 최대 25% 할인 + 캐시백, 라운지 무료 이용권 1+1 증정"
    tags = extract_benefit_tags(text)
    assert "할인" in tags
    assert "캐시백" in tags
    assert "무료" in tags
    assert "1+1" in tags
    # 중복 없이, 매칭 없으면 빈 리스트
    assert extract_benefit_tags("일반 안내문") == []
