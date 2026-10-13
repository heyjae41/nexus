"""공개 URL 만 가져오는 HTTP 조회 — 작가 도구(fetch_reference)의 SSRF 방어.

- http/https 만, `user:pw@` 사용자정보·공백/제어문자 금지
- 호스트를 DNS 로 한 번 풀어 모든 주소가 공개(글로벌) 주소여야 한다: 루프백·사설·링크로컬(169.254 메타데이터)·
  CGNAT(100.64/10)·멀티캐스트 거부. IPv4-mapped·6to4·Teredo·NAT64 에 박힌 IPv4 도 풀어서 검사하고
  IPv4-compatible(::/96) 은 거부
- 검사한 IP 로 직접 연결한다(Host 헤더·SNI 는 원래 호스트명) — 검사와 연결 사이의 DNS 리바인딩 차단
- 리다이렉트는 자동 추적하지 않고 홉마다 다시 검사하며 MAX_REDIRECTS 까지만 따라간다
- 본문은 스트리밍으로 max_bytes 까지만 읽고, 전체 시간(total_timeout)을 홉마다 깎아 쓴다
- 환경의 HTTP(S)_PROXY 는 무시한다(trust_env=False) — 프록시가 이름을 풀면 검사가 무의미하다
"""
import ipaddress
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

MAX_REDIRECTS = 3
DEFAULT_MAX_BYTES = 2_000_000
DEFAULT_TIMEOUT = 15.0
DEFAULT_TOTAL_TIMEOUT = 40.0
ALLOWED_SCHEMES = frozenset({"http", "https"})
_NAT64 = ipaddress.ip_network("64:ff9b::/96")
_IPV4_COMPAT = ipaddress.ip_network("::/96")

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


def _embedded_ipv4(ip: ipaddress.IPv6Address) -> ipaddress.IPv4Address | None:
    """전환 주소(mapped·6to4·Teredo·NAT64)에 박힌 IPv4 를 꺼낸다. IPv4-compatible 은 None(거부)."""
    if ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    if ip.sixtofour is not None:
        return ip.sixtofour
    if ip.teredo is not None:
        return ip.teredo[1]
    if ip in _NAT64 or ip in _IPV4_COMPAT:
        return ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF) if ip in _NAT64 else None
    return None


def _is_public(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        if ip in _IPV4_COMPAT:
            return False
        ip = _embedded_ipv4(ip) or ip
    return ip.is_global and not ip.is_multicast


def _public_host(url: str) -> str:
    """URL 모양 검사 (스킴·호스트·사용자정보·공백·localhost) 후 호스트명을 돌려준다."""
    if any(ch.isspace() for ch in url):
        raise UnsafeUrlError("주소에 공백이나 제어문자가 있습니다")
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


def _public_addresses(url: str, resolve: Resolver) -> tuple[str, list[str]]:
    host = _public_host(url)
    addresses = _addresses_of(host, resolve)
    if not addresses or not all(_is_public(address) for address in addresses):
        raise UnsafeUrlError("내부 주소는 가져올 수 없습니다")
    return host, addresses


def validate_public_url(url: str, *, resolve: Resolver = _resolve) -> str:
    """공개 http(s) URL 이면 그대로 돌려주고, 아니면 UnsafeUrlError."""
    _public_addresses(url, resolve)
    return url


@dataclass(frozen=True)
class _PinnedRequest:
    """검사한 IP 로 연결하되 Host·SNI 는 원래 호스트명을 쓰는 요청."""

    url: str
    headers: dict[str, str]
    extensions: dict[str, str]


def _pin(url: str, resolve: Resolver) -> _PinnedRequest:
    host, addresses = _public_addresses(url, resolve)
    parts = urlsplit(url)
    ip = addresses[0].split("%", 1)[0]
    ip_text = f"[{ip}]" if ":" in ip else ip
    netloc = ip_text if parts.port is None else f"{ip_text}:{parts.port}"
    pinned = urlunsplit(parts._replace(netloc=netloc))
    extensions = {"sni_hostname": host} if parts.scheme.lower() == "https" else {}
    return _PinnedRequest(pinned, {"Host": parts.netloc}, extensions)


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


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise UnsafeUrlError("조회 시간이 초과됐습니다")
    return remaining


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
    """공개 URL 의 본문을 max_bytes 까지 읽어 돌려준다. 홉마다 주소를 다시 검사하고 그 IP 로 연결한다."""
    deadline = time.monotonic() + total_timeout
    current = url
    with httpx.Client(
        follow_redirects=False, timeout=timeout, headers=headers, transport=transport,
        trust_env=False,
    ) as client:
        for _ in range(max_redirects + 1):
            pinned = _pin(current, resolve)
            hop_timeout = min(timeout, _remaining(deadline))
            try:
                stream = client.stream(
                    "GET", pinned.url, headers=pinned.headers, extensions=pinned.extensions,
                    timeout=hop_timeout,
                )
                with stream as response:
                    if response.has_redirect_location:
                        current = urljoin(current, response.headers["location"])
                        continue
                    response.raise_for_status()
                    body, truncated = _read_capped(response, max_bytes, deadline)
                    return FetchedPage(current, _decode(body, response.encoding), truncated)
            except httpx.InvalidURL as exc:
                raise UnsafeUrlError(f"잘못된 주소입니다: {exc}") from exc
    raise UnsafeUrlError("리다이렉트가 너무 많습니다")
