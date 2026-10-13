"""참고 URL 가져오기의 SSRF 방어 — 공개 http(s) 주소만, 검사한 IP 로 연결, 홉마다 재검사, 본문 상한."""
import httpx
import pytest

from app.services.safe_fetch import (
    MAX_REDIRECTS,
    UnsafeUrlError,
    fetch_public_text,
    validate_public_url,
)

ADDRESSES = {
    "example.com": ["93.184.216.34"],
    "v6.example.com": ["2606:4700::1111"],
    "private.test": ["10.0.0.5"],
    "meta.test": ["169.254.169.254"],
    "loop.test": ["127.0.0.2"],
    "cgnat.test": ["100.64.0.1"],
    "ula.test": ["fd00::1"],
    "mapped.test": ["::ffff:10.0.0.9"],
    "nat64.test": ["64:ff9b::a00:5"],
    "sixtofour.test": ["2002:a00:5::1"],
    "zone.test": ["fe80::1%eth0"],
    "mixed.test": ["93.184.216.34", "10.0.0.5"],
}


def resolve(host: str) -> list[str]:
    try:
        return ADDRESSES[host]
    except KeyError as exc:
        raise OSError("name not found") from exc


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/file",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "example.com/no-scheme",
        "http:///missing-host",
        "http://user:pw@example.com/",
        "http://exa\tmple.com/",
        "http://example.com/a b",
        "http://localhost/",
        "http://127.0.0.1:8000/api/internal/ingest/run",
        "http://0.0.0.0/",
        "http://10.1.2.3/",
        "http://192.168.0.10/",
        "http://172.16.5.5/",
        "http://169.254.169.254/latest/meta-data/",
        "http://100.64.0.1/",
        "http://[::1]/",
        "http://[fd00::1]/",
        "http://[::ffff:10.0.0.9]/",
        "http://[64:ff9b::a9fe:a9fe]/",
        "http://[::7f00:1]/",
        "http://[2002:a00:5::1]/",
        "http://private.test/",
        "http://meta.test/",
        "http://loop.test/",
        "http://cgnat.test/",
        "http://ula.test/",
        "http://mapped.test/",
        "http://nat64.test/",
        "http://sixtofour.test/",
        "http://zone.test/",
        "http://mixed.test/",
        "http://unknown.test/",
    ],
)
def test_rejects_non_public_targets(url):
    with pytest.raises(UnsafeUrlError):
        validate_public_url(url, resolve=resolve)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/post?x=1",
        "http://example.com:8080/",
        "https://v6.example.com/",
        "http://[64:ff9b::5db8:d822]/",  # NAT64 에 박힌 93.184.216.34 는 공개 주소
    ],
)
def test_accepts_public_http_targets(url):
    assert validate_public_url(url, resolve=resolve) == url


def _transport(routes, seen=None):
    """요청은 검사한 IP 로 가고 Host 헤더가 원래 호스트명이다 — 라우팅 키는 scheme://Host/path."""

    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.url.scheme}://{request.headers['host']}{request.url.raw_path.decode()}"
        if seen is not None:
            seen.append((request.url.host, request.headers["host"], request.extensions.get("sni_hostname")))
        status, headers, body = routes[key]
        return httpx.Response(status, headers=headers, content=body)

    return httpx.MockTransport(handler)


def test_fetches_public_page_connecting_to_the_validated_ip():
    seen = []
    transport = _transport(
        {"https://example.com/a": (200, {"content-type": "text/html"}, b"<p>hi</p>")}, seen
    )
    page = fetch_public_text("https://example.com/a", resolve=resolve, transport=transport)
    assert page.text == "<p>hi</p>"
    assert page.truncated is False
    # DNS 리바인딩 차단: 연결은 검사한 IP 로, Host·SNI 는 원래 호스트명으로
    assert seen == [("93.184.216.34", "example.com", "example.com")]


def test_keeps_port_and_brackets_ipv6_when_pinning():
    seen = []
    transport = _transport({
        "http://example.com:8080/p": (200, {}, b"a"),
        "https://v6.example.com/q": (200, {}, b"b"),
    }, seen)
    fetch_public_text("http://example.com:8080/p", resolve=resolve, transport=transport)
    fetch_public_text("https://v6.example.com/q", resolve=resolve, transport=transport)
    assert seen[0] == ("93.184.216.34", "example.com:8080", None)
    assert seen[1] == ("2606:4700::1111", "v6.example.com", "v6.example.com")


@pytest.mark.parametrize(
    "location",
    ["https://example.com/b", "/b", "b", "//example.com/b"],
    ids=["absolute", "root-relative", "relative", "scheme-relative"],
)
def test_follows_public_redirects_in_every_location_form(location):
    transport = _transport({
        "https://example.com/a": (302, {"location": location}, b""),
        "https://example.com/b": (200, {}, b"ok"),
    })
    page = fetch_public_text("https://example.com/a", resolve=resolve, transport=transport)
    assert page.text == "ok" and page.url == "https://example.com/b"


@pytest.mark.parametrize(
    "location", ["http://meta.test/latest/meta-data/", "//meta.test/", "http://10.0.0.5/"]
)
def test_rechecks_each_redirect_hop(location):
    transport = _transport({"https://example.com/a": (302, {"location": location}, b"")})
    with pytest.raises(UnsafeUrlError):
        fetch_public_text("https://example.com/a", resolve=resolve, transport=transport)


def test_stops_after_max_redirects():
    routes = {
        f"https://example.com/{i}": (302, {"location": f"https://example.com/{i + 1}"}, b"")
        for i in range(MAX_REDIRECTS + 2)
    }
    with pytest.raises(UnsafeUrlError):
        fetch_public_text("https://example.com/0", resolve=resolve, transport=_transport(routes))


def test_caps_body_size():
    transport = _transport({"https://example.com/big": (200, {}, b"x" * 10_000)})
    page = fetch_public_text(
        "https://example.com/big", resolve=resolve, transport=transport, max_bytes=1_000
    )
    assert page.truncated is True
    assert len(page.text) <= 1_000


def test_total_deadline_applies_before_each_hop():
    transport = _transport({"https://example.com/a": (200, {}, b"x")})
    with pytest.raises(UnsafeUrlError):
        fetch_public_text(
            "https://example.com/a", resolve=resolve, transport=transport, total_timeout=0
        )
