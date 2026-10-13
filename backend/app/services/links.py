"""외부 이동 URL 규칙: 수집 원글 주소에 항상 ref 파라미터를 부착한다.

http(s) 가 아닌 주소(javascript:, data:, 프로토콜 상대 등)는 None — 카드가 링크 없이 그려진다.
수집 소스나 미래의 수집기가 넘긴 값이 그대로 <a href> 가 되므로 여기서 한 번 더 거른다."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REF_KEY = "ref"
REF_VALUE = "nexus.bccard.ai"
ALLOWED_SCHEMES = ("http", "https")


def with_ref(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES or not parts.netloc:
        return None
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if query.get(REF_KEY) == REF_VALUE:
        return url
    query[REF_KEY] = REF_VALUE
    return urlunsplit(parts._replace(query=urlencode(query)))
