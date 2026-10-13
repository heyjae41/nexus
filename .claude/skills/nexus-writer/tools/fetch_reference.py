#!/usr/bin/env python3
"""참고 URL 본문 추출 도구 — 팀원이 제시한 URL 의 글 텍스트를 추출한다.

사용법: python fetch_reference.py <URL> [최대문자수=6000]
출력: 제목 + 본문 텍스트 (stdout)

공개 http(s) 주소만 가져온다 — 사설망·루프백·메타데이터(169.254.169.254) 주소와 그리로 가는
리다이렉트는 거부하고, 본문은 2MB 까지만 읽는다 (SSRF 방어, app.services.safe_fetch).
"""
import sys

from _bootstrap import PROJECT_ROOT  # noqa: E402,F401 — app.* import 경로 설정

import httpx  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

from app.services.safe_fetch import UnsafeUrlError, fetch_public_text  # noqa: E402

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NexusWriter/1.0)"}
NOISE_TAGS = ("script", "style", "nav", "footer", "header", "aside", "iframe")
DEFAULT_LIMIT = 6000
MAX_LIMIT = 20000


def _parse_limit(raw: str | None) -> int:
    if raw is None:
        return DEFAULT_LIMIT
    try:
        limit = int(raw)
    except ValueError as exc:
        raise ValueError("최대문자수는 양의 정수여야 합니다") from exc
    if limit < 1:
        raise ValueError("최대문자수는 양의 정수여야 합니다")
    return min(limit, MAX_LIMIT)


def main() -> int:
    if len(sys.argv) < 2:
        print("사용법: python fetch_reference.py <URL> [최대문자수]", file=sys.stderr)
        return 1
    url = sys.argv[1]
    try:
        limit = _parse_limit(sys.argv[2] if len(sys.argv) > 2 else None)
        page = fetch_public_text(url, headers=HEADERS)
    except UnsafeUrlError as exc:
        print(f"오류: 가져올 수 없는 주소 - {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    except httpx.HTTPError as exc:
        print(f"오류: URL 조회 실패 - {exc}", file=sys.stderr)
        return 1

    soup = BeautifulSoup(page.text, "html.parser")
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else "(제목 없음)"
    main_el = soup.find("article") or soup.find("main") or soup.body or soup
    text = main_el.get_text("\n", strip=True)

    print(f"# {title}\n")
    print(text[:limit])
    if len(text) > limit or page.truncated:
        print(f"\n...(이하 생략, 전체 {len(text)}자{' 이상' if page.truncated else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
