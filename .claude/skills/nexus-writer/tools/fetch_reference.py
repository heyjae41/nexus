#!/usr/bin/env python3
"""참고 URL 본문 추출 도구 — 팀원이 제시한 URL 의 글 텍스트를 추출한다.

사용법: python fetch_reference.py <URL> [최대문자수=6000]
출력: 제목 + 본문 텍스트 (stdout)
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import httpx  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NexusWriter/1.0)"}
NOISE_TAGS = ("script", "style", "nav", "footer", "header", "aside", "iframe")


def main() -> int:
    if len(sys.argv) < 2:
        print("사용법: python fetch_reference.py <URL> [최대문자수]", file=sys.stderr)
        return 1
    url = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 6000

    try:
        res = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        res.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"오류: URL 조회 실패 - {exc}", file=sys.stderr)
        return 1

    soup = BeautifulSoup(res.text, "html.parser")
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else "(제목 없음)"
    main_el = soup.find("article") or soup.find("main") or soup.body or soup
    text = main_el.get_text("\n", strip=True)

    print(f"# {title}\n")
    print(text[:limit])
    if len(text) > limit:
        print(f"\n...(이하 생략, 전체 {len(text)}자)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
