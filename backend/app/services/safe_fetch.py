"""공개 URL 만 가져오는 HTTP 조회 — 작가 도구(fetch_reference)의 SSRF 방어.

- http/https 만, `user:pw@` 사용자정보 금지
- 호스트를 DNS 로 풀어 모든 주소가 공개(글로벌) 주소여야 한다: 루프백·사설·링크로컬(169.254 메타데이터)·
  CGNAT(100.64/10)·멀티캐스트·IPv4-mapped IPv6 등은 거부
- 리다이렉트는 자동 추적하지 않고 홉마다 다시 검사하며 MAX_REDIRECTS 까지만 따라간다
- 본문은 스트리밍으로 max_bytes 까지만 읽고 전체 시간에 상한을 둔다

잔여 위험: 검사 시점과 연결 시점 사이에 DNS 응답이 바뀌는 리바인딩은 막지 못한다.
"""
import ipaddress
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

MAX_REDIRECTS = 3
DEFAULT_MAX_BYTES = 2_000_000
DEFAULT_TIMEOUT = 15.0
DEFAULT_TOTAL_TIMEOUT = 40.0
ALLOWED_SCHEMES = frozenset({"http", "https"})

Resolver = Callable[[str], list[str]]


class UnsafeUrlError(ValueError):
    """공개 http(s) 주소가 아니거나 조회 한도를 넘었다."""


@dataclass(frozen=True)
class FetchedPage:
    url: str
    text: str
    truncated: bool


def _resolve(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


def _is_public(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def _public_host(url: str) -> str:
    """URL 모양 검사 (스킴·호스트·사용자정보·localhost) 후 호스트명을 돌려준다."""
    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeUrlError("http/https 주소만 가져올 수 있습니다")
    host = parts.hostname
    if not host:
        raise UnsafeUrlError("호스트가 없는 주소입니다")
    if parts.username or parts.password:
        raise UnsafeUrlError("사용자 정보가 포함된 주소는 가져올 수 없습니다")
    if host == "localhost" or host.endswith(".localhost"):
        raise UnsafeUrlError("내부 주소는 가져올 수 없습니다")
    return host


def _addresses_of(host: str, resolve: Resolver) -> list[str]:
    try:
        ipaddress.ip_address(host)
        return [host]
    except ValueError:
        pass
    try:
        return resolve(host)
    except OSError as exc:
        raise UnsafeUrlError(f"호스트를 찾을 수 없습니다: {host}") from exc


def validate_public_url(url: str, *, resolve: Resolver = _resolve) -> str:
    """공개 http(s) URL 이면 그대로 돌려주고, 아니면 UnsafeUrlError."""
    addresses = _addresses_of(_public_host(url), resolve)
    if not addresses or not all(_is_public(address) for address in addresses):
        raise UnsafeUrlError("내부 주소는 가져올 수 없습니다")
    return url


def _read_capped(response: httpx.Response, max_bytes: int, deadline: float) -> tuple[bytes, bool]:
    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_bytes():
        if time.monotonic() > deadline:
            raise UnsafeUrlError("응답을 읽는 데 너무 오래 걸립니다")
        room = max_bytes - size
        if len(chunk) > room:
            chunks.append(chunk[:room])
            return b"".join(chunks), True
        chunks.append(chunk)
        size += len(chunk)
    return b"".join(chunks), False


def _decode(body: bytes, encoding: str | None) -> str:
    try:
        return body.decode(encoding or "utf-8", errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def fetch_public_text(
    url: str,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_redirects: int = MAX_REDIRECTS,
    timeout: float = DEFAULT_TIMEOUT,
    total_timeout: float = DEFAULT_TOTAL_TIMEOUT,
    headers: dict[str, str] | None = None,
    resolve: Resolver = _resolve,
    transport: httpx.BaseTransport | None = None,
) -> FetchedPage:
    """공개 URL 의 본문을 max_bytes 까지 읽어 돌려준다. 홉마다 주소를 다시 검사한다."""
    deadline = time.monotonic() + total_timeout
    current = url
    with httpx.Client(
        follow_redirects=False, timeout=timeout, headers=headers, transport=transport
    ) as client:
        for _ in range(max_redirects + 1):
            validate_public_url(current, resolve=resolve)
            with client.stream("GET", current) as response:
                if response.has_redirect_location:
                    current = urljoin(current, response.headers["location"])
                    continue
                response.raise_for_status()
                body, truncated = _read_capped(response, max_bytes, deadline)
                return FetchedPage(current, _decode(body, response.encoding), truncated)
    raise UnsafeUrlError("리다이렉트가 너무 많습니다")
