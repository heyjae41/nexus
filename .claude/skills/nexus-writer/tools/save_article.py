#!/usr/bin/env python3
"""글 저장 도구 — JSON 입력을 받아 /contents 에 명명규칙에 맞는 HTML 로 저장한다.

사용법:
  python save_article.py article.json          # 파일 입력
  echo '{...}' | python save_article.py -      # stdin 입력

입력 JSON 필드:
  title(필수), article_type(newsletter|column|guide, 필수),
  summary(필수), author(필수), body_html(필수), key_visual_html(필수),
  published_date(yyyy-mm-dd, 생략 시 오늘), read_minutes(생략 시 본문 기준 자동)

출력: 저장된 파일 경로 (stdout)
"""
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.article_builder import (  # noqa: E402
    build_filename,
    estimate_read_minutes,
    render_article_html,
)
from bs4 import BeautifulSoup  # noqa: E402

REQUIRED = ("title", "article_type", "summary", "author", "body_html", "key_visual_html")


def main() -> int:
    source = sys.argv[1] if len(sys.argv) > 1 else "-"
    raw = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"오류: JSON 파싱 실패 - {exc}", file=sys.stderr)
        return 1

    missing = [f for f in REQUIRED if not str(payload.get(f, "")).strip()]
    if missing:
        print(f"오류: 필수 필드 누락 - {', '.join(missing)}", file=sys.stderr)
        return 1

    published = (
        date.fromisoformat(payload["published_date"])
        if payload.get("published_date")
        else date.today()
    )
    body_text = BeautifulSoup(payload["body_html"], "html.parser").get_text(" ", strip=True)
    read_minutes = int(payload.get("read_minutes") or estimate_read_minutes(body_text))

    try:
        filename = build_filename(published, payload["article_type"], payload["title"])
        html = render_article_html(
            title=payload["title"],
            summary=payload["summary"],
            author=payload["author"],
            body_html=payload["body_html"],
            key_visual_html=payload["key_visual_html"],
            read_minutes=read_minutes,
        )
    except ValueError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1

    contents_dir = PROJECT_ROOT / "contents"
    contents_dir.mkdir(exist_ok=True)
    target = contents_dir / filename
    target.write_text(html, encoding="utf-8")
    print(str(target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
