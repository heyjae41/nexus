"""card.Pick 지역(국가/권역) 추출·필터 전개 테스트.

- 이벤트 텍스트에서 국가(도시·랜드마크 포함)와 권역(동남아/유럽 등)을 사전 매칭
- 분류 불가 시: 해외성 신호가 있으면 '해외공통', 없으면 '국내·기타'
- 국가 필터 선택 시 소속 권역·해외공통까지 전개 (해외공통은 항상 포함, 후순위)
"""
from app.services.card_benefit_geo import (
    COUNTRY_FLAGS,
    OVERSEAS_COMMON,
    DOMESTIC_ETC,
    expand_country_filter,
    extract_countries,
    match_rank,
)


class TestExtractCountries:
    def test_country_by_name_and_city(self):
        assert extract_countries("일본 세븐일레븐 2만원 결제 시 적립") == ["일본"]
        assert extract_countries("다낭 호텔 최대 25% 할인") == ["베트남"]
        assert extract_countries("파리 루브르 박물관 패스트 레인") == ["프랑스"]

    def test_multiple_countries(self):
        found = extract_countries("일본·태국·베트남 여행 시 캐시백")
        assert set(found) == {"일본", "태국", "베트남"}

    def test_region_kept_as_is(self):
        assert extract_countries("동남아 전 가맹점 5% 할인") == ["동남아"]
        assert extract_countries("유럽 여행 필수 혜택") == ["유럽"]

    def test_overseas_generic_bucket(self):
        assert extract_countries("해외 결제 시 5% 캐시백") == [OVERSEAS_COMMON]
        assert extract_countries("해외여행자보험 무료 가입") == [OVERSEAS_COMMON]
        assert extract_countries("공항 라운지 무료 이용") == [OVERSEAS_COMMON]

    def test_domestic_bucket(self):
        assert extract_countries("서울랜드 파크이용권 1+1") == [DOMESTIC_ETC]
        assert extract_countries("") == [DOMESTIC_ETC]
        assert extract_countries(None) == [DOMESTIC_ETC]

    def test_country_wins_over_generic_signal(self):
        # 국가가 명시되면 해외공통이 아니라 그 국가로 분류한다
        assert extract_countries("일본 해외 결제 시 캐시백") == ["일본"]


class TestExpandCountryFilter:
    def test_country_expands_to_regions_and_common(self):
        expanded = expand_country_filter("베트남")
        assert "베트남" in expanded
        assert "동남아" in expanded          # 소속 권역
        assert OVERSEAS_COMMON in expanded  # 해외공통 항상 포함
        assert "일본" not in expanded

    def test_region_expands_to_member_countries(self):
        expanded = expand_country_filter("유럽")
        assert "유럽" in expanded and "프랑스" in expanded
        assert OVERSEAS_COMMON in expanded

    def test_domestic_is_isolated(self):
        expanded = expand_country_filter(DOMESTIC_ETC)
        assert expanded == {DOMESTIC_ETC}

    def test_match_rank_orders_specific_first(self):
        # 정렬 우선순위: 국가 명시(0) < 권역(1) < 해외공통(2)
        assert match_rank(["베트남"], "베트남") == 0
        assert match_rank(["동남아"], "베트남") == 1
        assert match_rank([OVERSEAS_COMMON], "베트남") == 2

    def test_country_flags_cover_known_countries(self):
        assert COUNTRY_FLAGS.get("일본") == "🇯🇵"
        assert COUNTRY_FLAGS.get(OVERSEAS_COMMON)  # 해외공통도 아이콘 보유


class TestFalsePositiveGuards:
    """사전 부분문자열 오탐 방지 (리뷰 HIGH)."""

    def test_sebu_boilerplate_is_not_philippines(self):
        assert extract_countries("세부 조건은 상세페이지 참조, 해외 결제 시 캐시백") == [OVERSEAS_COMMON]
        assert extract_countries("세부내용은 유의사항 확인") == [DOMESTIC_ETC]
        # 진짜 세부(도시)는 잡아야 한다
        assert extract_countries("필리핀 세부 여행 특가") == ["필리핀"]
        assert extract_countries("세부 막탄 리조트 할인") == ["필리핀"]

    def test_english_card_names_are_not_usa(self):
        # 'LA' 같은 짧은 영문 토큰이 카드명(PLATINUM/GALAXY/CLASS)에 오탐되면 안 됨
        assert extract_countries("VISA PLATINUM 대상 해외 적립") == [OVERSEAS_COMMON]
        assert extract_countries("GALAXY 카드 국내 이벤트") == [DOMESTIC_ETC]
        # 로스앤젤레스는 정상 인식
        assert extract_countries("로스앤젤레스 직항 특가") == ["미국"]


class TestMatchRankRegionSelection:
    """권역 선택 시에도 명시>권역>공통 순위 유지 (리뷰 MEDIUM)."""

    def test_member_country_ranks_above_common_under_region_filter(self):
        assert match_rank(["유럽"], "유럽") == 0
        assert match_rank(["프랑스"], "유럽") == 1       # 소속국 = 권역 매칭
        assert match_rank([OVERSEAS_COMMON], "유럽") == 2

    def test_unrelated_region_does_not_get_rank_one(self):
        # 관련 없는 권역 단어만 있는 이벤트가 1순위를 받으면 안 됨 (리뷰 LOW)
        assert match_rank(["유럽"], "베트남") == 2
