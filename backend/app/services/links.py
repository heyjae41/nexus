"""외부 이동 URL 규칙: 브런치 원글 주소에 항상 ref 파라미터를 부착한다."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REF_KEY = "ref"
REF_VALUE = "nexus.bccard.ai"


def with_ref(url: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if query.get(REF_KEY) == REF_VALUE:
        return url
    query[REF_KEY] = REF_VALUE
    return urlunsplit(parts._replace(query=urlencode(query)))
