"""card.Pick 국가 코드 분류 및 필터 지원.

공개 API는 지정된 ISO 3166-1 alpha-2 코드와 ``ALL``만 사용한다. 국내 전용
혜택은 내부 표식 ``KR``로 분류하고 API에서 제외한다. 지정 목록에 없는 해외
국가·권역·미분류 항목은 해외공통 ``ALL``이다.
"""

import re

OVERSEAS_COMMON = "ALL"
DOMESTIC_ONLY = "KR"

# API/필터에서 허용하는 국가 코드와 표시명. 이 목록 밖의 장소는 ALL로 분류한다.
COUNTRY_NAMES: dict[str, str] = {
    "TW": "대만", "GU": "괌", "FR": "프랑스", "ES": "스페인", "GB": "영국",
    "MO": "마카오", "HU": "헝가리", "TH": "태국", "HK": "홍콩", "SG": "싱가폴",
    "JP": "일본", "MY": "말레이지아", "US": "미국", "AE": "아랍에미레이트",
    "CN": "중국", "ID": "인도네시아", "VN": "베트남", "CA": "캐나다",
    "AU": "오스트레일리아", "IT": "이탈리아", "CZ": "체코", "ALL": "해외공통",
}

# 코드 → 감지 키워드 (국가명 + 주요 도시·랜드마크)
COUNTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "JP": ("일본", "도쿄", "오사카", "후쿠오카", "삿포로", "오키나와", "나고야", "교토", "엔화", "돈키호테", "재팬"),
    "CN": ("중국", "상하이", "베이징"),
    "TW": ("대만", "타이베이", "타이완"),
    "HK": ("홍콩",), "MO": ("마카오",),
    "VN": ("베트남", "다낭", "하노이", "나트랑", "호치민", "푸꾸옥"),
    "TH": ("태국", "방콕", "치앙마이", "푸켓"),
    "SG": ("싱가포르", "싱가폴", "마리나 베이", "센토사"),
    "MY": ("말레이시아", "말레이지아", "쿠알라룸푸르", "코타키나발루"),
    "ID": ("인도네시아", "발리", "자카르타"),
    "GU": ("괌",),
    "US": ("미국", "하와이", "뉴욕", "라스베가스", "로스앤젤레스"),
    "FR": ("프랑스", "파리", "루브르"), "GB": ("영국", "런던"),
    "IT": ("이탈리아", "로마", "밀라노"), "ES": ("스페인", "바르셀로나", "마드리드"),
    "HU": ("헝가리", "부다페스트"), "CZ": ("체코", "프라하"),
    "AU": ("호주", "오스트레일리아", "시드니", "멜버른"),
    "CA": ("캐나다", "밴쿠버", "토론토"),
    "AE": ("아랍에미레이트", "UAE", "두바이", "아부다비"),
}

COUNTRY_FLAGS = {
    "TW": "🇹🇼", "GU": "🇬🇺", "FR": "🇫🇷", "ES": "🇪🇸", "GB": "🇬🇧",
    "MO": "🇲🇴", "HU": "🇭🇺", "TH": "🇹🇭", "HK": "🇭🇰", "SG": "🇸🇬",
    "JP": "🇯🇵", "MY": "🇲🇾", "US": "🇺🇸", "AE": "🇦🇪", "CN": "🇨🇳",
    "ID": "🇮🇩", "VN": "🇻🇳", "CA": "🇨🇦", "AU": "🇦🇺", "IT": "🇮🇹",
    "CZ": "🇨🇿", "ALL": "🌏",
}
KNOWN_PLACES = tuple(COUNTRY_NAMES)

_STOP_PHRASES_RE = re.compile(
    r"세부\s*(?:조건|내용|사항|정보|혜택|기준|일정|안내|방법|사용|절차|설명)"
    r"|파리바게뜨|런던제화|로마자"
)
_DOMESTIC_RE = re.compile(
    r"국내|(?:대한민국|한국)\s*(?:내|전용|여행|숙박|호텔)"
    r"|제주(?:도)?|내륙|서울랜드"
)
_OVERSEAS_RE = re.compile(
    r"해외|국외|글로벌|전\s*세계|세계\s*각국|국내\s*(?:외|[/·&]\s*외)"
)


def _match_keyword_map(blob: str) -> list[str]:
    return [
        code for code, keywords in COUNTRY_KEYWORDS.items()
        if any(keyword in blob for keyword in keywords)
    ]


def is_domestic_only(text: str | None, geo_text: str | None = None) -> bool:
    """국가·해외 단서 없이 국내 지역/이용 단서만 있는 혜택인지 판정한다.

    상세 본문의 ``해외 이용 시 수수료`` 같은 상용구는 해외 혜택 근거로 쓰지
    않지만, 제목·요약의 명시적 해외 단서는 국내 판정보다 우선한다.
    """
    primary = _STOP_PHRASES_RE.sub(" ", text or "")
    detail = _STOP_PHRASES_RE.sub(" ", geo_text or "")
    combined = f"{primary} {detail}"
    if _match_keyword_map(combined) or _OVERSEAS_RE.search(primary):
        return False
    return bool(_DOMESTIC_RE.search(combined))


def extract_countries(text: str | None, geo_text: str | None = None) -> list[str]:
    """지정 국가, 국내 전용 ``KR``, 해외공통 ``ALL``을 반환한다."""
    blob = _STOP_PHRASES_RE.sub(" ", text or "")
    combined = f"{blob} {_STOP_PHRASES_RE.sub(' ', geo_text or '')}"
    found = _match_keyword_map(combined)
    if found:
        return found
    if is_domestic_only(text, geo_text):
        return [DOMESTIC_ONLY]
    return [OVERSEAS_COMMON]


def normalize_country_codes(values: str | None) -> list[str]:
    """기존 저장값을 공개 API 코드로 변환하고 국내 전용값은 제거한다."""
    if not values:
        return [OVERSEAS_COMMON]
    codes: list[str] = []
    domestic_only = False
    for value in values.split(","):
        value = value.strip()
        if value == DOMESTIC_ONLY or is_domestic_only(value):
            domestic_only = True
            continue
        if value in COUNTRY_NAMES:
            code = value
        else:
            code = next(
                (key for key, keywords in COUNTRY_KEYWORDS.items() if value in keywords),
                OVERSEAS_COMMON,
            )
        if code not in codes:
            codes.append(code)
    return codes or ([] if domestic_only else [OVERSEAS_COMMON])


def expand_country_filter(selected: str) -> set[str]:
    """국가 선택은 해당 코드와 해외공통 혜택만 포함한다."""
    return {selected} if selected == OVERSEAS_COMMON else {selected, OVERSEAS_COMMON}


def match_rank(event_countries: list[str], selected: str) -> int:
    """정렬 우선순위: 선택 국가(0), 해외공통(2)."""
    if selected == OVERSEAS_COMMON:
        return 2
    return 0 if selected in event_countries else 2
