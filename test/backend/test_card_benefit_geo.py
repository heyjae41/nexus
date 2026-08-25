"""card.Pick 국가 코드 분류·필터 계약 테스트."""
from app.services.card_benefit_geo import (
    COUNTRY_FLAGS, COUNTRY_NAMES, OVERSEAS_COMMON, expand_country_filter,
    extract_countries, match_rank, normalize_country_codes,
)


def test_extracts_configured_country_codes_from_names_and_cities():
    assert extract_countries("일본 세븐일레븐 2만원 결제 시 적립") == ["JP"]
    assert extract_countries("다낭 호텔 최대 25% 할인") == ["VN"]
    assert set(extract_countries("괌과 마카오 여행 특가")) == {"GU", "MO"}
    assert set(extract_countries("두바이와 프라하 여행")) == {"AE", "CZ"}


def test_extracts_multiple_configured_codes():
    assert set(extract_countries("일본·태국·베트남 여행 시 캐시백")) == {"JP", "TH", "VN"}


def test_unconfigured_country_region_and_unclassified_values_become_all():
    assert extract_countries("동남아 전 가맹점 5% 할인") == [OVERSEAS_COMMON]
    assert extract_countries("독일 여행 혜택") == [OVERSEAS_COMMON]
    assert extract_countries("서울랜드 파크이용권 1+1") == [OVERSEAS_COMMON]
    assert extract_countries(None) == [OVERSEAS_COMMON]


def test_false_positive_guards_preserve_all_fallback():
    assert extract_countries("세부 조건은 상세페이지 참조") == [OVERSEAS_COMMON]
    assert extract_countries("파리바게뜨 제휴 할인") == [OVERSEAS_COMMON]
    assert extract_countries("VISA PLATINUM 대상 해외 적립") == [OVERSEAS_COMMON]


def test_normalizes_legacy_values_to_configured_codes_or_all():
    assert normalize_country_codes("베트남,일본") == ["VN", "JP"]
    assert normalize_country_codes("동남아,독일,해외공통") == ["ALL"]
    assert normalize_country_codes(None) == ["ALL"]


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
