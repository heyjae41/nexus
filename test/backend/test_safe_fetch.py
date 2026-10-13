"""참고 URL 가져오기의 SSRF 방어 — 공개 http(s) 주소만, 리다이렉트 홉마다 재검사, 본문 상한."""
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
        "http://private.test/",
        "http://meta.test/",
        "http://loop.test/",
        "http://cgnat.test/",
        "http://ula.test/",
        "http://mapped.test/",
        "http://mixed.test/",
        "http://unknown.test/",
    ],
)
def test_rejects_non_public_targets(url):
    with pytest.raises(UnsafeUrlError):
        validate_public_url(url, resolve=resolve)


@pytest.mark.parametrize(
    "url", ["https://example.com/post?x=1", "http://example.com:8080/", "https://v6.example.com/"]
)
def test_accepts_public_http_targets(url):
    assert validate_public_url(url, resolve=resolve) == url


def _transport(routes):
    def handler(request: httpx.Request) -> httpx.Response:
        status, headers, body = routes[str(request.url)]
        return httpx.Response(status, headers=headers, content=body)

    return httpx.MockTransport(handler)


def test_fetches_public_page():
    transport = _transport({"https://example.com/a": (200, {"content-type": "text/html"}, b"<p>hi</p>")})
    page = fetch_public_text("https://example.com/a", resolve=resolve, transport=transport)
    assert page.text == "<p>hi</p>"
    assert page.truncated is False


def test_follows_public_redirects_but_rechecks_each_hop():
    transport = _transport({
        "https://example.com/a": (302, {"location": "https://example.com/b"}, b""),
        "https://example.com/b": (200, {}, b"ok"),
    })
    assert fetch_public_text("https://example.com/a", resolve=resolve, transport=transport).text == "ok"

    transport = _transport({
        "https://example.com/a": (302, {"location": "http://meta.test/latest/meta-data/"}, b""),
    })
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
