"""파드 안에서 내부 운영 API 를 호출한다 — 백엔드 이미지에는 curl 이 없다.

사용법: python -m app.internal_call content/resanitize   (→ POST http://127.0.0.1:8000/api/internal/content/resanitize)
        python -m app.internal_call media/backfill
루프백에서 부르므로 X-Internal-Token 없이 통과한다 (api/internal_access.py).
"""
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable

BASE_URL = "http://127.0.0.1:8000"
PREFIX = "/api/internal/"


def build_request(path: str, base_url: str = BASE_URL) -> urllib.request.Request:
    """'content/resanitize' 나 '/api/internal/content/resanitize' 모두 같은 URL 로 만든다."""
    tail = path.strip().lstrip("/")
    if tail.startswith(PREFIX.lstrip("/")):
        tail = tail[len(PREFIX) - 1 :]
    if not tail:
        raise ValueError("호출할 내부 API 경로를 주세요 (예: content/resanitize)")
    return urllib.request.Request(f"{base_url}{PREFIX}{tail}", method="POST")


def call(path: str, *, opener: Callable = urllib.request.urlopen, timeout: float = 600) -> tuple[int, str]:
    """(HTTP 상태, 응답 본문). 4xx/5xx 도 본문을 돌려준다."""
    request = build_request(path)
    try:
        with opener(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def main(argv: list[str] | None = None, *, opener: Callable = urllib.request.urlopen) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        status, body = call(argv[0], opener=opener)
    except (ValueError, OSError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    try:
        print(json.dumps(json.loads(body), ensure_ascii=False))
    except ValueError:
        print(body)
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    sys.exit(main())
