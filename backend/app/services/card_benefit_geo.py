"""card.Pick 지역(국가/권역) 분류 — 사전 기반 매칭.

이벤트 텍스트에서 대상 국가를 추출한다. 권역 단어(동남아/유럽 등)는 원문
그대로 보존하고, 필터 시점에 소속 국가로 전개한다. 분류 불가 시 해외성
신호가 있으면 '해외공통', 없으면 '국내·기타' 버킷으로 분류한다.

'베트남' 필터 = 베트남 명시 ∪ 소속 권역(동남아) ∪ 해외공통 — 여행객에게
유효한 혜택을 빠뜨리지 않기 위한 포함 관계 전개이며, 정렬은 명시가 우선.
"""

OVERSEAS_COMMON = "해외공통"
DOMESTIC_ETC = "국내·기타"

# 국가 → 감지 키워드 (국가명 + 주요 도시·랜드마크·통화 등)
COUNTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "일본": ("일본", "도쿄", "오사카", "후쿠오카", "삿포로", "오키나와", "나고야",
           "교토", "엔화", "돈키호테", "재팬"),
    "중국": ("중국", "상하이", "베이징", "알리페이", "유니온페이"),
    "대만": ("대만", "타이베이", "타이완"),
    "홍콩": ("홍콩", "마카오"),
    "베트남": ("베트남", "다낭", "하노이", "나트랑", "호치민", "푸꾸옥"),
    "태국": ("태국", "방콕", "치앙마이", "푸켓"),
    "필리핀": ("필리핀", "세부", "보라카이", "마닐라"),
    "싱가포르": ("싱가포르", "마리나 베이", "센토사"),
    "말레이시아": ("말레이시아", "쿠알라룸푸르", "코타키나발루"),
    "인도네시아": ("인도네시아", "발리", "자카르타"),
    "미국": ("미국", "하와이", "뉴욕", "라스베가스", "괌", "사이판", "LA"),
    "프랑스": ("프랑스", "파리", "루브르"),
    "영국": ("영국", "런던"),
    "이탈리아": ("이탈리아", "로마", "밀라노"),
    "스페인": ("스페인", "바르셀로나", "마드리드"),
    "독일": ("독일", "뮌헨", "프랑크푸르트"),
    "스위스": ("스위스", "취리히"),
    "호주": ("호주", "시드니", "멜버른"),
    "캐나다": ("캐나다", "밴쿠버", "토론토"),
}

# 권역 → 감지 키워드 (원문 보존용) 및 소속 국가
REGION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "동남아": ("동남아",),
    "유럽": ("유럽",),
    "미주": ("미주", "북미"),
    "동북아": ("동북아",),
}
REGION_MEMBERS: dict[str, tuple[str, ...]] = {
    "동남아": ("베트남", "태국", "필리핀", "싱가포르", "말레이시아", "인도네시아"),
    "유럽": ("프랑스", "영국", "이탈리아", "스페인", "독일", "스위스"),
    "미주": ("미국", "캐나다"),
    "동북아": ("일본", "중국", "대만", "홍콩"),
}

# 국가 미상이지만 '해외 혜택'임을 나타내는 신호
_OVERSEAS_SIGNALS = (
    "해외", "글로벌", "면세", "환전", "환율", "여행자보험", "여행보험",
    "공항", "라운지", "항공", "출국", "국제선", "마일리지", "트래블",
)

COUNTRY_FLAGS: dict[str, str] = {
    "일본": "🇯🇵", "중국": "🇨🇳", "대만": "🇹🇼", "홍콩": "🇭🇰", "베트남": "🇻🇳",
    "태국": "🇹🇭", "필리핀": "🇵🇭", "싱가포르": "🇸🇬", "말레이시아": "🇲🇾",
    "인도네시아": "🇮🇩", "미국": "🇺🇸", "프랑스": "🇫🇷", "영국": "🇬🇧",
    "이탈리아": "🇮🇹", "스페인": "🇪🇸", "독일": "🇩🇪", "스위스": "🇨🇭",
    "호주": "🇦🇺", "캐나다": "🇨🇦",
    "동남아": "🌴", "유럽": "🏰", "미주": "🗽", "동북아": "🏯",
    OVERSEAS_COMMON: "🌏", DOMESTIC_ETC: "🏠",
}

# 필터 파라미터 화이트리스트 (캐시 키 오염 방지용)
KNOWN_PLACES = (
    tuple(COUNTRY_KEYWORDS) + tuple(REGION_KEYWORDS)
    + (OVERSEAS_COMMON, DOMESTIC_ETC)
)


def _match_keyword_map(blob: str, keyword_map: dict[str, tuple[str, ...]]) -> list[str]:
    return [
        place for place, keywords in keyword_map.items()
        if any(k in blob for k in keywords)
    ]


def extract_countries(text: str | None) -> list[str]:
    """이벤트 텍스트에서 대상 지역 목록을 추출한다 (항상 1개 이상)."""
    blob = text or ""
    found = _match_keyword_map(blob, COUNTRY_KEYWORDS)
    found += _match_keyword_map(blob, REGION_KEYWORDS)
    if found:
        return found
    if any(signal in blob for signal in _OVERSEAS_SIGNALS):
        return [OVERSEAS_COMMON]
    return [DOMESTIC_ETC]


def expand_country_filter(selected: str) -> set[str]:
    """선택 지역을 매칭 대상 집합으로 전개한다.

    국가 → {국가, 소속 권역들, 해외공통} / 권역 → {권역, 소속 국가들, 해외공통}
    해외공통·국내·기타는 자기 자신만.
    """
    if selected in (OVERSEAS_COMMON, DOMESTIC_ETC):
        return {selected}
    expanded = {selected, OVERSEAS_COMMON}
    if selected in REGION_MEMBERS:
        expanded.update(REGION_MEMBERS[selected])
    expanded.update(
        region for region, members in REGION_MEMBERS.items() if selected in members
    )
    return expanded


def match_rank(event_countries: list[str], selected: str) -> int:
    """정렬 우선순위 — 0: 국가 명시, 1: 권역 매칭, 2: 해외공통."""
    if selected in event_countries:
        return 0
    if any(c in REGION_MEMBERS or selected in REGION_MEMBERS.get(c, ())
           for c in event_countries if c != OVERSEAS_COMMON):
        return 1
    return 2
