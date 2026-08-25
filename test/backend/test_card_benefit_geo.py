"""card.Pick 국가 코드 분류·필터 계약 테스트."""
from app.services.card_benefit_geo import (
    COUNTRY_FLAGS, COUNTRY_NAMES, DOMESTIC_ONLY, OVERSEAS_COMMON,
    expand_country_filter, extract_countries, is_domestic_only,
    match_rank, normalize_country_codes,
)


def test_extracts_configured_country_codes_from_names_and_cities():
    assert extract_countries("일본 세븐일레븐 2만원 결제 시 적립") == ["JP"]
    assert extract_countries("다낭 호텔 최대 25% 할인") == ["VN"]
    assert set(extract_countries("괌과 마카오 여행 특가")) == {"GU", "MO"}
    assert set(extract_countries("두바이와 프라하 여행")) == {"AE", "CZ"}


def test_extracts_multiple_configured_codes():
    assert set(extract_countries("일본·태국·베트남 여행 시 캐시백")) == {"JP", "TH", "VN"}


def test_unconfigured_overseas_region_and_unclassified_values_become_all():
    assert extract_countries("동남아 전 가맹점 5% 할인") == [OVERSEAS_COMMON]
    assert extract_countries("독일 여행 혜택") == [OVERSEAS_COMMON]
    assert extract_countries(None) == [OVERSEAS_COMMON]


def test_domestic_only_benefits_are_classified_separately_from_overseas_common():
    assert extract_countries("서울랜드 파크이용권 1+1") == [DOMESTIC_ONLY]
    assert extract_countries(
        "롯데렌터카 제주 최대 89%, 내륙 최대 65% 할인"
    ) == [DOMESTIC_ONLY]
    assert is_domestic_only("제주도 지역 렌터카 예약 할인") is True
    assert is_domestic_only("국내외 호텔 최대 25% 할인") is False
    assert is_domestic_only("제주 출발 해외여행 항공권 할인") is False
    assert is_domestic_only("한국 출발 독일 여행 할인") is False
    assert is_domestic_only("하이원 리조트 워터파크 최대 55% 할인") is True
    assert is_domestic_only("모나용평 객실 패키지 최대 70% 할인") is True
    assert is_domestic_only("휘닉스 파크 블루캐니언 할인") is True
    assert is_domestic_only("시그니엘 서울 라운지 프로모션") is True
    assert is_domestic_only("그랜드 조선 부산 다이닝 할인") is True


def test_overseas_trip_support_services_are_not_treated_as_domestic_only():
    assert is_domestic_only("인천공항 라운지 1+1 할인") is False
    assert is_domestic_only("김포공항 주차대행 할인") is False
    assert is_domestic_only("국제선 항공권 할인") is False
    assert is_domestic_only("신라면세점 할인") is False


def test_false_positive_guards_preserve_all_fallback():
    assert extract_countries("세부 조건은 상세페이지 참조") == [OVERSEAS_COMMON]
    assert extract_countries("파리바게뜨 제휴 할인") == [OVERSEAS_COMMON]
    assert extract_countries("VISA PLATINUM 대상 해외 적립") == [OVERSEAS_COMMON]


def test_normalizes_legacy_values_to_configured_codes_or_all():
    assert normalize_country_codes("베트남,일본") == ["VN", "JP"]
    assert normalize_country_codes("동남아,독일,해외공통") == ["ALL"]
    assert normalize_country_codes(None) == ["ALL"]
    assert normalize_country_codes(DOMESTIC_ONLY) == []
    assert normalize_country_codes("국내·기타") == []


def test_filter_uses_code_and_all_only():
    assert expand_country_filter("VN") == {"VN", "ALL"}
    assert expand_country_filter("ALL") == {"ALL"}
    assert match_rank(["VN"], "VN") == 0
    assert match_rank(["ALL"], "VN") == 2
    assert match_rank(["ALL"], "ALL") == 2


def test_country_metadata_covers_exactly_the_public_contract():
    expected = {
        "TW", "GU", "FR", "ES", "GB", "MO", "HU", "TH", "HK", "SG", "JP",
        "MY", "US", "AE", "CN", "ID", "VN", "CA", "AU", "IT", "CZ", "ALL",
    }
    assert set(COUNTRY_NAMES) == expected
    assert set(COUNTRY_FLAGS) == expected
